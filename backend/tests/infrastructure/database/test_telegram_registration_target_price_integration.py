"""Preço-alvo persistido com resultado imutável em PostgreSQL real."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from argos.application.ports.telegram_registration_target_price import RegistrationTargetPriceReplies
from argos.infrastructure.database.telegram_registration_target_price import PostgreSQLTelegramRegistrationTargetPriceRepository
from tests.infrastructure.database.test_telegram_registration_integration import context, begin

pytestmark = pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None, reason="PostgreSQL de teste ausente.")

_URL = "https://produto.mercadolivre.com.br/MLB-123-produto"
_PRICE = "R$ 2.500,90"
_REPLIES = RegistrationTargetPriceReplies("accepted", "invalid", "absent", "wrong-state")


@pytest.fixture
def price_context(context):
    engine, now, lease = context
    begin(context)
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_registration_results"))
        c.execute(text("UPDATE telegram_conversation_drafts SET state='awaiting_target_price', data=CAST(:data AS jsonb)"), {"data": json.dumps({"url": _URL, "alias": "Caneca Kitty", "extra": "preserved"})})
        for value in (1, 2):
            c.execute(text("UPDATE telegram_update_inbox SET payload=CAST(:payload AS jsonb) WHERE update_id=:id"),
                      {"id": value, "payload": json.dumps({"message": {"from": {"id": 700}, "chat": {"id": 800, "type": "private"}, "text": _PRICE}})})
    return context


def receive(ctx, update_id=1, **changes):
    engine, now, lease = ctx
    return PostgreSQLTelegramRegistrationTargetPriceRepository(engine).receive_for_update(**(dict(
        update_id=update_id, lease_token=lease, telegram_user_id=700, chat_id=800,
        text=_PRICE, target_price_cents=250090, observed_at=now, replies=_REPLIES) | changes))


def snapshot(engine):
    with engine.connect() as c:
        return c.execute(text("SELECT state,data,version,expires_at FROM telegram_conversation_drafts")).one_or_none()


def test_advances_once_and_replays_after_restart_and_cancel(price_context):
    engine, now, _ = price_context
    original = snapshot(engine)
    assert receive(price_context).text == "accepted"
    advanced = snapshot(engine)
    assert advanced.state == "awaiting_interval"
    assert advanced.data == {"url": _URL, "alias": "Caneca Kitty", "target_price_cents": 250090, "extra": "preserved"}
    assert advanced.version != original.version
    assert advanced.expires_at == original.expires_at
    assert receive(price_context).text == "accepted"
    assert snapshot(engine) == advanced
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_conversation_drafts"))
        recovered = uuid4()
        c.execute(text("UPDATE telegram_update_inbox SET lease_token=:lease WHERE update_id=1"), {"lease": recovered})
    engine.dispose()
    assert receive((engine, now, recovered)).text == "accepted"
    assert snapshot(engine) is None


@pytest.mark.parametrize("ids,expected", [([1, 1], ["accepted", "accepted"]), ([1, 2], ["accepted", "wrong-state"])])
def test_concurrent_updates_or_duplicate(price_context, ids, expected):
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda value: receive(price_context, value).text, ids))
    assert sorted(replies) == sorted(expected)
    assert snapshot(price_context[0]).state == "awaiting_interval"


@pytest.mark.parametrize("change", [{"lease_token": uuid4()}, {"telegram_user_id": 701}, {"chat_id": 801}, {"text": _PRICE + "?x=1"}, {"target_price_cents": 1}, {"target_price_cents": True}])
def test_divergent_claim_identity_text_or_url_cannot_mutate(price_context, change):
    original = snapshot(price_context[0])
    with pytest.raises(RuntimeError):
        receive(price_context, **change)
    assert snapshot(price_context[0]) == original


def test_invalid_alias_preserves_draft_and_persists_negative_result(price_context):
    engine = price_context[0]
    raw = "https://evil.test/MLB-123"
    with engine.begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}',to_jsonb(CAST(:raw AS text))) WHERE update_id=1"), {"raw": raw})
    original = snapshot(engine)
    assert receive(price_context, text=raw, target_price_cents=None).text == "invalid"
    assert snapshot(engine) == original
    assert receive(price_context, text=raw, target_price_cents=None).text == "invalid"


def test_expired_draft_and_missing_draft_do_not_advance(price_context):
    engine, now, _ = price_context
    original = snapshot(engine)
    assert receive(price_context, observed_at=now + timedelta(hours=1)).text == "absent"
    assert snapshot(engine) == original
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_conversation_drafts"))
    assert receive(price_context, 2).text == "absent"


def test_reply_insertion_failure_rolls_back_advance(price_context):
    original = snapshot(price_context[0])
    with pytest.raises(IntegrityError):
        receive(price_context, replies=RegistrationTargetPriceReplies("", "invalid", "absent", "wrong-state"))
    assert snapshot(price_context[0]) == original
    assert receive(price_context).text == "accepted"


def test_expired_lease_cannot_advance(price_context):
    original = snapshot(price_context[0])
    with price_context[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_expires_at=clock_timestamp()-interval '1 second'"))
    with pytest.raises(RuntimeError, match="Lease"):
        receive(price_context)
    assert snapshot(price_context[0]) == original


def test_cancel_concurrent_with_receive_never_recreates_draft(price_context):
    from argos.infrastructure.database.telegram_conversations import PostgreSQLTelegramConversationDraftRepository
    engine = price_context[0]
    def cancel():
        return PostgreSQLTelegramConversationDraftRepository(engine).cancel_for_owner(telegram_user_id=700)
    with ThreadPoolExecutor(max_workers=2) as pool:
        receiving = pool.submit(receive, price_context)
        cancelling = pool.submit(cancel)
        assert receiving.result().text in {"accepted", "absent"}
        assert cancelling.result() is True
    assert snapshot(engine) is None


