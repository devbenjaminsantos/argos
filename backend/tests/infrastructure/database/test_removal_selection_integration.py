"""Seleção vinculada ao UUID original e resposta recuperável."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from tests.infrastructure.database.test_telegram_removal_integration import context,removing,removal,draft
from tests.infrastructure.database.test_monitored_products_integration import add
from argos.infrastructure.database.telegram_removal_selection import PostgreSQLTelegramRemovalSelectionRepository

pytestmark=pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None,reason="PostgreSQL de teste ausente.")

@pytest.fixture
def selecting(removing):
    add(removing)
    removal(removing)
    with removing[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}','\"1\"') WHERE update_id=2"))
    return removing


def select(ctx,raw='1',**changes):
    args=dict(update_id=2,lease_token=ctx[2],telegram_user_id=700,chat_id=800,text=raw,observed_at=ctx[1])
    return PostgreSQLTelegramRemovalSelectionRepository(ctx[0]).select_for_update(**(args|changes))


def test_proposal_keeps_expiry_and_replays_after_restart(selecting):
    original=draft(selecting)
    reply=select(selecting)
    proposal=draft(selecting)
    assert proposal.state=='awaiting_removal_confirmation'
    assert proposal.version!=original.version and proposal.lifetime==original.lifetime
    assert proposal.data['product_id']==original.data['products_by_slot']['1']
    assert proposal.version.hex in reply.text
    selecting[0].dispose()
    assert select(selecting)==reply and draft(selecting)==proposal
    with selecting[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NULL"))==1


@pytest.mark.parametrize('raw',['0','2','1.0','confirmar'])
def test_invalid_selection_preserves_map(selecting,raw):
    original=draft(selecting)
    with selecting[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET payload=jsonb_set(payload,'{message,text}',to_jsonb(CAST(:raw AS text))) WHERE update_id=2"),dict(raw=raw))
    assert 'Envie um número' in select(selecting,raw).text
    assert draft(selecting)==original


def test_reused_slot_does_not_select_replacement(selecting):
    with selecting[0].begin() as c:
        c.execute(text("UPDATE monitored_products SET removed_at=clock_timestamp()"))
    add(selecting,alias='Substituto')
    assert 'indisponível' in select(selecting).text
    assert draft(selecting) is None
    with selecting[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NULL"))==1


def test_same_update_concurrent_has_one_proposal(selecting):
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies=list(pool.map(lambda _:select(selecting),range(2)))
    assert replies[0]==replies[1]
    assert draft(selecting).version.hex in replies[0].text


def test_response_failure_rolls_back_proposal(selecting,monkeypatch):
    import argos.infrastructure.database.telegram_removal_selection as module
    original=draft(selecting)
    monkeypatch.setattr(module,'format_removal_proposal',lambda *args:'')
    with pytest.raises(IntegrityError):
        select(selecting)
    assert draft(selecting)==original


def test_expired_draft_and_foreign_claim_cannot_select(selecting):
    with pytest.raises(RuntimeError):
        select(selecting,telegram_user_id=701)
    assert 'Não há remoção ativa' in select(selecting,observed_at=selecting[1]+timedelta(hours=1)).text
    assert draft(selecting).state=='awaiting_product_to_remove'
