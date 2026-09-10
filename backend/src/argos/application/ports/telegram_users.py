"""Contrato de persistência da identidade Telegram."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TelegramUser:
    """Proprietário interno e seu destino atual de resposta."""

    telegram_user_id: int
    chat_id: int
    created_at: datetime
    updated_at: datetime


class TelegramUserRepository(Protocol):
    """Acesso à identidade sem usar chat como autorização."""

    def upsert(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        observed_at: datetime,
    ) -> TelegramUser: ...

    def get_by_owner(self, *, telegram_user_id: int) -> TelegramUser | None: ...
