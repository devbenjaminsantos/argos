"""Cancelamento isolado do rascunho conversacional."""

from argos.application.errors import ApplicationError
from datetime import datetime
from uuid import UUID
from argos.application.ports.telegram_cancellation import CancellationReplies, TelegramCancellationRepository
from argos.application.ports.telegram_messages import TelegramMessage

_CANCELLED_TEXT = "Operação cancelada. Nenhum produto existente foi alterado."
_NOTHING_TO_CANCEL_TEXT = "Não há nenhuma operação em andamento."


class CancelTelegramConversation:
    """Remove somente o rascunho pertencente ao usuário Telegram."""

    def __init__(self, conversations: TelegramCancellationRepository) -> None:
        self._conversations = conversations

    def execute(
        self,
        *,
        update_id: int,
        lease_token: UUID,
        observed_at: datetime,
        telegram_user_id: int,
        chat_id: int,
        text: str,
    ) -> TelegramMessage:
        if (any(not isinstance(v, int) or isinstance(v, bool)
                for v in (update_id, telegram_user_id, chat_id))
            or update_id < 0 or telegram_user_id <= 0 or chat_id <= 0
            or not isinstance(lease_token, UUID) or observed_at.utcoffset() is None):
            raise ApplicationError("invalid_input", "Identidade Telegram inválida.")
        if text.strip().casefold() != "/cancelar":
            raise ApplicationError("unsupported_command", "Comando não suportado.")

        return self._conversations.cancel_for_update(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id,
            observed_at=observed_at,
            replies=CancellationReplies(_CANCELLED_TEXT, _NOTHING_TO_CANCEL_TEXT),
        )
