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


def test_price_invalid_valid_replay_and_unavailable_step(url_context):
    engine = url_context[0]
    receive(url_context)
    with engine.begin() as c:
        c.execute(text("UPDATE telegram_conversation_drafts SET state='awaiting_target_price',data=data || '{\"alias\":\"Caneca Kitty\"}'::jsonb"))
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}', '\"1.50\"') WHERE update_id=2"))
    original = snapshot(engine)
    invalid = receive(url_context, 2, "1.50")
    assert "Envie um preço" in invalid.text
    assert snapshot(engine) == original
    with engine.begin() as c:
        c.execute(text("INSERT INTO telegram_update_inbox (update_id,payload,status,received_at,next_attempt_at,lease_token,lease_expires_at) SELECT 3,jsonb_set(payload,'{message,text}','\"R$ 2.500,90\"'),'processing',received_at,next_attempt_at,lease_token,lease_expires_at FROM telegram_update_inbox WHERE update_id=2"))
    accepted = receive(url_context, 3, "R$ 2.500,90")
    assert "Preço-alvo R$ 2.500,90 registrado" in accepted.text
    assert "intervalo será liberado" in accepted.text
    final = snapshot(engine)
    assert final.state == "awaiting_interval"
    assert final.data == {"url": _URL,"alias":"Caneca Kitty","target_price_cents":250090}
    assert final.expires_at == original.expires_at
    engine.dispose()
    assert receive(url_context, 2, "1.50") == invalid
    assert receive(url_context, 3, "R$ 2.500,90") == accepted
    assert snapshot(engine) == final
    with engine.begin() as c:
        c.execute(text("INSERT INTO telegram_update_inbox (update_id,payload,status,received_at,next_attempt_at,lease_token,lease_expires_at) SELECT 4,payload,status,received_at,next_attempt_at,lease_token,lease_expires_at FROM telegram_update_inbox WHERE update_id=3"))
    assert "etapa ainda não disponível" in receive(url_context, 4, "R$ 2.500,90").text
    assert snapshot(engine) == final


def test_composed_worker_receives_price(url_context):
    from datetime import UTC, datetime
    from argos.config import Settings
    from argos.telegram_worker import build_worker
    engine = url_context[0]
    with engine.begin() as c:
        c.execute(text("UPDATE telegram_conversation_drafts SET state='awaiting_target_price',data='{\"url\":\"https://mercadolivre.com.br/p/MLB123\",\"alias\":\"Caneca\"}'::jsonb"))
        c.execute(text("DELETE FROM telegram_update_inbox WHERE update_id=2"))
        c.execute(text("UPDATE telegram_update_inbox SET status='pending',lease_token=NULL,lease_expires_at=NULL,payload=jsonb_set(payload,'{message,text}','\"2500,90\"')"))
    class Sender:
        def __init__(self):
            self.messages=[]
        def send(self,message):
            self.messages.append(message)
    sender=Sender()
    assert build_worker(Settings(environment="test"),engine=engine,sender=sender).process_next(now=datetime.now(UTC))
    assert "R$ 2.500,90" in sender.messages[0].text
    assert snapshot(engine).data["target_price_cents"] == 250090
    with engine.connect() as c:
        assert c.scalar(text("SELECT status FROM telegram_update_inbox")) == "completed"
