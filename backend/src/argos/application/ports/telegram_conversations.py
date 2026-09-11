"""Contrato de persistência para o estado conversacional Telegram."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class TelegramConversationDraft:
    telegram_user_id: int
    state: str
    data: dict[str, object]
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class TelegramConversationDraftRepository(Protocol):
    """Opera rascunhos sempre no escopo do proprietário."""

    def get_active(
        self, *, telegram_user_id: int, observed_at: datetime
    ) -> TelegramConversationDraft | None: ...

    def cancel_for_owner(self, *, telegram_user_id: int) -> bool:
        """Remove o rascunho atual e informa se ele existia."""
        ...
