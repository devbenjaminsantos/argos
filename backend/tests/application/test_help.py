"""Testes isolados do caso de uso `/ajuda`."""

import pytest

from argos.application.errors import ApplicationError
from argos.application.use_cases.help import HelpTelegramConversation


def test_help_returns_only_available_commands_as_plain_text() -> None:
    reply = HelpTelegramConversation().execute(chat_id=800, text="/ajuda")
    assert reply.chat_id == 800
    assert "/start" in reply.text
    assert "/ajuda" in reply.text
    assert "/cancelar" in reply.text
    assert "/adicionar" not in reply.text
    assert "/produtos" not in reply.text


def test_help_normalizes_surrounding_space_and_case() -> None:
    assert HelpTelegramConversation().execute(chat_id=800, text="  /AJUDA  ").chat_id == 800


@pytest.mark.parametrize(("chat_id", "text"), [(0, "/ajuda"), (800, "/start")])
def test_help_rejects_invalid_input(chat_id: int, text: str) -> None:
    with pytest.raises(ApplicationError) as raised:
        HelpTelegramConversation().execute(chat_id=chat_id, text=text)
    assert raised.value.code in {"invalid_input", "unsupported_command"}
