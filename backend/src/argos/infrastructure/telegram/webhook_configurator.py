"""Configuração idempotente do webhook usando apenas secrets do runtime."""

import http.client
import json
from dataclasses import dataclass

from pydantic import SecretStr

from argos.infrastructure.telegram.bot_api import HTTPSBotAPITransport, TelegramHTTPTransport


class TelegramConfigurationError(RuntimeError):
    """Falha segura, sem incluir resposta remota ou credenciais."""


@dataclass(frozen=True)
class TelegramBotIdentity:
    username: str


class TelegramWebhookConfigurator:
    def __init__(self, token: SecretStr, *, transport: TelegramHTTPTransport | None = None, timeout_seconds: float = 5.0) -> None:
        self._token = token
        self._transport = transport or HTTPSBotAPITransport()
        self._timeout_seconds = timeout_seconds

    def configure(self, *, expected_username: str, webhook_url: str, webhook_secret: SecretStr) -> TelegramBotIdentity:
        identity = self._call("getMe", {})
        username = identity.get("username")
        if username != expected_username or identity.get("is_bot") is not True:
            raise TelegramConfigurationError("telegram_identity_mismatch")

        webhook = self._call("getWebhookInfo", {})
        if webhook.get("url") != webhook_url or webhook.get("allowed_updates") != ["message"]:
            self._call(
                "setWebhook",
                {
                    "url": webhook_url,
                    "secret_token": webhook_secret.get_secret_value(),
                    "allowed_updates": ["message"],
                    "max_connections": 1,
                },
            )
        return TelegramBotIdentity(username=username)

    def _call(self, method: str, payload: dict[str, object]) -> dict[str, object]:
        try:
            status, body = self._transport.post(
                path=f"/bot{self._token.get_secret_value()}/{method}",
                body=json.dumps(payload, separators=(",", ":")).encode(),
                timeout_seconds=self._timeout_seconds,
            )
            decoded = json.loads(body)
        except (OSError, TimeoutError, http.client.HTTPException, UnicodeDecodeError, json.JSONDecodeError):
            raise TelegramConfigurationError("telegram_configuration_unavailable") from None
        if status != 200 or not isinstance(decoded, dict) or decoded.get("ok") is not True:
            raise TelegramConfigurationError("telegram_configuration_rejected")
        result = decoded.get("result")
        if isinstance(result, dict):
            return result
        if result is True:
            return {}
        raise TelegramConfigurationError("telegram_configuration_invalid_response")
