"""Ajuda disponível sem dependência de infraestrutura."""

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage

_HELP_TEXT = """Comandos disponíveis neste ambiente de testes:

/start - registrar ou atualizar seu acesso
/ajuda - mostrar esta mensagem
/cancelar - cancelar a operação em andamento

O cadastro e a consulta de produtos serão liberados nas próximas etapas."""


class HelpTelegramConversation:
    """Produz a ajuda correspondente aos comandos realmente disponíveis."""

    def execute(self, *, chat_id: int, text: str) -> TelegramMessage:
        if chat_id <= 0:
            raise ApplicationError("invalid_input", "Chat Telegram inválido.")
        if text.strip().casefold() != "/ajuda":
            raise ApplicationError("unsupported_command", "Comando não suportado.")
        return TelegramMessage(chat_id=chat_id, text=_HELP_TEXT)
