"""Prepara a entrada da URL sem executar efeitos externos."""

from datetime import datetime
from uuid import UUID

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_url import (
    RegistrationURLReplies, TelegramRegistrationURLRepository,
)
from argos.domain.mercado_livre_url import normalize_mercado_livre_product_url

_REPLIES = RegistrationURLReplies(
    accepted="URL registrada no rascunho de teste. O recebimento do apelido será liberado na próxima etapa.\n\nUse /cancelar para interromper o cadastro.",
    invalid_url="Envie uma URL HTTPS de anúncio do Mercado Livre Brasil. Links encurtados não são aceitos.\n\nUse /cancelar para interromper o cadastro.",
    no_active_draft="Não há cadastro ativo. Use /adicionar para iniciar um rascunho de teste.",
    unexpected_state="Este rascunho já recebeu a URL ou está em outra etapa. Use /cancelar para reiniciar.",
)


class ReceiveTelegramRegistrationURL:
    def __init__(self, repository: TelegramRegistrationURLRepository) -> None:
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
            normalized_url = normalize_mercado_livre_product_url(text)
        except ValueError:
            normalized_url = None
        return self._repository.receive_for_update(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
            normalized_url=normalized_url, observed_at=observed_at, replies=_REPLIES,
        )
