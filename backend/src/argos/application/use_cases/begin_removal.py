"""Início de cadastro preparado para recuperação idempotente."""

from datetime import datetime, timedelta
from uuid import UUID

from argos.domain.target_price import format_target_price_brl
from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_removal import (
    BeginRemovalReplies,
    TelegramRemovalRepository,
)

_REPLIES = BeginRemovalReplies(
    empty="Você não possui produtos ativos para remover.",
    already_active="Já existe uma operação em andamento. Use /cancelar antes de iniciar outro cadastro.",
    registration_required="Envie /start para registrar seu acesso antes de remover um produto.",
)


class BeginTelegramRemoval:
    def __init__(
        self, repository: TelegramRemovalRepository, *,
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
        if text.strip().casefold() != "/remover":
            raise ApplicationError("unsupported_command", "Comando não suportado.")
        return self._repository.begin_for_update(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id,
            observed_at=observed_at, draft_lifetime=self._draft_lifetime,
            replies=_REPLIES,
        )


def format_removal_selection(products: list[tuple[int, str, int, int]]) -> str:
    lines=["Qual produto deseja remover?"]
    for slot, alias, cents, hours in products:
        lines.append(f"{slot}. {alias} — {format_target_price_brl(cents)}; {hours} horas")
    lines.append("Envie o número do produto. A remoção exigirá confirmação.\n\nUse /cancelar para interromper. Esta operação dura 15 minutos.")
    return "\n\n".join(lines)
