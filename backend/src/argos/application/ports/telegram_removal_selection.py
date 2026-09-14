"""Seleção durável por mapa de UUIDs do proprietário."""
from datetime import datetime
from typing import Protocol
from uuid import UUID
from argos.application.ports.telegram_messages import TelegramMessage

class TelegramRemovalSelectionRepository(Protocol):
    def select_for_update(self, *, update_id: int, lease_token: UUID,
                         telegram_user_id: int, chat_id: int, text: str,
                         observed_at: datetime) -> TelegramMessage:
        """Confere lease/payload; grava proposta e resposta juntos, sem remover."""
        ...
