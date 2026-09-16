"""Listagem dos produtos do proprietário Telegram."""
from datetime import datetime
from uuid import UUID
from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_products import TelegramProductsRepository
from argos.domain.target_price import format_target_price_brl


def format_products(products: list[tuple[UUID, int, str, int, int]]) -> str:
    if not products:
        return "Você ainda não cadastrou produtos. Use /adicionar para começar."
    lines = ["Seus produtos cadastrados:"]
    for product_id, slot, alias, cents, hours in products:
        lines.append(
            f"{slot}. {alias} — preço-alvo: {format_target_price_brl(cents)}; "
            f"intervalo: {hours} horas\nCódigo: {product_id}"
        )
    lines.append("Para consultar o preço agora, envie /verificar seguido do código completo.")
    return "\n\n".join(lines)


class ListTelegramProducts:
    def __init__(self, repository: TelegramProductsRepository) -> None:
        self._repository = repository

    def execute(self, *, update_id: int, lease_token: UUID,
                telegram_user_id: int, chat_id: int, text: str,
                observed_at: datetime) -> TelegramMessage:
        if (any(not isinstance(v, int) or isinstance(v, bool)
                for v in (update_id, telegram_user_id, chat_id))
            or update_id < 0 or telegram_user_id <= 0 or chat_id <= 0
            or not isinstance(lease_token, UUID) or observed_at.utcoffset() is None):
            raise ApplicationError("invalid_input", "Update de consulta inválido.")
        if text.strip().casefold() != "/produtos":
            raise ApplicationError("unsupported_command", "Comando não suportado.")
        return self._repository.list_for_update(update_id=update_id,
            lease_token=lease_token, telegram_user_id=telegram_user_id,
            chat_id=chat_id, observed_at=observed_at)
