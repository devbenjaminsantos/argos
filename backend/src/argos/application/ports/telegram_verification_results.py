"""Checkpoint curto e durável da resposta de uma verificação Telegram."""

from typing import Protocol
from uuid import UUID

from argos.application.ports.telegram_messages import TelegramMessage


class TelegramVerificationResults(Protocol):
    def find_for_claim(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, text: str,
    ) -> TelegramMessage | None:
        """Valida claim/payload e recupera resposta sem executar coleta."""
        ...

    def save_for_claim(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, text: str,
        reply: TelegramMessage,
    ) -> TelegramMessage:
        """Valida novamente o claim e grava ou reutiliza a resposta imutável."""
        ...
