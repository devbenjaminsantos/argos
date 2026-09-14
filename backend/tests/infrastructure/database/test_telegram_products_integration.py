"""Listagem privada e recuperação do snapshot em PostgreSQL real."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from argos.infrastructure.database.telegram_products import PostgreSQLTelegramProductsRepository

_URL = os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(_URL is None, reason="PostgreSQL de teste ausente.")

@pytest.fixture
def context():
    engine = create_engine(_URL)
    now = datetime.now(UTC)
    lease = uuid4()
    cleanup = "TRUNCATE monitored_products, telegram_registration_results, telegram_update_inbox, telegram_conversation_drafts, telegram_users"
    with engine.begin() as c:
        c.execute(text(cleanup))
        c.execute(text("INSERT INTO telegram_users VALUES (700,800,:now,:now)"), {"now": now})
        for update_id in (1, 2):
            c.execute(text("INSERT INTO telegram_update_inbox (update_id,payload,status,received_at,next_attempt_at,lease_token,lease_expires_at) VALUES (:id, CAST(:payload AS jsonb),'processing',:now,:now,:lease,:expires)"),
                {"id": update_id, "payload": '{"message":{"from":{"id":700},"chat":{"id":800,"type":"private"},"text":"/produtos"}}',
                 "now": now, "lease": lease, "expires": now + timedelta(minutes=5)})
    try:
        yield engine, now, lease
    finally:
        with engine.begin() as c:
            c.execute(text(cleanup))
        engine.dispose()


def listing(context, update_id=1, **changes):
    engine, now, lease = context
    args = dict(update_id=update_id, lease_token=lease, telegram_user_id=700,
                chat_id=800, observed_at=now)
    return PostgreSQLTelegramProductsRepository(engine).list_for_update(**(args | changes))


def add_product(context, owner=700, alias="Caneca", slot=1):
    with context[0].begin() as c:
        c.execute(text("INSERT INTO monitored_products (id,telegram_user_id,slot,product_key,url,alias,target_price_cents,interval_hours,created_at) VALUES (:id,:owner,:slot,:key,'https://www.mercadolivre.com.br/p/MLB123',:alias,15000,12,:now)"),
                  dict(id=uuid4(), owner=owner, slot=slot, key=f"MLB{slot}", alias=alias, now=context[1]))


def test_owner_isolation_and_snapshot_recovery(context):
    with context[0].begin() as c:
        c.execute(text("INSERT INTO telegram_users VALUES (701,801,:now,:now)"), dict(now=context[1]))
    add_product(context, 701, "Outro proprietário")
    assert "ainda não cadastrou" in listing(context).text
    add_product(context)
    assert "ainda não cadastrou" in listing(context).text
    reply = listing(context, 2)
    assert "Caneca" in reply.text and "R$ 150,00" in reply.text
    assert "Outro proprietário" not in reply.text
    context[0].dispose()
    with context[0].begin() as c:
        c.execute(text("UPDATE monitored_products SET alias='Alterado' WHERE telegram_user_id=700"))
        c.execute(text("UPDATE telegram_update_inbox SET lease_token=:lease"),dict(lease=context[2]))
    assert listing(context, 2) == reply


def test_same_update_concurrent_uses_one_snapshot(context):
    add_product(context)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: listing(context), range(2)))
    assert replies[0] == replies[1]
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 1


@pytest.mark.parametrize("changes", [{"lease_token":uuid4()}, {"telegram_user_id":701}, {"chat_id":801}])
def test_invalid_claim_has_no_result(context, changes):
    with pytest.raises(RuntimeError):
        listing(context, **changes)
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 0


def test_composed_worker_lists_without_changing_draft(context):
    from argos.config import Settings
    from argos.telegram_worker import build_worker
    add_product(context)
    with context[0].begin() as c:
        c.execute(text("DELETE FROM telegram_update_inbox WHERE update_id=2"))
        c.execute(text("UPDATE telegram_update_inbox SET status='pending',lease_token=NULL,lease_expires_at=NULL"))
        c.execute(text("INSERT INTO telegram_conversation_drafts VALUES (700,'awaiting_url','{}',:now,:now,:expiry,:version)"),dict(now=context[1],expiry=context[1]+timedelta(minutes=15),version=uuid4()))
        original=c.execute(text("SELECT * FROM telegram_conversation_drafts")).one()
    class Sender:
        def send(self, message):
            assert "Caneca" in message.text
    worker=build_worker(Settings(environment="test"),engine=context[0],sender=Sender())
    assert worker.process_next(now=context[1])
    assert not worker.process_next(now=context[1])
    with context[0].connect() as c:
        assert c.execute(text("SELECT * FROM telegram_conversation_drafts")).one()==original
        assert c.scalar(text("SELECT status FROM telegram_update_inbox"))=='completed'


def test_expired_lease_cannot_persist_snapshot(context):
    with context[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_expires_at=clock_timestamp()-interval '1 second'"))
    with pytest.raises(RuntimeError):
        listing(context)
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results"))==0


def test_unregistered_owner_requires_start_and_replay_is_stable(context):
    with context[0].begin() as c:
        c.execute(text("DELETE FROM telegram_users"))
    assert "/start" in listing(context).text
    with context[0].begin() as c:
        c.execute(text("INSERT INTO telegram_users VALUES (700,800,:now,:now)"),dict(now=context[1]))
    assert "/start" in listing(context).text
    assert "ainda não cadastrou" in listing(context,2).text


def test_three_slots_are_listed_in_order(context):
    for slot in (3,1,2):
        add_product(context,alias=f"Produto {slot}",slot=slot)
    reply=listing(context).text
    assert reply.index("1. Produto 1")<reply.index("2. Produto 2")<reply.index("3. Produto 3")


def test_listing_omits_history_and_includes_reused_slot(context):
    add_product(context,alias="Histórico")
    with context[0].begin() as c:
        c.execute(text("UPDATE monitored_products SET removed_at=clock_timestamp()"))
    add_product(context,alias="Ativo")
    reply=listing(context).text
    assert "Ativo" in reply and "Histórico" not in reply
