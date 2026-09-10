"""Testes do adaptador Bot API sem chamadas externas."""

import json
from datetime import timedelta

import pytest
from pydantic import SecretStr

from argos.application.ports.telegram_messages import (
    TelegramDeliveryError,
    TelegramMessage,
)
from argos.infrastructure.telegram.bot_api import TelegramBotAPI

_TOKEN = "123456789:abcdefghijklmnopqrstuvwxyzABCDE"


class _TransportStub:
    def __init__(
        self,
        *,
        status: int = 200,
        response: object = {"ok": True, "result": {"message_id": 1}},
        error: Exception | None = None,
    ) -> None:
        self.status = status
        self.response = response
        self.error = error
        self.requests: list[tuple[str, bytes, float]] = []

    def post(
        self,
        *,
        path: str,
        body: bytes,
        timeout_seconds: float,
    ) -> tuple[int, bytes]:
        self.requests.append((path, body, timeout_seconds))
        if self.error is not None:
            raise self.error
        if isinstance(self.response, bytes):
            return self.status, self.response
        return self.status, json.dumps(self.response).encode()


def _api(transport: _TransportStub) -> TelegramBotAPI:
    return TelegramBotAPI(
        SecretStr(_TOKEN),
        transport=transport,
        timeout_seconds=4,
    )


def test_send_uses_fixed_method_plain_text_and_timeout() -> None:
    transport = _TransportStub()

    _api(transport).send(TelegramMessage(chat_id=800, text="Olá <Argos>"))

    path, body, timeout = transport.requests[0]
    assert path == f"/bot{_TOKEN}/sendMessage"
    assert json.loads(body) == {"chat_id": 800, "text": "Olá <Argos>"}
    assert "parse_mode" not in json.loads(body)
    assert timeout == 4


def test_rate_limit_preserves_bounded_retry_after() -> None:
    transport = _TransportStub(
        status=429,
        response={
            "ok": False,
            "error_code": 429,
            "parameters": {"retry_after": 12},
        },
    )

    with pytest.raises(TelegramDeliveryError) as raised:
        _api(transport).send(TelegramMessage(chat_id=800, text="Olá"))

    assert raised.value.code == "telegram_rate_limited"
    assert raised.value.retryable is True
    assert raised.value.outcome_unknown is False
    assert raised.value.retry_after == timedelta(seconds=12)


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "telegram_rejected"),
        (401, "telegram_unauthorized"),
        (403, "telegram_forbidden"),
    ],
)
def test_client_rejections_are_permanent(status: int, code: str) -> None:
    with pytest.raises(TelegramDeliveryError) as raised:
        _api(_TransportStub(status=status, response={"ok": False})).send(
            TelegramMessage(chat_id=800, text="Olá")
        )

    assert raised.value.code == code
    assert raised.value.retryable is False
    assert raised.value.outcome_unknown is False


@pytest.mark.parametrize(
    "transport",
    [
        _TransportStub(error=TimeoutError("contains secret")),
        _TransportStub(status=500, response={"ok": False}),
        _TransportStub(status=200, response=b"not-json"),
    ],
)
def test_ambiguous_results_are_not_blindly_retried(
    transport: _TransportStub,
) -> None:
    with pytest.raises(TelegramDeliveryError) as raised:
        _api(transport).send(TelegramMessage(chat_id=800, text="Olá"))

    assert raised.value.outcome_unknown is True
    assert _TOKEN not in str(raised.value)


def test_token_is_redacted_and_invalid_configuration_fails_locally() -> None:
    api = _api(_TransportStub())

    assert _TOKEN not in repr(api)
    with pytest.raises(ValueError, match="formato inválido"):
        TelegramBotAPI(SecretStr("not-a-token"))


@pytest.mark.parametrize(
    "message",
    [
        TelegramMessage(chat_id=0, text="Olá"),
        TelegramMessage(chat_id=800, text=""),
        TelegramMessage(chat_id=800, text="x" * 4_097),
    ],
)
def test_invalid_outbound_message_never_reaches_transport(
    message: TelegramMessage,
) -> None:
    transport = _TransportStub()

    with pytest.raises(ValueError):
        _api(transport).send(message)

    assert transport.requests == []
