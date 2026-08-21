"""Testes da fronteira HTTP do webhook Telegram."""

from fastapi.testclient import TestClient
from pydantic import SecretStr

from argos.config import Settings
from argos.main import create_app

_SECRET = "development-webhook-secret"
_HEADERS = {
    "X-Telegram-Bot-Api-Secret-Token": _SECRET,
    "Content-Type": "application/json",
}
_VALID_UPDATE = {
    "update_id": 123,
    "message": {
        "message_id": 456,
        "from": {"id": 789},
        "chat": {"id": 789, "type": "private"},
        "text": "/start",
    },
}


def _client(*, maximum_bytes: int = 65_536) -> TestClient:
    settings = Settings(
        environment="test",
        telegram_webhook_secret=SecretStr(_SECRET),
        telegram_webhook_max_body_bytes=maximum_bytes,
    )
    return TestClient(create_app(settings))


def test_webhook_fails_closed_when_secret_is_not_configured() -> None:
    client = TestClient(create_app(Settings(environment="test")))

    response = client.post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=_VALID_UPDATE,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


def test_webhook_rejects_missing_or_inexact_secret() -> None:
    client = _client()

    missing = client.post("/webhooks/telegram", json=_VALID_UPDATE)
    prefixed = client.post(
        "/webhooks/telegram",
        headers={**_HEADERS, "X-Telegram-Bot-Api-Secret-Token": f"x{_SECRET}"},
        json=_VALID_UPDATE,
    )

    assert missing.status_code == 401
    assert prefixed.status_code == 401
    assert _SECRET not in missing.text
    assert _SECRET not in prefixed.text


def test_webhook_rejects_non_json_and_malformed_json() -> None:
    client = _client()

    wrong_type = client.post(
        "/webhooks/telegram",
        headers={**_HEADERS, "Content-Type": "text/plain"},
        content="not-json",
    )
    malformed = client.post(
        "/webhooks/telegram",
        headers=_HEADERS,
        content=b"{invalid",
    )

    assert wrong_type.status_code == 415
    assert malformed.status_code == 400


def test_webhook_rejects_body_over_configured_limit() -> None:
    client = _client(maximum_bytes=1_024)
    oversized = {
        **_VALID_UPDATE,
        "message": {**_VALID_UPDATE["message"], "text": "x" * 2_000},
    }

    response = client.post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=oversized,
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_webhook_accepts_only_private_text_messages() -> None:
    client = _client()
    group_update = {
        **_VALID_UPDATE,
        "message": {
            **_VALID_UPDATE["message"],
            "chat": {"id": -100, "type": "group"},
        },
    }
    edited_update = {
        "update_id": 124,
        "edited_message": _VALID_UPDATE["message"],
    }

    group_response = client.post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=group_update,
    )
    edited_response = client.post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=edited_update,
    )

    assert group_response.status_code == 422
    assert edited_response.status_code == 422
    assert group_response.json()["error"]["code"] == "validation_error"
    assert edited_response.json()["error"]["code"] == "validation_error"


def test_valid_update_is_not_acknowledged_before_persistence_exists() -> None:
    response = _client().post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=_VALID_UPDATE,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert response.headers["X-Correlation-ID"]
