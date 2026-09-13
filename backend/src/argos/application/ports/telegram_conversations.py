"""Contrato de persistência para o estado conversacional Telegram."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4
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
    version: UUID = field(default_factory=uuid4)


class TelegramConversationDraftRepository(Protocol):
    """Opera rascunhos sempre no escopo do proprietário."""

    def begin(
        self, *, telegram_user_id: int, observed_at: datetime, expires_at: datetime
    ) -> TelegramConversationDraft | None:
        """Inicia cadastro ou substitui expirado; nunca sobrescreve ativo."""
        ...

    def advance(
        self, *, expected: TelegramConversationDraft, state: str,
        data: dict[str, object], observed_at: datetime
    ) -> TelegramConversationDraft | None:
        """Avança somente a versão ativa esperada; conflito retorna None."""
        ...

    def get_active(
        self, *, telegram_user_id: int, observed_at: datetime
    ) -> TelegramConversationDraft | None: ...

    def cancel_for_owner(self, *, telegram_user_id: int) -> bool:
        """Remove o rascunho atual e informa se ele existia."""
        ...
