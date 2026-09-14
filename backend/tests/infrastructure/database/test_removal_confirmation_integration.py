"""Confirmação, replay e rollback de remoção lógica em PostgreSQL."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.infrastructure.database.test_removal_selection_integration import context,removing,selecting,select,draft
from tests.infrastructure.database.test_monitored_products_integration import add
from argos.infrastructure.database.telegram_removal_confirmation import PostgreSQLTelegramRemovalConfirmationRepository

pytestmark=pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None,reason="PostgreSQL de teste ausente.")

@pytest.fixture
def confirming(selecting):
    select(selecting)
    raw=f"remover {draft(selecting).version.hex}"
    with selecting[0].begin() as c:
        c.execute(text("DELETE FROM telegram_registration_results WHERE update_id=2"))
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}',to_jsonb(CAST(:raw AS text))) WHERE update_id=2"),dict(raw=raw))
    return selecting,raw


def confirm(ctx,**changes):
    context,raw=ctx
    args=dict(update_id=2,lease_token=context[2],telegram_user_id=700,chat_id=800,text=raw,observed_at=context[1])
    return PostgreSQLTelegramRemovalConfirmationRepository(context[0]).confirm_for_update(**(args|changes))


def test_removal_and_recovery_never_touch_replacement(confirming):
    ctx,_=confirming
    reply=confirm(confirming)
    assert 'Produto removido' in reply.text and draft(ctx) is None
    add(ctx,alias='Substituto')
    ctx[0].dispose()
    lease=uuid4()
    with ctx[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_token=:lease WHERE update_id=2"),dict(lease=lease))
    assert confirm(confirming,lease_token=lease)==reply
    with ctx[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NULL"))==1
        assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NOT NULL"))==1


@pytest.mark.parametrize('raw',['remover','confirmar',f'remover {uuid4().hex}'])
def test_wrong_code_preserves_proposal(confirming,raw):
    ctx,_=confirming
    original=draft(ctx)
    with ctx[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}',to_jsonb(CAST(:raw AS text))) WHERE update_id=2"),dict(raw=raw))
    assert 'código completo' in confirm(confirming,text=raw).text
    assert draft(ctx)==original


def test_concurrent_same_update_removes_once(confirming):
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda _:confirm(confirming),range(2)))
    assert replies[0]==replies[1]
    assert draft(confirming[0]) is None


def test_reply_failure_rolls_back_removal_and_consumption(confirming,monkeypatch):
    import argos.infrastructure.database.telegram_removal_confirmation as module
    ctx,_=confirming
    original=draft(ctx)
    monkeypatch.setattr(module,'REMOVED_TEXT','')
    with pytest.raises(IntegrityError):
        confirm(confirming)
    assert draft(ctx)==original
    with ctx[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NOT NULL"))==0


def test_old_code_cannot_confirm_new_proposal(confirming):
    ctx,_=confirming
    with ctx[0].begin() as c:
        c.execute(text("UPDATE telegram_conversation_drafts SET version=:version"),dict(version=uuid4()))
    assert 'código completo' in confirm(confirming).text
    assert draft(ctx) is not None


def test_product_already_removed_consumes_without_replacement(confirming):
    ctx,_=confirming
    with ctx[0].begin() as c:
        c.execute(text("UPDATE monitored_products SET removed_at=clock_timestamp()"))
    add(ctx,alias='Substituto')
    assert 'indisponível' in confirm(confirming).text
    assert draft(ctx) is None
    with ctx[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NULL"))==1


def test_expired_proposal_or_foreign_claim_cannot_remove(confirming):
    with pytest.raises(RuntimeError):
        confirm(confirming,telegram_user_id=701)
    assert 'Não há remoção ativa' in confirm(confirming,observed_at=confirming[0][1]+timedelta(hours=1)).text
    assert draft(confirming[0]) is not None
