"""Cancelamento isolado do rascunho conversacional."""

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_conversations import (
    TelegramConversationDraftRepository,
)
from argos.application.ports.telegram_messages import TelegramMessage

_CANCELLED_TEXT = "Operação cancelada. Nenhum produto existente foi alterado."
_NOTHING_TO_CANCEL_TEXT = "Não há nenhuma operação em andamento."


class CancelTelegramConversation:
    """Remove somente o rascunho pertencente ao usuário Telegram."""

    def __init__(self, conversations: TelegramConversationDraftRepository) -> None:
        self._conversations = conversations

    def execute(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        text: str,
    ) -> TelegramMessage:
        if telegram_user_id <= 0 or chat_id <= 0:
            raise ApplicationError("invalid_input", "Identidade Telegram inválida.")
        if text.strip().casefold() != "/cancelar":
            raise ApplicationError("unsupported_command", "Comando não suportado.")

        cancelled = self._conversations.cancel_for_owner(
            telegram_user_id=telegram_user_id
        )
        return TelegramMessage(
            chat_id=chat_id,
            text=_CANCELLED_TEXT if cancelled else _NOTHING_TO_CANCEL_TEXT,
        )
