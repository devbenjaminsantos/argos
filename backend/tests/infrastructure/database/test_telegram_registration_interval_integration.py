"""Intervalo persistido com resultado imutável em PostgreSQL real."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from argos.application.ports.telegram_registration_interval import RegistrationIntervalReplies
from argos.infrastructure.database.telegram_registration_interval import PostgreSQLTelegramRegistrationIntervalRepository
from tests.infrastructure.database.test_telegram_registration_integration import context, begin

pytestmark = pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None, reason="PostgreSQL de teste ausente.")

_URL = "https://produto.mercadolivre.com.br/MLB-123-produto"
_INTERVAL = "12"
_REPLIES = RegistrationIntervalReplies("accepted", "invalid", "absent", "wrong-state")


@pytest.fixture
def interval_context(context):
    engine, now, lease = context
    begin(context)
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_registration_results"))
        c.execute(text("UPDATE telegram_conversation_drafts SET state='awaiting_interval', data=CAST(:data AS jsonb)"), {"data": json.dumps({"url": _URL, "alias": "Caneca Kitty", "target_price_cents": 250090, "extra": "preserved"})})
        for value in (1, 2):
            c.execute(text("UPDATE telegram_update_inbox SET payload=CAST(:payload AS jsonb) WHERE update_id=:id"),
                      {"id": value, "payload": json.dumps({"message": {"from": {"id": 700}, "chat": {"id": 800, "type": "private"}, "text": _INTERVAL}})})
    return context


def receive(ctx, update_id=1, **changes):
    engine, now, lease = ctx
    return PostgreSQLTelegramRegistrationIntervalRepository(engine).receive_for_update(**(dict(
        update_id=update_id, lease_token=lease, telegram_user_id=700, chat_id=800,
        text=_INTERVAL, interval_hours=12, observed_at=now, replies=_REPLIES) | changes))


def snapshot(engine):
    with engine.connect() as c:
        return c.execute(text("SELECT state,data,version,expires_at FROM telegram_conversation_drafts")).one_or_none()


def test_advances_once_and_replays_after_restart_and_cancel(interval_context):
    engine, now, _ = interval_context
    original = snapshot(engine)
    assert receive(interval_context).text == "accepted"
    advanced = snapshot(engine)
    assert advanced.state == "awaiting_confirmation"
    assert advanced.data == {"url": _URL, "alias": "Caneca Kitty", "interval_hours": 12, "target_price_cents": 250090, "extra": "preserved"}
    assert advanced.version != original.version
    assert advanced.expires_at == original.expires_at
    assert receive(interval_context).text == "accepted"
    assert snapshot(engine) == advanced
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_conversation_drafts"))
        recovered = uuid4()
        c.execute(text("UPDATE telegram_update_inbox SET lease_token=:lease WHERE update_id=1"), {"lease": recovered})
    engine.dispose()
    assert receive((engine, now, recovered)).text == "accepted"
    assert snapshot(engine) is None


@pytest.mark.parametrize("ids,expected", [([1, 1], ["accepted", "accepted"]), ([1, 2], ["accepted", "wrong-state"])])
def test_concurrent_updates_or_duplicate(interval_context, ids, expected):
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda value: receive(interval_context, value).text, ids))
    assert sorted(replies) == sorted(expected)
    assert snapshot(interval_context[0]).state == "awaiting_confirmation"


@pytest.mark.parametrize("change", [{"lease_token": uuid4()}, {"telegram_user_id": 701}, {"chat_id": 801}, {"text": _INTERVAL + "?x=1"}, {"interval_hours": 1}, {"interval_hours": True}])
def test_divergent_claim_identity_text_or_url_cannot_mutate(interval_context, change):
    original = snapshot(interval_context[0])
    with pytest.raises(RuntimeError):
        receive(interval_context, **change)
    assert snapshot(interval_context[0]) == original


def test_invalid_alias_preserves_draft_and_persists_negative_result(interval_context):
    engine = interval_context[0]
    raw = "https://evil.test/MLB-123"
    with engine.begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}',to_jsonb(CAST(:raw AS text))) WHERE update_id=1"), {"raw": raw})
    original = snapshot(engine)
    assert receive(interval_context, text=raw, interval_hours=None).text == "invalid"
    assert snapshot(engine) == original
    assert receive(interval_context, text=raw, interval_hours=None).text == "invalid"


def test_expired_draft_and_missing_draft_do_not_advance(interval_context):
    engine, now, _ = interval_context
    original = snapshot(engine)
    assert receive(interval_context, observed_at=now + timedelta(hours=1)).text == "absent"
    assert snapshot(engine) == original
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_conversation_drafts"))
    assert receive(interval_context, 2).text == "absent"


def test_reply_insertion_failure_rolls_back_advance(interval_context):
    original = snapshot(interval_context[0])
    with pytest.raises(IntegrityError):
        receive(interval_context, replies=RegistrationIntervalReplies("", "invalid", "absent", "wrong-state"))
    assert snapshot(interval_context[0]) == original
    assert receive(interval_context).text == "accepted"


def test_expired_lease_cannot_advance(interval_context):
    original = snapshot(interval_context[0])
    with interval_context[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_expires_at=clock_timestamp()-interval '1 second'"))
    with pytest.raises(RuntimeError, match="Lease"):
        receive(interval_context)
    assert snapshot(interval_context[0]) == original


def test_cancel_concurrent_with_receive_never_recreates_draft(interval_context):
    from argos.infrastructure.database.telegram_conversations import PostgreSQLTelegramConversationDraftRepository
    engine = interval_context[0]
    def cancel():
        return PostgreSQLTelegramConversationDraftRepository(engine).cancel_for_owner(telegram_user_id=700)
    with ThreadPoolExecutor(max_workers=2) as pool:
        receiving = pool.submit(receive, interval_context)
        cancelling = pool.submit(cancel)
        assert receiving.result().text in {"accepted", "absent"}
        assert cancelling.result() is True
    assert snapshot(engine) is None




def test_accepts_24_hours_without_changing_prior_data(interval_context):
    engine = interval_context[0]
    original = snapshot(engine)
    with engine.begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}','\"24\"') WHERE update_id=1"))
    assert receive(interval_context, text="24", interval_hours=24).text == "accepted"
    final = snapshot(engine)
    assert final.state == "awaiting_confirmation"
    assert final.data == {**original.data, "interval_hours": 24}
    assert final.expires_at == original.expires_at
