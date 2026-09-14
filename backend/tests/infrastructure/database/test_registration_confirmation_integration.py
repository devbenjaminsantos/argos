import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from argos.application.ports.telegram_registration_confirmation import RegistrationConfirmationReplies
from argos.infrastructure.database.telegram_registration_confirmation import PostgreSQLTelegramRegistrationConfirmationRepository
from tests.infrastructure.database.test_telegram_registration_integration import context,begin
from tests.infrastructure.database.test_telegram_registration_url_integration import snapshot

pytestmark=pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None,reason="PostgreSQL de teste ausente.")
_REPLIES=RegistrationConfirmationReplies("created","corrected","duplicate","limit","invalid-data","invalid-action","absent","wrong-state")
_DATA={"url":"https://mercadolivre.com.br/p/MLB123?variation=7","alias":"Caneca","target_price_cents":15000,"interval_hours":12}


@pytest.fixture
def confirming(context):
    begin(context)
    with context[0].begin() as c:
        c.execute(text("DELETE FROM telegram_registration_results"))
        c.execute(text("UPDATE telegram_conversation_drafts SET state='awaiting_confirmation',data=CAST(:data AS jsonb)"),{"data":json.dumps(_DATA)})
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}','\"confirmar\"')"))
    return context


def confirm(ctx,update_id=1,**changes):
    engine,now,lease=ctx
    return PostgreSQLTelegramRegistrationConfirmationRepository(engine).confirm_for_update(**(dict(update_id=update_id,lease_token=lease,telegram_user_id=700,chat_id=800,text="confirmar",observed_at=now,replies=_REPLIES)|changes))


def count(engine):
    with engine.connect() as c: return c.scalar(text("SELECT count(*) FROM monitored_products"))


def test_creation_and_replay_after_restart_new_lease_and_cancel(confirming):
    engine,now,_=confirming
    assert confirm(confirming).text=="created"
    assert snapshot(engine) is None
    assert count(engine)==1
    with engine.begin() as c:
        lease=uuid4()
        c.execute(text("UPDATE telegram_update_inbox SET lease_token=:lease WHERE update_id=1"),{"lease":lease})
        row=c.execute(text("SELECT product_key,target_price_cents,interval_hours FROM monitored_products")).one()
        assert row==("MLB123",15000,12)
    engine.dispose()
    assert confirm((engine,now,lease)).text=="created"
    assert count(engine)==1
    assert snapshot(engine) is None


@pytest.mark.parametrize("ids",[[1,1],[1,2]])
def test_concurrent_confirmation_creates_once(confirming,ids):
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda id:confirm(confirming,id).text,ids))
    assert results.count("created")== (2 if ids==[1,1] else 1)
    assert count(confirming[0])==1


def test_correction_preserves_expiration_and_replays(confirming):
    original=snapshot(confirming[0])
    with confirming[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}','\"corrigir\"') WHERE update_id=1"))
    assert confirm(confirming,text="corrigir").text=="corrected"
    final=snapshot(confirming[0])
    assert final.state=="awaiting_url" and final.data=={}
    assert final.version!=original.version and final.expires_at==original.expires_at
    assert confirm(confirming,text="corrigir").text=="corrected"
    assert snapshot(confirming[0])==final and count(confirming[0])==0


def test_reply_failure_rolls_back_product_and_draft(confirming):
    from dataclasses import replace
    original=snapshot(confirming[0])
    with pytest.raises(IntegrityError): confirm(confirming,replies=replace(_REPLIES,created=""))
    assert count(confirming[0])==0 and snapshot(confirming[0])==original
    assert confirm(confirming).text=="created"


@pytest.mark.parametrize("changes",[{"lease_token":uuid4()},{"telegram_user_id":701},{"chat_id":801},{"text":"corrigir"}])
def test_invalid_claim_cannot_create(confirming,changes):
    with pytest.raises(RuntimeError): confirm(confirming,**changes)
    assert count(confirming[0])==0


def test_expired_draft_and_invalid_stored_data(confirming):
    assert confirm(confirming,observed_at=confirming[1]+timedelta(hours=1)).text=="absent"
    with confirming[0].begin() as c:
        c.execute(text("UPDATE telegram_conversation_drafts SET data='{}'::jsonb"))
    assert confirm(confirming,2).text=="invalid-data"
    assert count(confirming[0])==0


def test_duplicate_by_key_preserves_draft(confirming):
    assert confirm(confirming).text=="created"
    with confirming[0].begin() as c:
        c.execute(text("INSERT INTO telegram_conversation_drafts (telegram_user_id,state,data,created_at,updated_at,expires_at,version) VALUES (700,'awaiting_confirmation',CAST(:data AS jsonb),:now,:now,:expires,:version)"),{"data":json.dumps(_DATA|{"url":"https://produto.mercadolivre.com.br/MLB-123-slug?variation=8"}),"now":confirming[1],"expires":confirming[1]+timedelta(minutes=15),"version":uuid4()})
    original=snapshot(confirming[0])
    assert confirm(confirming,2).text=="duplicate"
    assert snapshot(confirming[0])==original and count(confirming[0])==1


@pytest.mark.parametrize("occupied,expected",[(2,{"created","absent"}),(3,{"limit"})])
def test_concurrent_limit_preserves_three_slots(confirming,occupied,expected):
    from sqlalchemy import insert
    from argos.infrastructure.database.models import MonitoredProductRecord
    with confirming[0].begin() as c:
        for slot in range(1,occupied+1):
            c.execute(insert(MonitoredProductRecord).values(id=uuid4(),telegram_user_id=700,slot=slot,product_key=f"MLB{slot}",url=f"https://mercadolivre.com.br/p/MLB{slot}",alias="Existing",target_price_cents=15000,interval_hours=12,created_at=confirming[1]))
    original=snapshot(confirming[0])
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda id:confirm(confirming,id).text,[1,2]))
    assert set(replies)==expected and count(confirming[0])==3
    if occupied==3: assert snapshot(confirming[0])==original


def test_expired_lease_rolls_back(confirming):
    original=snapshot(confirming[0])
    with confirming[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_expires_at=clock_timestamp()-interval '1 second'"))
    with pytest.raises(RuntimeError,match="Lease"): confirm(confirming)
    assert snapshot(confirming[0])==original and count(confirming[0])==0
