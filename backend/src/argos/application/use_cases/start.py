"""Primeiro fluxo conversacional do bot."""

from datetime import datetime

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_users import TelegramUserRepository

_START_TEXT = """Olá! Eu sou o Argos.

Posso acompanhar até 3 produtos do Mercado Livre e avisar quando o preço atingir seu objetivo.

Use /adicionar para cadastrar um produto ou /ajuda para ver os comandos."""


class StartTelegramConversation:
    """Registra a identidade e prepara a resposta de `/start`."""

    def __init__(self, users: TelegramUserRepository) -> None:
        self._users = users

    def execute(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        text: str,
        observed_at: datetime,
    ) -> TelegramMessage:
        if telegram_user_id <= 0 or chat_id <= 0:
            raise ApplicationError(
                "invalid_input",
                "Identidade Telegram inválida.",
            )
        if text.strip().casefold() != "/start":
            raise ApplicationError(
                "unsupported_command",
                "Comando não suportado.",
            )
        if observed_at.utcoffset() is None:
            raise ApplicationError(
                "invalid_input",
                "Data de recebimento inválida.",
            )

        user = self._users.upsert(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            observed_at=observed_at,
        )
        return TelegramMessage(chat_id=user.chat_id, text=_START_TEXT)
