"""Cancelamento durável sob leases e concorrência PostgreSQL reais."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from argos.application.ports.telegram_cancellation import CancellationReplies
from argos.infrastructure.database.telegram_cancellation import PostgreSQLTelegramCancellationRepository

_URL=os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark=pytest.mark.skipif(_URL is None,reason="PostgreSQL de teste ausente.")
_REPLIES=CancellationReplies("cancelled","nothing")

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
                {"id": update_id, "payload": '{"message":{"from":{"id":700},"chat":{"id":800,"type":"private"},"text":"/cancelar"}}',
                 "now": now, "lease": lease, "expires": now + timedelta(minutes=5)})
    try:
        yield engine, now, lease
    finally:
        with engine.begin() as c:
            c.execute(text(cleanup))
        engine.dispose()


def cancel(context, update_id=1, **changes):
    engine,now,lease=context
    args=dict(update_id=update_id,lease_token=lease,telegram_user_id=700,
              chat_id=800,observed_at=now,replies=_REPLIES)
    return PostgreSQLTelegramCancellationRepository(engine).cancel_for_update(**(args|changes))


def new_draft(context, owner=700):
    version=uuid4()
    with context[0].begin() as c:
        c.execute(text("INSERT INTO telegram_conversation_drafts VALUES (:owner,'awaiting_url','{}',:now,:now,:expiry,:version)"),
                  dict(owner=owner,now=context[1],expiry=context[1]+timedelta(minutes=15),version=version))
    return version


def test_recovered_cancel_preserves_new_operation(context):
    new_draft(context)
    assert cancel(context).text=='cancelled'
    version=new_draft(context)
    context[0].dispose()
    lease=uuid4()
    with context[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_token=:lease WHERE update_id=1"),dict(lease=lease))
    assert cancel(context,lease_token=lease).text=='cancelled'
    with context[0].connect() as c:
        assert c.scalar(text("SELECT version FROM telegram_conversation_drafts"))==version
    assert cancel(context,2).text=='cancelled'


def test_no_operation_reply_stays_stable_after_new_draft(context):
    assert cancel(context).text=='nothing'
    version=new_draft(context)
    assert cancel(context).text=='nothing'
    with context[0].connect() as c:
        assert c.scalar(text("SELECT version FROM telegram_conversation_drafts"))==version


def test_concurrent_same_update_has_one_result(context):
    new_draft(context)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda _:cancel(context).text,range(2)))
    assert replies==['cancelled','cancelled']
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results"))==1
        assert c.scalar(text("SELECT count(*) FROM telegram_conversation_drafts"))==0


def test_different_updates_serialize_cancel(context):
    new_draft(context)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda value:cancel(context,value).text,[1,2]))
    assert sorted(replies)==['cancelled','nothing']


def test_reply_failure_rolls_back_cancel(context):
    version=new_draft(context)
    with pytest.raises(IntegrityError):
        cancel(context,replies=CancellationReplies('', 'nothing'))
    with context[0].connect() as c:
        assert c.scalar(text("SELECT version FROM telegram_conversation_drafts"))==version
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results"))==0


@pytest.mark.parametrize('changes',[{'lease_token':uuid4()},{'telegram_user_id':701},{'chat_id':801}])
def test_invalid_claim_preserves_draft(context,changes):
    version=new_draft(context)
    with pytest.raises(RuntimeError):
        cancel(context,**changes)
    with context[0].connect() as c:
        assert c.scalar(text("SELECT version FROM telegram_conversation_drafts"))==version
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results"))==0


def test_expired_lease_preserves_draft(context):
    new_draft(context)
    with context[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_expires_at=clock_timestamp()-interval '1 second'"))
    with pytest.raises(RuntimeError):
        cancel(context)


def test_other_owner_and_products_are_preserved(context):
    with context[0].begin() as c:
        c.execute(text("INSERT INTO telegram_users VALUES (701,801,:now,:now)"),dict(now=context[1]))
        c.execute(text("INSERT INTO monitored_products VALUES (:id,700,1,'MLB123','https://www.mercadolivre.com.br/p/MLB123','Caneca',15000,12,:now)"),dict(id=uuid4(),now=context[1]))
    new_draft(context)
    other=new_draft(context,701)
    assert cancel(context).text=='cancelled'
    with context[0].connect() as c:
        assert c.scalar(text("SELECT version FROM telegram_conversation_drafts"))==other
        assert c.scalar(text("SELECT count(*) FROM monitored_products"))==1


def test_worker_interrupted_after_commit_preserves_new_draft(context):
    from argos.config import Settings
    from argos.telegram_worker import build_worker
    new_draft(context)
    with context[0].begin() as c:
        c.execute(text("DELETE FROM telegram_update_inbox WHERE update_id=2"))
        c.execute(text("UPDATE telegram_update_inbox SET status='pending',lease_token=NULL,lease_expires_at=NULL"))
    class Sender:
        fail=True
        messages=[]
        def send(self,message):
            self.messages.append(message)
            if self.fail:
                raise RuntimeError('interrupted')
    sender=Sender()
    worker=build_worker(Settings(environment='test'),engine=context[0],sender=sender)
    with pytest.raises(RuntimeError,match='interrupted'):
        worker.process_next(now=context[1])
    version=new_draft(context)
    sender.fail=False
    context[0].dispose()
    recovered=build_worker(Settings(environment='test'),engine=context[0],sender=sender)
    assert recovered.process_next(now=context[1]+timedelta(minutes=2))
    assert sender.messages[0]==sender.messages[1]
    with context[0].connect() as c:
        assert c.scalar(text("SELECT version FROM telegram_conversation_drafts"))==version
        assert c.execute(text("SELECT status,attempt_count FROM telegram_update_inbox")).one()==('completed',2)
