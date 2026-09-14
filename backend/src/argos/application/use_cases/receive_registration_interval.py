"""Prepara a entrada do intervalo sem executar efeitos externos."""

from datetime import datetime
from uuid import UUID

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_interval import (
    RegistrationIntervalReplies, TelegramRegistrationIntervalRepository,
)
from argos.domain.collection_interval import parse_collection_interval_hours

REGISTRATION_INTERVAL_REPLIES = RegistrationIntervalReplies(
    accepted="Intervalo registrado no rascunho de teste. A confirmação e a criação do produto serão liberadas na próxima etapa.\n\nUse /cancelar para interromper o cadastro.",
    invalid_interval="Envie somente 12 ou 24, representando o intervalo em horas.\n\nUse /cancelar para interromper o cadastro.",
    no_active_draft="Não há cadastro ativo. Use /adicionar para iniciar um rascunho de teste.",
    unexpected_state="Este rascunho não está aguardando intervalo. Use /cancelar para reiniciar.",
)


class ReceiveTelegramRegistrationInterval:
    def __init__(self, repository: TelegramRegistrationIntervalRepository) -> None:
        self._repository = repository

    def execute(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str, observed_at: datetime,
    ) -> TelegramMessage:
        if (
            any(not isinstance(v, int) or isinstance(v, bool) for v in (update_id, telegram_user_id, chat_id))
            or update_id < 0 or telegram_user_id <= 0 or chat_id <= 0
            or not isinstance(lease_token, UUID)
            or observed_at.utcoffset() is None or not isinstance(text, str)
            or not text.strip() or len(text) > 4096
        ):
            raise ApplicationError("invalid_input", "Entrada de cadastro inválida.")
        if text.strip().startswith("/"):
            raise ApplicationError("unsupported_command", "Comando não suportado.")
        try:
            interval_hours = parse_collection_interval_hours(text)
        except ValueError:
            interval_hours = None
        return self._repository.receive_for_update(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
            interval_hours=interval_hours, observed_at=observed_at, replies=REGISTRATION_INTERVAL_REPLIES,
        )
