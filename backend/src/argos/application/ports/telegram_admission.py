"""Contrato atômico de deduplicação, limite e entrada na inbox."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Protocol


class TelegramAdmissionResult(Enum):
    ADMITTED = "admitted"
    DUPLICATE = "duplicate"
    RATE_LIMITED = "rate_limited"


class TelegramAdmissionRepository(Protocol):
    def admit(
        self,
        *,
        update_id: int,
        telegram_user_id: int,
        payload: dict[str, object],
        received_at: datetime,
        maximum_commands: int,
        window: timedelta,
    ) -> TelegramAdmissionResult:
        """Decide e persiste atomicamente, serializando admissões por usuário.

        Repetição não consome quota nem muda a decisão persistida. Somente
        ADMITTED cria trabalho na inbox; RATE_LIMITED também fica deduplicado.
        A janela conta admissões em (received_at - window, received_at].
        Qualquer falha reverte decisão, quota e inserção na inbox juntas.
        """
        ...
