"""Contrato de mensagens enviadas pelo Telegram."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TelegramMessage:
    """Texto simples destinado a um chat já associado ao proprietário."""

    chat_id: int
    text: str


class TelegramMessageSender(Protocol):
    """Porta de saída implementada posteriormente pela Bot API."""

    def send(self, message: TelegramMessage) -> None: ...


class TelegramDeliveryError(Exception):
    """Falha classificada sem carregar resposta ou credencial do provedor."""

    def __init__(
        self,
        code: str,
        *,
        retryable: bool,
        outcome_unknown: bool = False,
    ) -> None:
        if not code or len(code) > 64:
            raise ValueError("code deve ter entre 1 e 64 caracteres.")
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.outcome_unknown = outcome_unknown
