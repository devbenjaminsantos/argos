"""Garantias de admissão sob transações e concorrência PostgreSQL reais."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import StatementError

from argos.application.ports.telegram_admission import TelegramAdmissionResult as Result
from argos.infrastructure.database.telegram_admission import PostgreSQLTelegramAdmissionRepository

_DATABASE_URL = os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(_DATABASE_URL is None, reason="PostgreSQL de teste ausente.")
_NOW = datetime(2026, 9, 12, tzinfo=UTC)


@pytest.fixture
def engine():
    db = create_engine(_DATABASE_URL, pool_size=25, max_overflow=0)
    with db.begin() as connection:
        connection.execute(text("TRUNCATE telegram_admissions, telegram_admission_owners, telegram_update_inbox"))
    try:
        yield db
    finally:
        with db.begin() as connection:
            connection.execute(text("TRUNCATE telegram_admissions, telegram_admission_owners, telegram_update_inbox"))
        db.dispose()


def admit(engine, update_id, owner=700, now=_NOW, payload=None):
    return PostgreSQLTelegramAdmissionRepository(engine).admit(
        update_id=update_id, telegram_user_id=owner, received_at=now,
        payload={} if payload is None else payload,
        maximum_commands=10, window=timedelta(seconds=60),
    )


def counts(engine):
    with engine.connect() as connection:
        return tuple(connection.execute(text(
            "SELECT (SELECT count(*) FROM telegram_admissions), "
            "(SELECT count(*) FROM telegram_update_inbox)"
        )).one())


def test_limit_duplicates_boundary_and_owner_isolation(engine):
    for update_id in range(10):
        assert admit(engine, update_id) is Result.ADMITTED
    assert admit(engine, 10) is Result.RATE_LIMITED
    assert admit(engine, 0) is Result.DUPLICATE
    assert admit(engine, 10, now=_NOW + timedelta(seconds=60)) is Result.DUPLICATE
    assert admit(engine, 11, owner=701) is Result.ADMITTED
    assert admit(engine, 12, now=_NOW + timedelta(seconds=59)) is Result.RATE_LIMITED
    assert admit(engine, 13, now=_NOW + timedelta(seconds=60)) is Result.ADMITTED
    assert counts(engine) == (14, 12)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT decision FROM telegram_admissions WHERE update_id=10")) == "rate_limited"
        assert connection.scalar(text("SELECT count(*) FROM telegram_users WHERE telegram_user_id=700")) == 0


def test_concurrent_commands_cannot_exceed_limit(engine):
    barrier = Barrier(20)
    def execute(update_id):
        barrier.wait(timeout=15)
        return admit(engine, update_id)
    with ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(execute, range(20)))
    assert results.count(Result.ADMITTED) == 10
    assert results.count(Result.RATE_LIMITED) == 10
    assert counts(engine) == (20, 10)


def test_concurrent_duplicate_across_owners_creates_only_one_work_item(engine):
    barrier = Barrier(2)
    def execute(owner):
        barrier.wait(timeout=15)
        return admit(engine, 1, owner=owner)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, [700, 701]))
    assert results.count(Result.ADMITTED) == 1
    assert results.count(Result.DUPLICATE) == 1
    assert counts(engine) == (1, 1)


def test_stale_timestamps_cannot_bypass_full_window(engine):
    for update_id in range(10):
        assert admit(engine, update_id, now=_NOW + timedelta(seconds=120)) is Result.ADMITTED
    assert admit(engine, 10, now=_NOW) is Result.RATE_LIMITED


def test_inbox_failure_rolls_back_owner_and_decision(engine):
    with pytest.raises(StatementError):
        admit(engine, 1, payload={"invalid_json": object()})
    assert counts(engine) == (0, 0)
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM telegram_admission_owners")) == 0
    assert admit(engine, 1) is Result.ADMITTED


def test_quota_and_rejected_dedup_survive_pool_restart(engine):
    for update_id in range(10):
        assert admit(engine, update_id) is Result.ADMITTED
    assert admit(engine, 10) is Result.RATE_LIMITED
    engine.dispose()
    assert admit(engine, 10, now=_NOW + timedelta(seconds=120)) is Result.DUPLICATE
    assert admit(engine, 11) is Result.RATE_LIMITED


def test_preexisting_inbox_update_does_not_consume_quota(engine):
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO telegram_update_inbox (update_id,payload,received_at,next_attempt_at) "
            "VALUES (1,'{}',:now,:now)"
        ), {"now": _NOW})
    assert admit(engine, 1) is Result.DUPLICATE
    assert counts(engine) == (0, 1)


def test_runtime_grants_exclude_delete_and_public_read(engine):
    with engine.connect() as connection:
        for table in ("telegram_admissions", "telegram_admission_owners"):
            for privilege in ("SELECT", "INSERT", "UPDATE"):
                assert connection.scalar(text("SELECT has_table_privilege('argos_runtime', :table, :privilege)"), {"table": table, "privilege": privilege})
            assert not connection.scalar(text("SELECT has_table_privilege('argos_runtime', :table, 'DELETE')"), {"table": table})
            for role in ("anon", "authenticated", "service_role"):
                assert not connection.scalar(text("SELECT has_table_privilege(:role, :table, 'SELECT')"), {"role": role, "table": table})
