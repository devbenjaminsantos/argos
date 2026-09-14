"""Prepara a entrada do apelido sem executar efeitos externos."""

from datetime import datetime
from uuid import UUID

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_alias import (
    RegistrationAliasReplies, TelegramRegistrationAliasRepository,
)
from argos.domain.product_alias import normalize_product_alias

REGISTRATION_ALIAS_REPLIES = RegistrationAliasReplies(
    accepted="Apelido registrado no rascunho de teste. O recebimento do preço-alvo será liberado na próxima etapa.\n\nUse /cancelar para interromper o cadastro.",
    invalid_alias="Envie um apelido de 1 a 60 caracteres, sem links ou caracteres de controle.\n\nUse /cancelar para interromper o cadastro.",
    no_active_draft="Não há cadastro ativo. Use /adicionar para iniciar um rascunho de teste.",
    unexpected_state="Este rascunho está em uma etapa ainda não disponível. Use /cancelar para reiniciar.",
)


class ReceiveTelegramRegistrationAlias:
    def __init__(self, repository: TelegramRegistrationAliasRepository) -> None:
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
            normalized_alias = normalize_product_alias(text)
        except ValueError:
            normalized_alias = None
        return self._repository.receive_for_update(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
            normalized_alias=normalized_alias, observed_at=observed_at, replies=REGISTRATION_ALIAS_REPLIES,
        )
