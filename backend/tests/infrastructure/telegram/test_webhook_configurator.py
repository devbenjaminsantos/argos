"""Testes da configuração administrativa do webhook."""

import json

import pytest
from pydantic import SecretStr

from argos.infrastructure.telegram.webhook_configurator import (
    TelegramConfigurationError,
    TelegramWebhookConfigurator,
)

TOKEN = SecretStr("123456789:abcdefghijklmnopqrstuvwxyzABCDE")
SECRET = SecretStr("webhook_secret")


class Transport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.requests = []

    def post(self, *, path, body, timeout_seconds):
        self.requests.append((path, json.loads(body), timeout_seconds))
        return 200, json.dumps({"ok": True, "result": next(self.responses)}).encode()


def test_configures_identity_and_missing_webhook_without_exposing_secrets() -> None:
    transport = Transport([
        {"is_bot": True, "username": "argos_teste_bot"},
        {"url": "", "allowed_updates": []},
        True,
    ])
    identity = TelegramWebhookConfigurator(TOKEN, transport=transport).configure(
        expected_username="argos_teste_bot",
        webhook_url="https://argos.example/webhooks/telegram",
        webhook_secret=SECRET,
    )
    assert identity.username == "argos_teste_bot"
    assert [request[0].rsplit("/", 1)[-1] for request in transport.requests] == ["getMe", "getWebhookInfo", "setWebhook"]
    assert transport.requests[-1][1]["allowed_updates"] == ["message"]
    assert transport.requests[-1][1]["max_connections"] == 1


def test_keeps_matching_webhook() -> None:
    transport = Transport([
        {"is_bot": True, "username": "argos_teste_bot"},
        {"url": "https://argos.example/webhooks/telegram", "allowed_updates": ["message"]},
    ])
    TelegramWebhookConfigurator(TOKEN, transport=transport).configure(
        expected_username="argos_teste_bot",
        webhook_url="https://argos.example/webhooks/telegram",
        webhook_secret=SECRET,
    )
    assert len(transport.requests) == 2


def test_rejects_unexpected_identity_safely() -> None:
    transport = Transport([{"is_bot": True, "username": "other_bot"}])
    with pytest.raises(TelegramConfigurationError) as raised:
        TelegramWebhookConfigurator(TOKEN, transport=transport).configure(
            expected_username="argos_teste_bot",
            webhook_url="https://argos.example/webhooks/telegram",
            webhook_secret=SECRET,
        )
    assert str(raised.value) == "telegram_identity_mismatch"
    assert TOKEN.get_secret_value() not in str(raised.value)
    assert SECRET.get_secret_value() not in str(raised.value)
