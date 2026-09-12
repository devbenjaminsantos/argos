"""Política de admissão independente da entrada HTTP e do PostgreSQL."""

from datetime import datetime, timedelta

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_admission import (
    TelegramAdmissionRepository,
    TelegramAdmissionResult,
)


class AdmitTelegramUpdate:
    def __init__(
        self,
        repository: TelegramAdmissionRepository,
        *,
        maximum_commands: int = 10,
        window: timedelta = timedelta(seconds=60),
    ) -> None:
        if (
            not isinstance(maximum_commands, int)
            or isinstance(maximum_commands, bool)
            or maximum_commands <= 0
            or window <= timedelta(0)
        ):
            raise ValueError("Limite e janela devem ser positivos.")
        self._repository = repository
        self._maximum_commands = maximum_commands
        self._window = window

    def execute(
        self,
        *,
        update_id: int,
        telegram_user_id: int,
        payload: dict[str, object],
        received_at: datetime,
    ) -> TelegramAdmissionResult:
        if (
            not isinstance(update_id, int)
            or isinstance(update_id, bool)
            or not isinstance(telegram_user_id, int)
            or isinstance(telegram_user_id, bool)
            or telegram_user_id <= 0
            or received_at.utcoffset() is None
        ):
            raise ApplicationError("invalid_input", "Update Telegram inválido.")
        return self._repository.admit(
            update_id=update_id,
            telegram_user_id=telegram_user_id,
            payload=payload,
            received_at=received_at,
            maximum_commands=self._maximum_commands,
            window=self._window,
        )
