"""Testes isolados do caso de uso `/start`."""

from datetime import UTC, datetime

import pytest

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_users import TelegramUser
from argos.application.use_cases.start import StartTelegramConversation


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


def test_start_upserts_owner_and_returns_plain_text_reply() -> None:
    users = _UsersStub()
    use_case = StartTelegramConversation(users)
    observed_at = datetime.now(UTC)

    reply = use_case.execute(
        telegram_user_id=700,
        chat_id=800,
        text="/start",
        observed_at=observed_at,
    )

    assert users.upserts == [(700, 800, observed_at)]
    assert reply.chat_id == 800
    assert "Eu sou o Argos" in reply.text
    assert "/adicionar" in reply.text
    assert "/ajuda" in reply.text


def test_start_normalizes_surrounding_space_and_case() -> None:
    users = _UsersStub()

    StartTelegramConversation(users).execute(
        telegram_user_id=700,
        chat_id=800,
        text="  /START  ",
        observed_at=datetime.now(UTC),
    )

    assert len(users.upserts) == 1


def test_start_rejects_other_commands_without_persisting() -> None:
    users = _UsersStub()

    with pytest.raises(ApplicationError) as raised:
        StartTelegramConversation(users).execute(
            telegram_user_id=700,
            chat_id=800,
            text="/adicionar",
            observed_at=datetime.now(UTC),
        )

    assert raised.value.code == "unsupported_command"
    assert users.upserts == []


def test_start_rejects_naive_timestamp_without_persisting() -> None:
    users = _UsersStub()

    with pytest.raises(ApplicationError) as raised:
        StartTelegramConversation(users).execute(
            telegram_user_id=700,
            chat_id=800,
            text="/start",
            observed_at=datetime.now(),
        )

    assert raised.value.code == "invalid_input"
    assert users.upserts == []


def test_start_rejects_invalid_identity_without_persisting() -> None:
    users = _UsersStub()

    with pytest.raises(ApplicationError) as raised:
        StartTelegramConversation(users).execute(
            telegram_user_id=0,
            chat_id=800,
            text="/start",
            observed_at=datetime.now(UTC),
        )

    assert raised.value.code == "invalid_input"
    assert users.upserts == []
