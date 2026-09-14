"""Consulta privada com resposta durável por update."""
from datetime import datetime
from typing import Protocol
from uuid import UUID
from argos.application.ports.telegram_messages import TelegramMessage


class TelegramProductsRepository(Protocol):
    def list_for_update(self, *, update_id: int, lease_token: UUID,
                        telegram_user_id: int, chat_id: int,
                        observed_at: datetime) -> TelegramMessage:
        """Verifica payload/lease; persiste snapshot e reutiliza em recuperação."""
        ...
