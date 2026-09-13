"""Início de cadastro preparado para recuperação idempotente."""

from datetime import datetime, timedelta
from uuid import UUID

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration import (
    BeginRegistrationReplies,
    TelegramRegistrationRepository,
)

_REPLIES = BeginRegistrationReplies(
    started="Rascunho de teste iniciado por 15 minutos. O recebimento da URL e o cadastro completo serão liberados nas próximas etapas.\n\nUse /cancelar para interromper o cadastro.",
    already_active="Já existe uma operação em andamento. Use /cancelar antes de iniciar outro cadastro.",
    registration_required="Envie /start para registrar seu acesso antes de cadastrar um produto.",
)


class BeginTelegramRegistration:
    def __init__(
        self, repository: TelegramRegistrationRepository, *,
        draft_lifetime: timedelta = timedelta(minutes=15),
    ) -> None:
        if not timedelta(0) < draft_lifetime <= timedelta(days=1):
            raise ValueError("Duração do rascunho deve estar entre zero e um dia.")
        self._repository = repository
        self._draft_lifetime = draft_lifetime

    def execute(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, text: str,
        observed_at: datetime,
    ) -> TelegramMessage:
        if (
            any(not isinstance(value, int) or isinstance(value, bool)
                for value in (update_id, telegram_user_id, chat_id))
            or update_id < 0 or telegram_user_id <= 0 or chat_id <= 0
            or not isinstance(lease_token, UUID)
            or observed_at.utcoffset() is None
        ):
            raise ApplicationError("invalid_input", "Update de cadastro inválido.")
        if text.strip().casefold() != "/adicionar":
            raise ApplicationError("unsupported_command", "Comando não suportado.")
        return self._repository.begin_for_update(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id,
            observed_at=observed_at, draft_lifetime=self._draft_lifetime,
            replies=_REPLIES,
        )
