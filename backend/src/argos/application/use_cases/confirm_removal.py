"""Confirmação durável de remoção lógica."""
from datetime import datetime
from uuid import UUID
from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_removal_confirmation import TelegramRemovalConfirmationRepository

REMOVED_TEXT = "Produto removido. A vaga está disponível para um novo cadastro."

class ConfirmTelegramRemoval:
    def __init__(self, repository: TelegramRemovalConfirmationRepository) -> None:
        self._repository = repository

    def execute(self, *, update_id: int, lease_token: UUID,
                telegram_user_id: int, chat_id: int, text: str,
                observed_at: datetime) -> TelegramMessage:
        if (any(not isinstance(v, int) or isinstance(v, bool)
                for v in (update_id, telegram_user_id, chat_id))
            or update_id < 0 or telegram_user_id <= 0 or chat_id <= 0
            or not isinstance(lease_token, UUID) or observed_at.utcoffset() is None):
            raise ApplicationError("invalid_input", "Update de consulta inválido.")
        if not isinstance(text, str) or not text.strip() or len(text) > 4096 or text.strip().startswith("/"):
            raise ApplicationError("unsupported_command", "Comando não suportado.")
        return self._repository.confirm_for_update(update_id=update_id,
            lease_token=lease_token, telegram_user_id=telegram_user_id,
            chat_id=chat_id, text=text, observed_at=observed_at)
