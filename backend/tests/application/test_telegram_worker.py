"""Testes do worker Telegram sem banco ou rede."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from argos.application.ports.telegram_inbox import ClaimedTelegramUpdate
from argos.application.ports.telegram_messages import (
    TelegramDeliveryError,
    TelegramMessage,
)
from argos.application.ports.telegram_users import TelegramUser
from argos.application.services.telegram_worker import TelegramInboxWorker
from argos.application.use_cases.start import StartTelegramConversation

_LEASE_TOKEN = UUID("00000000-0000-0000-0000-000000000001")
_NOW = datetime(2026, 9, 10, 18, 0, tzinfo=UTC)
_PAYLOAD = {
    "update_id": 10,
    "message": {
        "message_id": 11,
        "from": {"id": 700},
        "chat": {"id": 800, "type": "private"},
        "text": "/start",
    },
}


class _InboxStub:
    def __init__(self, payload: dict[str, object] | None = _PAYLOAD) -> None:
        self.payload = payload
        self.completed: list[tuple[int, UUID, datetime]] = []
        self.retried: list[tuple[int, UUID, datetime, str]] = []
        self.dead_letters: list[tuple[int, UUID, str]] = []

    def enqueue(self, **_kwargs: object) -> bool:
        raise NotImplementedError

    def claim_next(
        self, *, now: datetime, lease_duration: timedelta
    ) -> ClaimedTelegramUpdate | None:
        if self.payload is None:
            return None
        return ClaimedTelegramUpdate(
            update_id=10,
            payload=self.payload,
            attempt_count=1,
            lease_token=_LEASE_TOKEN,
            lease_expires_at=now + lease_duration,
        )

    def complete(
        self, *, update_id: int, lease_token: UUID, completed_at: datetime
    ) -> bool:
        self.completed.append((update_id, lease_token, completed_at))
        return True

    def retry(
        self,
        *,
        update_id: int,
        lease_token: UUID,
        next_attempt_at: datetime,
        error_code: str,
    ) -> bool:
        self.retried.append(
            (update_id, lease_token, next_attempt_at, error_code)
        )
        return True

    def dead_letter(
        self, *, update_id: int, lease_token: UUID, error_code: str
    ) -> bool:
        self.dead_letters.append((update_id, lease_token, error_code))
        return True


class _UsersStub:
    def __init__(self) -> None:
        self.upserts: list[tuple[int, int, datetime]] = []

    def upsert(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        observed_at: datetime,
    ) -> TelegramUser:
        self.upserts.append((telegram_user_id, chat_id, observed_at))
        return TelegramUser(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            created_at=observed_at,
            updated_at=observed_at,
        )

    def get_by_owner(self, *, telegram_user_id: int) -> TelegramUser | None:
        raise NotImplementedError


class _SenderStub:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.messages: list[TelegramMessage] = []

    def send(self, message: TelegramMessage) -> None:
        if self.error is not None:
            raise self.error
        self.messages.append(message)


def _worker(
    inbox: _InboxStub,
    sender: _SenderStub,
    users: _UsersStub | None = None,
) -> TelegramInboxWorker:
    return TelegramInboxWorker(
        inbox=inbox,
        start=StartTelegramConversation(users or _UsersStub()),
        sender=sender,
        lease_duration=timedelta(seconds=20),
        retry_delay=timedelta(seconds=15),
    )


def test_worker_processes_start_and_completes_after_send() -> None:
    inbox = _InboxStub()
    users = _UsersStub()
    sender = _SenderStub()

    processed = _worker(inbox, sender, users).process_next(now=_NOW)

    assert processed is True
    assert users.upserts == [(700, 800, _NOW)]
    assert len(sender.messages) == 1
    assert sender.messages[0].chat_id == 800
    assert inbox.completed == [(10, _LEASE_TOKEN, _NOW)]
    assert inbox.retried == []
    assert inbox.dead_letters == []


def test_worker_returns_false_when_no_update_is_available() -> None:
    assert _worker(_InboxStub(None), _SenderStub()).process_next(now=_NOW) is False


def test_worker_retries_only_definite_transient_failure() -> None:
    inbox = _InboxStub()
    sender = _SenderStub(
        TelegramDeliveryError("telegram_rate_limited", retryable=True)
    )

    assert _worker(inbox, sender).process_next(now=_NOW) is True

    assert inbox.retried == [
        (10, _LEASE_TOKEN, _NOW + timedelta(seconds=15), "telegram_rate_limited")
    ]
    assert inbox.completed == []
    assert inbox.dead_letters == []


def test_worker_honors_provider_retry_after() -> None:
    inbox = _InboxStub()
    sender = _SenderStub(
        TelegramDeliveryError(
            "telegram_rate_limited",
            retryable=True,
            retry_after=timedelta(seconds=45),
        )
    )

    assert _worker(inbox, sender).process_next(now=_NOW) is True

    assert inbox.retried == [
        (10, _LEASE_TOKEN, _NOW + timedelta(seconds=45), "telegram_rate_limited")
    ]


@pytest.mark.parametrize(
    "error",
    [
        TelegramDeliveryError("telegram_blocked", retryable=False),
        TelegramDeliveryError(
            "telegram_outcome_unknown",
            retryable=True,
            outcome_unknown=True,
        ),
    ],
)
def test_worker_dead_letters_permanent_or_ambiguous_delivery(
    error: TelegramDeliveryError,
) -> None:
    inbox = _InboxStub()

    assert _worker(inbox, _SenderStub(error)).process_next(now=_NOW) is True

    assert inbox.dead_letters == [(10, _LEASE_TOKEN, error.code)]
    assert inbox.retried == []
    assert inbox.completed == []


def test_worker_dead_letters_invalid_or_unsupported_payload() -> None:
    inbox = _InboxStub({"message": {"text": "/ajuda"}})

    assert _worker(inbox, _SenderStub()).process_next(now=_NOW) is True

    assert inbox.dead_letters == [
        (10, _LEASE_TOKEN, "invalid_or_unsupported_update")
    ]


def test_unexpected_failure_leaves_lease_for_recovery() -> None:
    inbox = _InboxStub()

    with pytest.raises(RuntimeError, match="unexpected"):
        _worker(inbox, _SenderStub(RuntimeError("unexpected"))).process_next(
            now=_NOW
        )

    assert inbox.completed == []
    assert inbox.retried == []
    assert inbox.dead_letters == []
