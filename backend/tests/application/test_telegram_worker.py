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
from argos.application.use_cases.begin_registration import BeginTelegramRegistration
from argos.application.use_cases.cancel import CancelTelegramConversation
from argos.application.use_cases.help import HelpTelegramConversation
from argos.application.use_cases.list_products import ListTelegramProducts
from argos.application.use_cases.receive_registration_text import ReceiveTelegramRegistrationText
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


class _ProductsStub:
    def list_for_update(self, **kwargs):
        return TelegramMessage(chat_id=kwargs["chat_id"], text="Lista de produtos")


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


class _ConversationsStub:
    def __init__(self, *, exists: bool = False) -> None:
        self.exists = exists
        self.cancelled_for: list[int] = []

    def cancel_for_update(self, *, telegram_user_id: int, chat_id: int, replies, **kwargs):
        self.cancelled_for.append(telegram_user_id)
        return TelegramMessage(chat_id=chat_id, text=replies.cancelled if self.exists else replies.nothing_to_cancel)


class _RegistrationStub:
    def __init__(self):
        self.calls = []

    def begin_for_update(self, **kwargs):
        self.calls.append(kwargs)
        return TelegramMessage(chat_id=kwargs["chat_id"], text=kwargs["replies"].started)


class _RegistrationURLStub:
    def __init__(self):
        self.calls = []

    def receive_for_update(self, **kwargs):
        self.calls.append(kwargs)
        return TelegramMessage(chat_id=kwargs["chat_id"], text=kwargs["url_replies"].accepted if kwargs["text"].startswith("https://mercadolivre") else kwargs["url_replies"].invalid_url)


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
    conversations: _ConversationsStub | None = None,
    registrations: _RegistrationStub | None = None,
    urls: _RegistrationURLStub | None = None,
) -> TelegramInboxWorker:
    return TelegramInboxWorker(
        inbox=inbox,
        start=StartTelegramConversation(users or _UsersStub()),
        help_conversation=HelpTelegramConversation(),
        cancel_conversation=CancelTelegramConversation(
            conversations or _ConversationsStub()
        ),
        begin_registration=BeginTelegramRegistration(registrations or _RegistrationStub()),
        receive_registration_text=ReceiveTelegramRegistrationText(urls or _RegistrationURLStub()),
        list_products=ListTelegramProducts(_ProductsStub()),
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


def test_worker_processes_help_without_upserting_identity() -> None:
    payload = {
        **_PAYLOAD,
        "message": {**_PAYLOAD["message"], "text": "  /AJUDA  "},
    }
    inbox = _InboxStub(payload)
    users = _UsersStub()
    sender = _SenderStub()

    assert _worker(inbox, sender, users).process_next(now=_NOW) is True

    assert users.upserts == []
    assert len(sender.messages) == 1
    assert "/start" in sender.messages[0].text
    assert "/ajuda" in sender.messages[0].text
    assert inbox.completed == [(10, _LEASE_TOKEN, _NOW)]


@pytest.mark.parametrize(
    ("exists", "expected"),
    [
        (True, "Operação cancelada"),
        (False, "Não há nenhuma operação em andamento"),
    ],
)
def test_worker_processes_cancel_without_upserting_identity(
    exists: bool, expected: str
) -> None:
    payload = {
        **_PAYLOAD,
        "message": {**_PAYLOAD["message"], "text": "  /CANCELAR  "},
    }
    inbox = _InboxStub(payload)
    users = _UsersStub()
    conversations = _ConversationsStub(exists=exists)
    sender = _SenderStub()

    assert _worker(
        inbox, sender, users, conversations
    ).process_next(now=_NOW) is True

    assert users.upserts == []
    assert conversations.cancelled_for == [700]
    assert len(sender.messages) == 1
    assert expected in sender.messages[0].text
    assert inbox.completed == [(10, _LEASE_TOKEN, _NOW)]


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
    inbox = _InboxStub({"message": {"text": "/adicionar"}})

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


def test_worker_dispatches_registration_with_claimed_update_and_lease():
    payload = {**_PAYLOAD, "message": {**_PAYLOAD["message"], "text": " /ADICIONAR "}}
    inbox, sender, users, registrations = _InboxStub(payload), _SenderStub(), _UsersStub(), _RegistrationStub()
    assert _worker(inbox, sender, users, registrations=registrations).process_next(now=_NOW)
    call = registrations.calls[0]
    assert (call["update_id"], call["lease_token"], call["telegram_user_id"], call["chat_id"], call["observed_at"]) == (10, _LEASE_TOKEN, 700, 800, _NOW)
    assert users.upserts == []
    assert "Rascunho de teste" in sender.messages[0].text
    assert "próximas etapas" in sender.messages[0].text
    assert inbox.completed == [(10, _LEASE_TOKEN, _NOW)]


@pytest.mark.parametrize("raw,expected", [("https://mercadolivre.com.br/p/MLB123", "URL registrada"), ("https://evil.test/x", "Envie uma URL")])
def test_worker_routes_text_to_registration_url_with_claim(raw, expected):
    inbox = _InboxStub({**_PAYLOAD, "message": {**_PAYLOAD["message"], "text": raw}})
    sender, users, urls = _SenderStub(), _UsersStub(), _RegistrationURLStub()
    assert _worker(inbox, sender, users, urls=urls).process_next(now=_NOW)
    call = urls.calls[0]
    assert (call["update_id"], call["lease_token"], call["text"]) == (10, _LEASE_TOKEN, raw)
    assert users.upserts == []
    assert expected in sender.messages[0].text
    assert inbox.completed == [(10, _LEASE_TOKEN, _NOW)]


def test_worker_routes_products_to_private_listing():
    payload={**_PAYLOAD,"message":{**_PAYLOAD["message"],"text":"/produtos"}}
    inbox=_InboxStub(payload)
    sender=_SenderStub()
    worker=_worker(inbox=inbox,sender=sender)
    assert worker.process_next(now=_NOW)
    assert sender.messages[0].text=="Lista de produtos"
    assert len(inbox.completed)==1
