"""Prepara a entrada de texto do cadastro sem executar efeitos externos."""

from datetime import datetime
from uuid import UUID

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_text import TelegramRegistrationTextRepository
from argos.application.use_cases.receive_registration_url import REGISTRATION_URL_REPLIES
from argos.application.use_cases.receive_registration_alias import REGISTRATION_ALIAS_REPLIES


class ReceiveTelegramRegistrationText:
    def __init__(self, repository: TelegramRegistrationTextRepository) -> None:
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
        return self._repository.receive_for_update(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
            observed_at=observed_at, url_replies=REGISTRATION_URL_REPLIES,
            alias_replies=REGISTRATION_ALIAS_REPLIES,
        )
