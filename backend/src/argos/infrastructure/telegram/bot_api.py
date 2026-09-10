"""Adaptador síncrono e restrito da Telegram Bot API."""

import http.client
import json
import re
from datetime import timedelta
from typing import Protocol

from pydantic import SecretStr

from argos.application.ports.telegram_messages import (
    TelegramDeliveryError,
    TelegramMessage,
)

_BOT_TOKEN = re.compile(r"^[0-9]+:[A-Za-z0-9_-]{20,}$")
_MAX_RESPONSE_BYTES = 65_536
_MAX_RETRY_AFTER_SECONDS = 86_400


class TelegramHTTPTransport(Protocol):
    """Transporte mínimo substituído por fake nos testes."""

    def post(
        self,
        *,
        path: str,
        body: bytes,
        timeout_seconds: float,
    ) -> tuple[int, bytes]: ...


class HTTPSBotAPITransport:
    """Transporte HTTPS fixo, sem redirects nem host configurável."""

    def post(
        self,
        *,
        path: str,
        body: bytes,
        timeout_seconds: float,
    ) -> tuple[int, bytes]:
        connection = http.client.HTTPSConnection(
            "api.telegram.org",
            port=443,
            timeout=timeout_seconds,
        )
        try:
            connection.request(
                "POST",
                path,
                body=body,
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            response_body = response.read(_MAX_RESPONSE_BYTES + 1)
        finally:
            connection.close()

        if len(response_body) > _MAX_RESPONSE_BYTES:
            raise TelegramDeliveryError(
                "telegram_response_too_large",
                retryable=False,
                outcome_unknown=True,
            )
        return response.status, response_body


class TelegramBotAPI:
    """Envia mensagens sem expor token, corpo remoto ou destino em erros."""

    def __init__(
        self,
        token: SecretStr,
        *,
        transport: TelegramHTTPTransport | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        raw_token = token.get_secret_value()
        if not _BOT_TOKEN.fullmatch(raw_token):
            raise ValueError("Token Telegram possui formato inválido.")
        if timeout_seconds <= 0 or timeout_seconds > 30:
            raise ValueError("Timeout Telegram deve estar entre 0 e 30 segundos.")
        self._token = token
        self._transport = transport or HTTPSBotAPITransport()
        self._timeout_seconds = timeout_seconds

    def send(self, message: TelegramMessage) -> None:
        if message.chat_id <= 0:
            raise ValueError("chat_id deve ser positivo.")
        if not message.text or len(message.text) > 4_096:
            raise ValueError("Mensagem Telegram deve ter entre 1 e 4096 caracteres.")

        body = json.dumps(
            {"chat_id": message.chat_id, "text": message.text},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        try:
            status, response_body = self._transport.post(
                path=f"/bot{self._token.get_secret_value()}/sendMessage",
                body=body,
                timeout_seconds=self._timeout_seconds,
            )
        except TelegramDeliveryError:
            raise
        except (OSError, TimeoutError, http.client.HTTPException):
            raise TelegramDeliveryError(
                "telegram_outcome_unknown",
                retryable=True,
                outcome_unknown=True,
            ) from None

        payload = _decode_response(response_body)
        if status == 200 and payload.get("ok") is True:
            return
        if status == 429:
            raise TelegramDeliveryError(
                "telegram_rate_limited",
                retryable=True,
                retry_after=_retry_after(payload),
            )
        if status == 401:
            code = "telegram_unauthorized"
        elif status == 403:
            code = "telegram_forbidden"
        elif 400 <= status < 500:
            code = "telegram_rejected"
        else:
            raise TelegramDeliveryError(
                "telegram_outcome_unknown",
                retryable=True,
                outcome_unknown=True,
            )
        raise TelegramDeliveryError(code, retryable=False)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(token=SecretStr('**********'), "
            f"timeout_seconds={self._timeout_seconds!r})"
        )


def _decode_response(body: bytes) -> dict[str, object]:
    if len(body) > _MAX_RESPONSE_BYTES:
        raise TelegramDeliveryError(
            "telegram_response_too_large",
            retryable=False,
            outcome_unknown=True,
        )
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise TelegramDeliveryError(
            "telegram_invalid_response",
            retryable=False,
            outcome_unknown=True,
        ) from None
    if not isinstance(payload, dict):
        raise TelegramDeliveryError(
            "telegram_invalid_response",
            retryable=False,
            outcome_unknown=True,
        )
    return payload


def _retry_after(payload: dict[str, object]) -> timedelta | None:
    parameters = payload.get("parameters")
    if not isinstance(parameters, dict):
        return None
    seconds = parameters.get("retry_after")
    if (
        not isinstance(seconds, int)
        or isinstance(seconds, bool)
        or seconds <= 0
        or seconds > _MAX_RETRY_AFTER_SECONDS
    ):
        return None
    return timedelta(seconds=seconds)
