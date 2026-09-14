"""Cancelamento com resposta durável por update."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from argos.application.ports.telegram_messages import TelegramMessage

@dataclass(frozen=True, slots=True)
class CancellationReplies:
    cancelled: str
    nothing_to_cancel: str

class TelegramCancellationRepository(Protocol):
    def cancel_for_update(self, *, update_id: int, lease_token: UUID,
                          telegram_user_id: int, chat_id: int,
                          observed_at: datetime, replies: CancellationReplies) -> TelegramMessage:
        """Valida lease/payload; grava consumo e resposta juntos.

        Replay retorna resposta original sem alcançar operação nova.
        Não altera produtos nem envia mensagens.
        """
        ...
