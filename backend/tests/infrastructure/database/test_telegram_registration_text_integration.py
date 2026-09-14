import os
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text
from argos.application.use_cases.receive_registration_text import ReceiveTelegramRegistrationText
from argos.infrastructure.database.telegram_registration_text import PostgreSQLTelegramRegistrationTextRepository
from tests.infrastructure.database.test_telegram_registration_integration import context
from tests.infrastructure.database.test_telegram_registration_url_integration import url_context, snapshot, _URL

pytestmark = pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None, reason="PostgreSQL de teste ausente.")


def receive(ctx, update_id=1, raw=_URL):
    engine, now, lease = ctx
    return ReceiveTelegramRegistrationText(PostgreSQLTelegramRegistrationTextRepository(engine)).execute(
        update_id=update_id, lease_token=lease, telegram_user_id=700, chat_id=800,
        text=raw, observed_at=now)


def test_replay_across_url_alias_restart_and_cancel(url_context):
    engine = url_context[0]
    original = snapshot(engine)
    first = receive(url_context)
    assert "Envie um apelido" in first.text
    advanced = snapshot(engine)
    assert receive(url_context) == first
    assert snapshot(engine) == advanced
    with engine.begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}',to_jsonb(CAST(:raw AS text))) WHERE update_id=2"), {"raw": " Caneca   Kitty "})
    second = receive(url_context, 2, " Caneca   Kitty ")
    assert "Apelido registrado" in second.text
    final = snapshot(engine)
    assert final.state == "awaiting_target_price"
    assert final.data == {"url": _URL, "alias": "Caneca Kitty"}
    assert final.expires_at == original.expires_at
    engine.dispose()
    assert receive(url_context) == first
    assert receive(url_context, 2, " Caneca   Kitty ") == second
    assert snapshot(engine) == final
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_conversation_drafts"))
    assert receive(url_context, 2, " Caneca   Kitty ") == second
    assert snapshot(engine) is None


def test_same_update_concurrently_advances_once(url_context):
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: receive(url_context), [1, 1]))
    assert replies[0] == replies[1]
    assert snapshot(url_context[0]).state == "awaiting_alias"


def test_new_url_in_alias_step_preserves_draft(url_context):
    receive(url_context)
    original = snapshot(url_context[0])
    assert "Envie um apelido" in receive(url_context, 2).text
    assert snapshot(url_context[0]) == original
