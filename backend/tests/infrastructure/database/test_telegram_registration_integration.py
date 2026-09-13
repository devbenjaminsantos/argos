"""Atomicidade de cadastro sob leases e concorrência PostgreSQL reais."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from argos.application.ports.telegram_registration import BeginRegistrationReplies
from argos.infrastructure.database.telegram_registration import PostgreSQLTelegramRegistrationRepository

_URL = os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(_URL is None, reason="PostgreSQL de teste ausente.")
_REPLIES = BeginRegistrationReplies("started", "active", "register-first")


@pytest.fixture
def context():
    engine = create_engine(_URL)
    now = datetime.now(UTC)
    lease = uuid4()
    cleanup = "TRUNCATE telegram_registration_results, telegram_update_inbox, telegram_conversation_drafts, telegram_users"
    with engine.begin() as c:
        c.execute(text(cleanup))
        c.execute(text("INSERT INTO telegram_users VALUES (700,800,:now,:now)"), {"now": now})
        for update_id in (1, 2):
            c.execute(text("INSERT INTO telegram_update_inbox (update_id,payload,status,received_at,next_attempt_at,lease_token,lease_expires_at) VALUES (:id, CAST(:payload AS jsonb),'processing',:now,:now,:lease,:expires)"),
                {"id": update_id, "payload": '{"message":{"from":{"id":700},"chat":{"id":800,"type":"private"},"text":"/adicionar"}}',
                 "now": now, "lease": lease, "expires": now + timedelta(minutes=5)})
    try:
        yield engine, now, lease
    finally:
        with engine.begin() as c:
            c.execute(text(cleanup))
        engine.dispose()


def begin(context, update_id=1, **changes):
    engine, now, lease = context
    args = dict(update_id=update_id, lease_token=lease, telegram_user_id=700,
                chat_id=800, observed_at=now, draft_lifetime=timedelta(minutes=15), replies=_REPLIES)
    return PostgreSQLTelegramRegistrationRepository(engine).begin_for_update(**(args | changes))


def test_replay_after_pool_restart_and_cancel_does_not_recreate(context):
    engine, _, _ = context
    assert begin(context).text == "started"
    with engine.begin() as c:
        original = c.execute(text("SELECT version,expires_at FROM telegram_conversation_drafts")).one()
    assert begin(context).text == "started"
    with engine.begin() as c:
        assert c.execute(text("SELECT version,expires_at FROM telegram_conversation_drafts")).one() == original
        c.execute(text("DELETE FROM telegram_conversation_drafts"))
    engine.dispose()
    recovered_lease = uuid4()
    with engine.begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_token=:lease WHERE update_id=1"), {"lease": recovered_lease})
    assert begin((engine, context[1], recovered_lease)).text == "started"
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_conversation_drafts")) == 0


def test_concurrent_updates_create_one_draft_and_preserve_active(context):
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda value: begin(context, value).text, [1, 2]))
    assert sorted(replies) == ["active", "started"]
    engine, _, _ = context
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_conversation_drafts")) == 1
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 2


def test_same_update_concurrently_reuses_one_result(context):
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(lambda _: begin(context).text, [1, 2]))
    assert replies == ["started", "started"]
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 1


def test_result_insertion_failure_rolls_back_draft(context):
    with pytest.raises(IntegrityError):
        begin(context, replies=BeginRegistrationReplies("", "active", "register-first"))
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_conversation_drafts")) == 0
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 0
    assert begin(context).text == "started"


@pytest.mark.parametrize("changes", [{"lease_token": uuid4()}, {"telegram_user_id": 701}, {"chat_id": 801}])
def test_invalid_lease_or_identity_cannot_mutate(context, changes):
    with pytest.raises(RuntimeError):
        begin(context, **changes)
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 0
        assert c.scalar(text("SELECT count(*) FROM telegram_conversation_drafts")) == 0


def test_expired_lease_is_rejected(context):
    with context[0].begin() as c:
        c.execute(text("UPDATE telegram_update_inbox SET lease_expires_at=clock_timestamp()-interval '1 second'"))
    with pytest.raises(RuntimeError, match="Lease"):
        begin(context)


def test_registration_required_result_is_stable(context):
    with context[0].begin() as c:
        c.execute(text("DELETE FROM telegram_users"))
    assert begin(context).text == "register-first"
    with context[0].begin() as c:
        c.execute(text("INSERT INTO telegram_users VALUES (700,800,:now,:now)"), {"now": context[1]})
    assert begin(context).text == "register-first"
    assert begin(context, 2).text == "started"



def test_results_are_immutable_for_runtime_and_private(context):
    with context[0].connect() as c:
        for privilege in ("SELECT", "INSERT"):
            assert c.scalar(text("SELECT has_table_privilege('argos_runtime', 'telegram_registration_results', :privilege)"), {"privilege": privilege})
        for privilege in ("UPDATE", "DELETE"):
            assert not c.scalar(text("SELECT has_table_privilege('argos_runtime', 'telegram_registration_results', :privilege)"), {"privilege": privilege})
        for role in ("anon", "authenticated", "service_role"):
            assert not c.scalar(text("SELECT has_table_privilege(:role, 'telegram_registration_results', 'SELECT')"), {"role": role})


def test_downgrade_refuses_existing_results(context, monkeypatch):
    from alembic import command
    from alembic.config import Config
    monkeypatch.setenv("ARGOS_ENVIRONMENT", "test")
    monkeypatch.setenv("ARGOS_MIGRATION_DATABASE_URL", _URL)
    assert begin(context).text == "started"
    with pytest.raises(RuntimeError, match="downgrade destrutivo recusado"):
        command.downgrade(Config("alembic.ini"), "20260913_06")
    assert begin(context).text == "started"


@pytest.mark.parametrize("interrupted", [False, True])
def test_composed_worker_recovers_persisted_reply_without_renewing_draft(context, interrupted):
    from argos.application.ports.telegram_messages import TelegramDeliveryError
    from argos.config import Settings
    from argos.telegram_worker import build_worker

    engine, now, _ = context
    with engine.begin() as c:
        c.execute(text("DELETE FROM telegram_update_inbox WHERE update_id=2"))
        c.execute(text("UPDATE telegram_update_inbox SET status='pending',lease_token=NULL,lease_expires_at=NULL"))

    class Sender:
        def __init__(self):
            self.messages = []
            self.fail = True

        def send(self, message):
            self.messages.append(message)
            if self.fail:
                if interrupted:
                    raise RuntimeError("Interrupção simulada antes do envio")
                raise TelegramDeliveryError("telegram_rate_limited", retryable=True)

    sender = Sender()
    worker = build_worker(Settings(environment="test"), engine=engine, sender=sender)
    if interrupted:
        with pytest.raises(RuntimeError, match="Interrupção simulada"):
            worker.process_next(now=now)
    else:
        assert worker.process_next(now=now)
    with engine.connect() as c:
        original = c.execute(text("SELECT version,expires_at FROM telegram_conversation_drafts")).one()
        assert c.scalar(text("SELECT status FROM telegram_update_inbox")) == ("processing" if interrupted else "pending")
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 1
    engine.dispose()
    sender.fail = False
    recovered = build_worker(Settings(environment="test"), engine=engine, sender=sender)
    assert recovered.process_next(now=now + timedelta(minutes=2))
    assert sender.messages[0] == sender.messages[1]
    with engine.connect() as c:
        assert c.execute(text("SELECT version,expires_at FROM telegram_conversation_drafts")).one() == original
        assert c.scalar(text("SELECT count(*) FROM telegram_registration_results")) == 1
        assert c.execute(text("SELECT status,attempt_count FROM telegram_update_inbox")).one() == ("completed", 2)
