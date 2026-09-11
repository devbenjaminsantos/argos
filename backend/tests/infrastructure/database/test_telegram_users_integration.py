"""Testes da identidade Telegram contra PostgreSQL real."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from argos.infrastructure.database.telegram_users import (
    PostgreSQLTelegramUserRepository,
)

_DATABASE_URL = os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    _DATABASE_URL is None,
    reason="ARGOS_TEST_DATABASE_URL não configurada.",
)


@pytest.fixture
def repository() -> PostgreSQLTelegramUserRepository:
    assert _DATABASE_URL is not None
    engine = create_engine(_DATABASE_URL, pool_size=5, max_overflow=0)
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE telegram_conversation_drafts, "
                "telegram_users"
            )
        )
    try:
        yield PostgreSQLTelegramUserRepository(engine)
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE telegram_conversation_drafts, "
                    "telegram_users"
                )
            )
        engine.dispose()


def test_upsert_preserves_owner_and_updates_destination(
    repository: PostgreSQLTelegramUserRepository,
) -> None:
    now = datetime.now(UTC)

    created = repository.upsert(
        telegram_user_id=700,
        chat_id=800,
        observed_at=now,
    )
    updated = repository.upsert(
        telegram_user_id=700,
        chat_id=801,
        observed_at=now + timedelta(seconds=1),
    )

    assert created.telegram_user_id == 700
    assert created.chat_id == 800
    assert updated.telegram_user_id == 700
    assert updated.chat_id == 801
    assert updated.created_at == created.created_at
    assert updated.updated_at > created.updated_at


def test_older_delivery_does_not_restore_stale_destination(
    repository: PostgreSQLTelegramUserRepository,
) -> None:
    now = datetime.now(UTC)
    repository.upsert(
        telegram_user_id=701,
        chat_id=810,
        observed_at=now + timedelta(seconds=1),
    )

    result = repository.upsert(
        telegram_user_id=701,
        chat_id=809,
        observed_at=now,
    )

    assert result.chat_id == 810
    assert result.updated_at == now + timedelta(seconds=1)


def test_concurrent_upsert_creates_one_owner(
    repository: PostgreSQLTelegramUserRepository,
) -> None:
    now = datetime.now(UTC)

    def upsert(index: int) -> object:
        return repository.upsert(
            telegram_user_id=702,
            chat_id=820 + index,
            observed_at=now + timedelta(microseconds=index),
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(upsert, range(4)))

    result = repository.get_by_owner(telegram_user_id=702)
    assert result is not None
    assert result.chat_id == 823
