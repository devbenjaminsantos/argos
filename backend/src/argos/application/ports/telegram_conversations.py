"""Contrato de persistência para o estado conversacional Telegram."""

from typing import Protocol


class TelegramConversationDraftRepository(Protocol):
    """Opera rascunhos sempre no escopo do proprietário."""

    def cancel_for_owner(self, *, telegram_user_id: int) -> bool:
        """Remove o rascunho atual e informa se ele existia."""
        ...
