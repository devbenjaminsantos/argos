"""Testes isolados do caso de uso `/cancelar`."""

import pytest

from argos.application.errors import ApplicationError
from argos.application.use_cases.cancel import CancelTelegramConversation


class _ConversationsStub:
    def __init__(self, *, exists: bool) -> None:
        self.exists = exists
        self.owners: list[int] = []

    def cancel_for_owner(self, *, telegram_user_id: int) -> bool:
        self.owners.append(telegram_user_id)
        return self.exists


@pytest.mark.parametrize(
    ("exists", "expected"),
    [
        (True, "Operação cancelada"),
        (False, "Não há nenhuma operação em andamento"),
    ],
)
def test_cancel_is_scoped_to_owner_and_reports_result(
    exists: bool, expected: str
) -> None:
    conversations = _ConversationsStub(exists=exists)

    reply = CancelTelegramConversation(conversations).execute(
        telegram_user_id=700,
        chat_id=800,
        text="  /CANCELAR  ",
    )

    assert conversations.owners == [700]
    assert reply.chat_id == 800
    assert expected in reply.text


@pytest.mark.parametrize(
    ("telegram_user_id", "chat_id", "text"),
    [(0, 800, "/cancelar"), (700, 0, "/cancelar"), (700, 800, "/start")],
)
def test_cancel_rejects_invalid_input_before_repository(
    telegram_user_id: int, chat_id: int, text: str
) -> None:
    conversations = _ConversationsStub(exists=True)

    with pytest.raises(ApplicationError):
        CancelTelegramConversation(conversations).execute(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            text=text,
        )

    assert conversations.owners == []
