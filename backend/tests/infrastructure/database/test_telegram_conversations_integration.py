"""Testes dos rascunhos contra PostgreSQL real."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from argos.infrastructure.database.telegram_conversations import (
    PostgreSQLTelegramConversationDraftRepository,
)

_DATABASE_URL = os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    _DATABASE_URL is None,
    reason="ARGOS_TEST_DATABASE_URL não configurada.",
)


@pytest.fixture
def repository():
    assert _DATABASE_URL is not None
    engine = create_engine(_DATABASE_URL)
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE telegram_conversation_drafts, telegram_users CASCADE"))
        connection.execute(
            text("INSERT INTO telegram_users (telegram_user_id, chat_id, created_at, updated_at) VALUES (700, 800, :now, :now), (701, 801, :now, :now)"),
            {"now": now},
        )
        connection.execute(
            text("INSERT INTO telegram_conversation_drafts (telegram_user_id, state, data, created_at, updated_at, expires_at) VALUES (700, 'awaiting_url', '{}'::jsonb, :now, :now, :active), (701, 'awaiting_alias', '{}'::jsonb, :now, :now, :expired)"),
            {"now": now, "active": now + timedelta(minutes=10), "expired": now + timedelta(seconds=1)},
        )
    try:
        yield PostgreSQLTelegramConversationDraftRepository(engine), now
    finally:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE telegram_conversation_drafts, telegram_users CASCADE"))
        engine.dispose()


def test_get_active_is_scoped_and_hides_expired_draft(repository) -> None:
    drafts, now = repository
    active = drafts.get_active(telegram_user_id=700, observed_at=now)
    expired = drafts.get_active(
        telegram_user_id=701, observed_at=now + timedelta(seconds=2)
    )
    assert active is not None
    assert active.telegram_user_id == 700
    assert active.state == "awaiting_url"
    assert expired is None


def test_cancel_deletes_only_owner_draft_atomically(repository) -> None:
    drafts, now = repository
    assert drafts.cancel_for_owner(telegram_user_id=700) is True
    assert drafts.cancel_for_owner(telegram_user_id=700) is False
    assert drafts.get_active(telegram_user_id=701, observed_at=now) is not None


def test_begin_preserves_active_and_replaces_expired(repository):
    drafts, now = repository
    assert drafts.begin(telegram_user_id=700, observed_at=now,
                        expires_at=now + timedelta(minutes=5)) is None
    restarted = drafts.begin(telegram_user_id=701, observed_at=now + timedelta(seconds=2),
                             expires_at=now + timedelta(minutes=5))
    assert restarted is not None
    assert restarted.state == "awaiting_url"
    assert restarted.data == {}
    assert drafts.get_active(telegram_user_id=700, observed_at=now).state == "awaiting_url"


def test_advance_preserves_expiry_and_rejects_stale_version(repository):
    drafts, now = repository
    expected = drafts.get_active(telegram_user_id=700, observed_at=now)
    changed = drafts.advance(expected=expected, state="awaiting_alias",
                             data={"url": "validated-by-application"},
                             observed_at=now + timedelta(seconds=1))
    assert changed is not None
    assert changed.expires_at == expected.expires_at
    assert changed.data == {"url": "validated-by-application"}
    assert drafts.advance(expected=expected, state="awaiting_alias", data={},
                          observed_at=now + timedelta(seconds=2)) is None
    assert drafts.get_active(telegram_user_id=701, observed_at=now).data == {}


def test_expired_draft_cannot_advance(repository):
    drafts, now = repository
    expected = drafts.get_active(telegram_user_id=701, observed_at=now)
    assert drafts.advance(expected=expected, state="awaiting_target_price", data={},
                          observed_at=now + timedelta(seconds=1)) is None


def test_concurrent_advances_allow_only_one_version(repository):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    drafts, now = repository
    expected = drafts.get_active(telegram_user_id=700, observed_at=now)
    barrier = Barrier(2)
    def execute(value):
        barrier.wait(timeout=10)
        return drafts.advance(expected=expected, state="awaiting_alias",
                              data={"choice": value}, observed_at=now + timedelta(seconds=1))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(execute, [1, 2]))
    assert sum(result is not None for result in results) == 1


def test_cancel_and_recreate_does_not_allow_old_snapshot(repository):
    drafts, now = repository
    expected = drafts.get_active(telegram_user_id=700, observed_at=now)
    drafts.cancel_for_owner(telegram_user_id=700)
    drafts.begin(telegram_user_id=700, observed_at=now,
                 expires_at=now + timedelta(minutes=5))
    assert drafts.advance(expected=expected, state="awaiting_alias", data={},
                          observed_at=now + timedelta(seconds=2)) is None
