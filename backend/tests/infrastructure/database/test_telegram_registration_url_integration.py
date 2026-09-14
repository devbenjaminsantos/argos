"""URL persistida com resultado imutável em PostgreSQL real."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from argos.application.ports.telegram_registration_url import RegistrationURLReplies
from argos.infrastructure.database.telegram_registration_url import PostgreSQLTelegramRegistrationURLRepository
from tests.infrastructure.database.test_telegram_registration_integration import context, begin

pytestmark = pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None, reason="PostgreSQL de teste ausente.")

_URL = "https://produto.mercadolivre.com.br/MLB-123-produto"
_REPLIES = RegistrationURLReplies("accepted", "invalid", "absent", "wrong-state")


@pytest.fixture
def url_context(context):
    engine, now, lease = context
    begin(context)
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_registration_results"))
        for value in (1, 2):
            c.execute(text("UPDATE telegram_update_inbox SET payload=CAST(:payload AS jsonb) WHERE update_id=:id"),
                      {"id": value, "payload": json.dumps({"message": {"from": {"id": 700}, "chat": {"id": 800, "type": "private"}, "text": _URL}})})
    return context


def receive(ctx, update_id=1, **changes):
    engine, now, lease = ctx
    return PostgreSQLTelegramRegistrationURLRepository(engine).receive_for_update(**(dict(
        update_id=update_id, lease_token=lease, telegram_user_id=700, chat_id=800,
        text=_URL, normalized_url=_URL, observed_at=now, replies=_REPLIES) | changes))


def snapshot(engine):
    with engine.connect() as c:
        return c.execute(text("SELECT state,data,version,expires_at FROM telegram_conversation_drafts")).one_or_none()


def test_advances_once_and_replays_after_restart_and_cancel(url_context):
    engine, now, _ = url_context
    original = snapshot(engine)
    assert receive(url_context).text == "accepted"
    advanced = snapshot(engine)
    assert advanced.state == "awaiting_alias"
    assert advanced.data == {"url": _URL}
    assert advanced.version != original.version
    assert advanced.expires_at == original.expires_at
    assert receive(url_context).text == "accepted"
    assert snapshot(engine) == advanced
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_conversation_drafts"))
        recovered = uuid4()
        c.execute(text("UPDATE telegram_update_inbox SET lease_token=:lease WHERE update_id=1"), {"lease": recovered})
    engine.dispose()
    assert receive((engine, now, recovered)).text == "accepted"
    assert snapshot(engine) is None


@pytest.mark.parametrize("ids,expected", [([1, 1], ["accepted", "accepted"]), ([1, 2], ["accepted", "wrong-state"])])
def test_concurrent_updates_or_duplicate(url_context, ids, expected):
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda value: receive(url_context, value).text, ids))
    assert sorted(replies) == sorted(expected)
    assert snapshot(url_context[0]).state == "awaiting_alias"


@pytest.mark.parametrize("change", [{"lease_token": uuid4()}, {"telegram_user_id": 701}, {"chat_id": 801}, {"text": _URL + "?x=1"}, {"normalized_url": "https://evil.test"}])
def test_divergent_claim_identity_text_or_url_cannot_mutate(url_context, change):
    original = snapshot(url_context[0])
    with pytest.raises(RuntimeError):
        receive(url_context, **change)
    assert snapshot(url_context[0]) == original


def test_invalid_url_preserves_draft_and_persists_negative_result(url_context):
    engine = url_context[0]
    raw = "https://evil.test/MLB-123"
    with engine.begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}',to_jsonb(CAST(:raw AS text))) WHERE update_id=1"), {"raw": raw})
    original = snapshot(engine)
    assert receive(url_context, text=raw, normalized_url=None).text == "invalid"
    assert snapshot(engine) == original
    assert receive(url_context, text=raw, normalized_url=None).text == "invalid"


def test_expired_draft_and_missing_draft_do_not_advance(url_context):
    engine, now, _ = url_context
    original = snapshot(engine)
    assert receive(url_context, observed_at=now + timedelta(hours=1)).text == "absent"
    assert snapshot(engine) == original
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_conversation_drafts"))
    assert receive(url_context, 2).text == "absent"


def test_reply_insertion_failure_rolls_back_advance(url_context):
    original = snapshot(url_context[0])
    with pytest.raises(IntegrityError):
        receive(url_context, replies=RegistrationURLReplies("", "invalid", "absent", "wrong-state"))
    assert snapshot(url_context[0]) == original
    assert receive(url_context).text == "accepted"


def test_expired_lease_cannot_advance(url_context):
    original = snapshot(url_context[0])
    with url_context[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_expires_at=clock_timestamp()-interval '1 second'"))
    with pytest.raises(RuntimeError, match="Lease"):
        receive(url_context)
    assert snapshot(url_context[0]) == original


def test_cancel_concurrent_with_receive_never_recreates_draft(url_context):
    from argos.infrastructure.database.telegram_conversations import PostgreSQLTelegramConversationDraftRepository
    engine = url_context[0]
    def cancel():
        return PostgreSQLTelegramConversationDraftRepository(engine).cancel_for_owner(telegram_user_id=700)
    with ThreadPoolExecutor(max_workers=2) as pool:
        receiving = pool.submit(receive, url_context)
        cancelling = pool.submit(cancel)
        assert receiving.result().text in {"accepted", "absent"}
        assert cancelling.result() is True
    assert snapshot(engine) is None


def test_http_to_composed_worker_invalid_valid_duplicate_and_quota(url_context):
    from datetime import UTC, datetime
    from fastapi.testclient import TestClient
    from pydantic import SecretStr
    from argos.application.use_cases.admit_telegram_update import AdmitTelegramUpdate
    from argos.config import Settings
    from argos.infrastructure.database.telegram_admission import PostgreSQLTelegramAdmissionRepository
    from argos.main import create_app
    from argos.telegram_worker import build_worker

    engine = url_context[0]
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_update_inbox"))
        c.execute(text("DELETE FROM telegram_admissions"))
        c.execute(text("DELETE FROM telegram_admission_owners"))
    class Sender:
        def __init__(self):
            self.messages = []
        def send(self, message):
            self.messages.append(message)
    sender = Sender()
    settings = Settings(environment="test", telegram_webhook_secret=SecretStr("integration-secret"))
    app = create_app(settings, telegram_admission=AdmitTelegramUpdate(PostgreSQLTelegramAdmissionRepository(engine)))
    worker = build_worker(settings, engine=engine, sender=sender)
    original = snapshot(engine)
    try:
        with TestClient(app) as client:
            for update_id, raw in enumerate(["https://evil.test/x", _URL] + [_URL] * 9, start=10):
                payload = {"update_id": update_id, "message": {"message_id": 1, "from": {"id": 700}, "chat": {"id": 800, "type": "private"}, "text": raw}}
                headers = {"X-Telegram-Bot-Api-Secret-Token": "integration-secret"}
                assert client.post("/webhooks/telegram", headers=headers, json=payload).status_code == 200
                assert client.post("/webhooks/telegram", headers=headers, json=payload).status_code == 200
                assert worker.process_next(now=datetime.now(UTC)) is (update_id < 20)
                if update_id == 10:
                    assert snapshot(engine) == original
            assert "Envie uma URL" in sender.messages[0].text
            assert "URL registrada" in sender.messages[1].text
            assert "já recebeu" in sender.messages[2].text
            assert len(sender.messages) == 10
            assert snapshot(engine).state == "awaiting_alias"
            assert snapshot(engine).expires_at == original.expires_at
        with engine.connect() as c:
            assert c.scalar(text("SELECT count(*) FROM telegram_update_inbox WHERE status='completed'")) == 10
            assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 10
            assert c.scalar(text("SELECT decision FROM telegram_admissions WHERE update_id=20")) == "rate_limited"
    finally:
        with engine.begin() as c:
            c.execute(text("DELETE FROM telegram_admissions"))
            c.execute(text("DELETE FROM telegram_admission_owners"))
