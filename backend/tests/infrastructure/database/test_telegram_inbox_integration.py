"""Testes da inbox contra PostgreSQL real."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, text

from argos.config import Settings
from argos.application.ports.telegram_messages import TelegramMessage
from argos.infrastructure.database.telegram_inbox import PostgreSQLTelegramInbox
from argos.main import create_app
from argos.telegram_worker import run_once

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


def test_concurrent_enqueue_persists_an_update_once(
    inbox: PostgreSQLTelegramInbox,
) -> None:
    now = datetime.now(UTC)

    def enqueue(index: int) -> bool:
        return inbox.enqueue(
            update_id=104,
            payload={"attempt": index},
            received_at=now,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        insertions = list(executor.map(enqueue, range(4)))

    assert sum(insertions) == 1
    claimed = inbox.claim_next(now=now, lease_duration=timedelta(seconds=30))
    assert claimed is not None
    assert claimed.payload["attempt"] in range(4)


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


def test_dead_letter_rejects_stale_lease_and_is_not_reclaimed(
    inbox: PostgreSQLTelegramInbox,
) -> None:
    now = datetime.now(UTC)
    inbox.enqueue(update_id=106, payload={"text": "/bad"}, received_at=now)
    claimed = inbox.claim_next(now=now, lease_duration=timedelta(seconds=10))
    assert claimed is not None

    assert inbox.dead_letter(
        update_id=claimed.update_id,
        lease_token=UUID("00000000-0000-0000-0000-000000000002"),
        error_code="invalid_update",
    ) is False
    assert inbox.dead_letter(
        update_id=claimed.update_id,
        lease_token=claimed.lease_token,
        error_code="invalid_update",
    ) is True
    assert inbox.claim_next(
        now=now + timedelta(seconds=11),
        lease_duration=timedelta(seconds=10),
    ) is None


def test_webhook_acknowledges_only_after_postgresql_persistence() -> None:
    assert _DATABASE_URL is not None
    engine = create_engine(_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE telegram_update_inbox"))

    settings = Settings(
        environment="test",
        database_url=SecretStr(_DATABASE_URL),
        telegram_webhook_secret=SecretStr("integration-webhook-secret"),
    )
    update = {
        "update_id": 105,
        "message": {
            "message_id": 1,
            "from": {"id": 789},
            "chat": {"id": 789, "type": "private"},
            "text": "/start",
        },
    }

    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/webhooks/telegram",
            headers={
                "X-Telegram-Bot-Api-Secret-Token": "integration-webhook-secret"
            },
            json=update,
        )

    with engine.begin() as connection:
        persisted = connection.execute(
            text(
                "SELECT payload, status, attempt_count "
                "FROM telegram_update_inbox WHERE update_id = 105"
            )
        ).one()
        connection.execute(text("TRUNCATE TABLE telegram_update_inbox"))
    engine.dispose()

    assert response.status_code == 200
    assert persisted.payload == update
    assert persisted.status == "pending"
    assert persisted.attempt_count == 0


def test_one_shot_worker_persists_owner_sends_start_and_completes() -> None:
    assert _DATABASE_URL is not None
    engine = create_engine(_DATABASE_URL)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE telegram_update_inbox"))
        connection.execute(
            text(
                "TRUNCATE TABLE telegram_conversation_drafts, "
                "telegram_users"
            )
        )

    now = datetime.now(UTC)
    inbox = PostgreSQLTelegramInbox(engine)
    update = {
        "update_id": 107,
        "message": {
            "message_id": 2,
            "from": {"id": 900},
            "chat": {"id": 901, "type": "private"},
            "text": "/start",
        },
    }
    inbox.enqueue(update_id=107, payload=update, received_at=now)

    class Sender:
        def __init__(self) -> None:
            self.messages: list[TelegramMessage] = []

        def send(self, message: TelegramMessage) -> None:
            self.messages.append(message)

    sender = Sender()
    settings = Settings(
        environment="test",
        database_url=SecretStr(_DATABASE_URL),
    )

    processed = run_once(settings, sender=sender, now=now)

    with engine.begin() as connection:
        inbox_status = connection.execute(
            text(
                "SELECT status, attempt_count FROM telegram_update_inbox "
                "WHERE update_id = 107"
            )
        ).one()
        user = connection.execute(
            text(
                "SELECT telegram_user_id, chat_id FROM telegram_users "
                "WHERE telegram_user_id = 900"
            )
        ).one()
        connection.execute(text("TRUNCATE TABLE telegram_update_inbox"))
        connection.execute(
            text(
                "TRUNCATE TABLE telegram_conversation_drafts, "
                "telegram_users"
            )
        )
    engine.dispose()

    assert processed is True
    assert inbox_status.status == "completed"
    assert inbox_status.attempt_count == 1
    assert (user.telegram_user_id, user.chat_id) == (900, 901)
    assert len(sender.messages) == 1
    assert sender.messages[0].chat_id == 901
    assert "Eu sou o Argos" in sender.messages[0].text
