"""Testes da inbox contra PostgreSQL real."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from argos.infrastructure.database.telegram_inbox import PostgreSQLTelegramInbox

_DATABASE_URL = os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    _DATABASE_URL is None,
    reason="ARGOS_TEST_DATABASE_URL não configurada.",
)


@pytest.fixture
def inbox() -> PostgreSQLTelegramInbox:
    assert _DATABASE_URL is not None
    engine = create_engine(_DATABASE_URL, pool_size=5, max_overflow=0)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE telegram_update_inbox"))
    try:
        yield PostgreSQLTelegramInbox(engine)
    finally:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE telegram_update_inbox"))
        engine.dispose()


def test_repeated_enqueue_preserves_first_payload(
    inbox: PostgreSQLTelegramInbox,
) -> None:
    now = datetime.now(UTC)

    first = inbox.enqueue(update_id=100, payload={"text": "/start"}, received_at=now)
    repeated = inbox.enqueue(
        update_id=100,
        payload={"text": "altered"},
        received_at=now + timedelta(seconds=1),
    )
    claimed = inbox.claim_next(now=now, lease_duration=timedelta(seconds=30))

    assert first is True
    assert repeated is False
    assert claimed is not None
    assert claimed.payload == {"text": "/start"}


def test_concurrent_claim_reserves_an_update_once(
    inbox: PostgreSQLTelegramInbox,
) -> None:
    now = datetime.now(UTC)
    inbox.enqueue(update_id=101, payload={"text": "/start"}, received_at=now)

    def claim() -> object:
        return inbox.claim_next(now=now, lease_duration=timedelta(seconds=30))

    with ThreadPoolExecutor(max_workers=2) as executor:
        claims = list(executor.map(lambda _index: claim(), range(2)))

    assert sum(item is not None for item in claims) == 1


def test_expired_lease_is_recovered_and_rejects_stale_completion(
    inbox: PostgreSQLTelegramInbox,
) -> None:
    now = datetime.now(UTC)
    inbox.enqueue(update_id=102, payload={"text": "/start"}, received_at=now)

    first = inbox.claim_next(now=now, lease_duration=timedelta(seconds=10))
    unavailable = inbox.claim_next(
        now=now + timedelta(seconds=9),
        lease_duration=timedelta(seconds=10),
    )
    recovered = inbox.claim_next(
        now=now + timedelta(seconds=11),
        lease_duration=timedelta(seconds=10),
    )

    assert first is not None
    assert unavailable is None
    assert recovered is not None
    assert recovered.update_id == first.update_id
    assert recovered.attempt_count == 2
    assert recovered.lease_token != first.lease_token
    assert inbox.complete(
        update_id=first.update_id,
        lease_token=first.lease_token,
        completed_at=now + timedelta(seconds=12),
    ) is False
    assert inbox.complete(
        update_id=recovered.update_id,
        lease_token=recovered.lease_token,
        completed_at=now + timedelta(seconds=12),
    ) is True


def test_retry_waits_until_next_attempt(
    inbox: PostgreSQLTelegramInbox,
) -> None:
    now = datetime.now(UTC)
    inbox.enqueue(update_id=103, payload={"text": "/start"}, received_at=now)
    claimed = inbox.claim_next(now=now, lease_duration=timedelta(seconds=10))
    assert claimed is not None

    assert inbox.retry(
        update_id=claimed.update_id,
        lease_token=claimed.lease_token,
        next_attempt_at=now + timedelta(minutes=1),
        error_code="telegram_unavailable",
    ) is True
    assert inbox.claim_next(
        now=now + timedelta(seconds=59),
        lease_duration=timedelta(seconds=10),
    ) is None
    retried = inbox.claim_next(
        now=now + timedelta(minutes=1),
        lease_duration=timedelta(seconds=10),
    )
    assert retried is not None
    assert retried.attempt_count == 2
