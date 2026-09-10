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
