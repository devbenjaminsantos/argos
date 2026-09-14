"""Abertura de remoção durável, sem desativação de produtos."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import text
from argos.application.ports.telegram_removal import BeginRemovalReplies
from argos.infrastructure.database.telegram_removal import PostgreSQLTelegramRemovalRepository
from tests.infrastructure.database.test_telegram_registration_integration import context, begin
from tests.infrastructure.database.test_monitored_products_integration import add

pytestmark=pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None,reason="PostgreSQL de teste ausente.")
_REPLIES=BeginRemovalReplies('empty','active','register')

@pytest.fixture
def removing(context):
    with context[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}','\"/remover\"')"))
    return context


def removal(ctx,update_id=1,**changes):
    args=dict(update_id=update_id,lease_token=ctx[2],telegram_user_id=700,chat_id=800,
              observed_at=ctx[1],draft_lifetime=timedelta(minutes=15),replies=_REPLIES)
    return PostgreSQLTelegramRemovalRepository(ctx[0]).begin_for_update(**(args|changes))


def draft(ctx):
    with ctx[0].connect() as c:
        return c.execute(text("SELECT state,data,version,expires_at-created_at AS lifetime FROM telegram_conversation_drafts WHERE telegram_user_id=700")).one_or_none()


def test_list_mapping_replay_and_restart_preserve_original(removing):
    add(removing)
    reply=removal(removing)
    original=draft(removing)
    assert original.state=='awaiting_product_to_remove'
    assert original.lifetime==timedelta(minutes=15)
    with removing[0].connect() as c:
        product=str(c.scalar(text("SELECT id FROM monitored_products")))
    assert original.data=={'products_by_slot':{'1':product}}
    with removing[0].begin() as c:
        c.execute(text("UPDATE monitored_products SET removed_at=clock_timestamp()"))
    add(removing,alias='Novo')
    removing[0].dispose()
    assert removal(removing)==reply and draft(removing)==original
    assert 'Novo' not in reply.text


def test_empty_and_unregistered_results_are_durable(removing):
    assert removal(removing).text=='empty'
    assert draft(removing) is None
    add(removing)
    assert removal(removing).text=='empty'
    with removing[0].begin() as c:
        c.execute(text("DELETE FROM monitored_products"))
        c.execute(text("DELETE FROM telegram_users"))
    assert removal(removing,2).text=='register'
    assert draft(removing) is None


def test_active_registration_is_preserved(removing):
    with removing[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}','\"/adicionar\"') WHERE update_id=1"))
    begin(removing)
    original=draft(removing)
    add(removing)
    assert removal(removing,2).text=='active'
    assert draft(removing)==original


def test_same_update_concurrency_has_one_draft_and_result(removing):
    add(removing)
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda _:removal(removing),range(2)))
    assert replies[0]==replies[1]
    with removing[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results"))==1
        assert c.scalar(text("SELECT count(*) FROM telegram_conversation_drafts"))==1


@pytest.mark.parametrize('changes',[{'lease_token':uuid4()},{'telegram_user_id':701},{'chat_id':801}])
def test_invalid_claim_cannot_open_draft(removing,changes):
    add(removing)
    with pytest.raises(RuntimeError):
        removal(removing,**changes)
    assert draft(removing) is None


def test_other_owner_and_history_are_not_presented(removing):
    add(removing,removed_at=removing[1],alias='Histórico')
    with removing[0].begin() as c:
        c.execute(text("INSERT INTO telegram_users VALUES (701,801,:now,:now)"),dict(now=removing[1]))
    add(removing,telegram_user_id=701,alias='Outro')
    assert removal(removing).text=='empty'
    add(removing,alias='Próprio')
    reply=removal(removing,2).text
    assert 'Próprio' in reply and 'Outro' not in reply and 'Histórico' not in reply


def test_reply_failure_rolls_back_opening(removing,monkeypatch):
    from sqlalchemy.exc import IntegrityError
    import argos.infrastructure.database.telegram_removal as module
    add(removing)
    monkeypatch.setattr(module,'format_removal_selection',lambda products:'')
    with pytest.raises(IntegrityError):
        removal(removing)
    assert draft(removing) is None


def test_expired_lease_cannot_open_removal(removing):
    add(removing)
    with removing[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_expires_at=clock_timestamp()-interval '1 second'"))
    with pytest.raises(RuntimeError):
        removal(removing)
    assert draft(removing) is None
