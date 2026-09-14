"""Seleção de produto para proposta de remoção, sem desativação."""
from datetime import datetime
from uuid import UUID
from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_removal_selection import TelegramRemovalSelectionRepository
from argos.domain.target_price import format_target_price_brl


def format_removal_proposal(slot: int, alias: str, cents: int, hours: int, version: UUID) -> str:
    return (f"Remover este produto?\n\n{slot}. {alias}\nPreço-alvo: {format_target_price_brl(cents)}\nIntervalo: {hours} horas"
            f"\n\nPara confirmar, envie: remover {version.hex}\nUse /cancelar para interromper.")


class SelectTelegramRemovalProduct:
    def __init__(self, repository: TelegramRemovalSelectionRepository) -> None:
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
        return self._repository.select_for_update(update_id=update_id,
            lease_token=lease_token, telegram_user_id=telegram_user_id,
            chat_id=chat_id, text=text, observed_at=observed_at)
