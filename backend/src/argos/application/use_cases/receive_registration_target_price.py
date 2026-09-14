"""Prepara a entrada do preço-alvo sem executar efeitos externos."""

from dataclasses import replace
from datetime import datetime
from uuid import UUID

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_target_price import (
    RegistrationTargetPriceReplies, TelegramRegistrationTargetPriceRepository,
)
from argos.domain.target_price import parse_target_price_cents, format_target_price_brl

REGISTRATION_TARGET_PRICE_REPLIES = RegistrationTargetPriceReplies(
    accepted="Preço-alvo registrado no rascunho de teste. O recebimento do intervalo será liberado na próxima etapa.\n\nUse /cancelar para interromper o cadastro.",
    invalid_target_price="Envie um preço entre R$ 0,01 e R$ 9.999.999,99, por exemplo: R$ 2.500,90.\n\nUse /cancelar para interromper o cadastro.",
    no_active_draft="Não há cadastro ativo. Use /adicionar para iniciar um rascunho de teste.",
    unexpected_state="Este rascunho não está aguardando preço-alvo. Use /cancelar para reiniciar.",
)


class ReceiveTelegramRegistrationTargetPrice:
    def __init__(self, repository: TelegramRegistrationTargetPriceRepository) -> None:
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
            target_price_cents = parse_target_price_cents(text)
        except ValueError:
            target_price_cents = None
        replies = REGISTRATION_TARGET_PRICE_REPLIES
        if target_price_cents is not None:
            replies = replace(replies, accepted=f"Preço-alvo {format_target_price_brl(target_price_cents)} registrado no rascunho de teste. O recebimento do intervalo será liberado na próxima etapa.\n\nUse /cancelar para interromper o cadastro.")
        return self._repository.receive_for_update(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
            target_price_cents=target_price_cents, observed_at=observed_at, replies=replies,
        )
