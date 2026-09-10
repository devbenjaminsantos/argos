"""Contrato da inbox durável de updates Telegram."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ClaimedTelegramUpdate:
    """Update reservado exclusivamente por um worker."""

    update_id: int
    payload: dict[str, object]
    attempt_count: int
    lease_token: UUID
    lease_expires_at: datetime


class TelegramInbox(Protocol):
    """Operações atômicas exigidas pelo processamento da inbox."""

    def enqueue(
        self,
        *,
        update_id: int,
        payload: dict[str, object],
        received_at: datetime,
    ) -> bool: ...

    def claim_next(
        self,
        *,
        now: datetime,
        lease_duration: timedelta,
    ) -> ClaimedTelegramUpdate | None: ...

    def complete(
        self,
        *,
        update_id: int,
        lease_token: UUID,
        completed_at: datetime,
    ) -> bool: ...

    def retry(
        self,
        *,
        update_id: int,
        lease_token: UUID,
        next_attempt_at: datetime,
        error_code: str,
    ) -> bool: ...

    def dead_letter(
        self,
        *,
        update_id: int,
        lease_token: UUID,
        error_code: str,
    ) -> bool: ...
