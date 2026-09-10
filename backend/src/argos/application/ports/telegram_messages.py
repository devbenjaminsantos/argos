"""Contrato de mensagens enviadas pelo Telegram."""

from dataclasses import dataclass
from datetime import timedelta
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
        retry_after: timedelta | None = None,
    ) -> None:
        if not code or len(code) > 64:
            raise ValueError("code deve ter entre 1 e 64 caracteres.")
        if retry_after is not None and (
            retry_after <= timedelta(0) or retry_after > timedelta(days=1)
        ):
            raise ValueError("retry_after deve estar entre 0 e 1 dia.")
        if retry_after is not None and (not retryable or outcome_unknown):
            raise ValueError(
                "retry_after exige falha retentável com resultado conhecido."
            )
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.outcome_unknown = outcome_unknown
        self.retry_after = retry_after
