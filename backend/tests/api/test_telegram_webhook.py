"""Testes da fronteira HTTP do webhook Telegram."""

from datetime import datetime

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.exc import OperationalError

from argos.application.ports.telegram_inbox import ClaimedTelegramUpdate
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


class _InboxStub:
    def __init__(self, *, error: bool = False) -> None:
        self.error = error
        self.enqueued: list[tuple[int, dict[str, object], datetime]] = []

    def enqueue(
        self,
        *,
        update_id: int,
        payload: dict[str, object],
        received_at: datetime,
    ) -> bool:
        if self.error:
            raise OperationalError("INSERT", {}, Exception("unavailable"))
        is_new = not any(item[0] == update_id for item in self.enqueued)
        if is_new:
            self.enqueued.append((update_id, payload, received_at))
        return is_new

    def claim_next(self, **_kwargs: object) -> ClaimedTelegramUpdate | None:
        raise NotImplementedError

    def complete(self, **_kwargs: object) -> bool:
        raise NotImplementedError

    def retry(self, **_kwargs: object) -> bool:
        raise NotImplementedError


class _RunnerStub:
    def __init__(self) -> None:
        self.notifications = 0

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    def notify(self) -> None:
        self.notifications += 1


def _client(
    *,
    maximum_bytes: int = 65_536,
    inbox: _InboxStub | None = None,
    runner: _RunnerStub | None = None,
) -> TestClient:
    settings = Settings(
        environment="test",
        telegram_webhook_secret=SecretStr(_SECRET),
        telegram_webhook_max_body_bytes=maximum_bytes,
    )
    return TestClient(
        create_app(
            settings,
            telegram_inbox=inbox,
            telegram_worker_runner=runner,
        )
    )


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


def test_valid_update_is_not_acknowledged_without_persistence() -> None:
    response = _client().post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=_VALID_UPDATE,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert response.headers["X-Correlation-ID"]


def test_valid_update_is_persisted_before_acknowledgement() -> None:
    inbox = _InboxStub()

    response = _client(inbox=inbox).post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=_VALID_UPDATE,
    )

    assert response.status_code == 200
    assert len(inbox.enqueued) == 1
    assert inbox.enqueued[0][0] == _VALID_UPDATE["update_id"]
    assert inbox.enqueued[0][1] == _VALID_UPDATE


def test_webhook_accepts_normalized_supported_command() -> None:
    inbox = _InboxStub()
    client = _client(inbox=inbox)

    for index, text in enumerate(
        ("  /START  ", "  /AJUDA  ", "  /CANCELAR  "), start=1
    ):
        update = {
            **_VALID_UPDATE,
            "update_id": _VALID_UPDATE["update_id"] + index,
            "message": {**_VALID_UPDATE["message"], "text": text},
        }
        assert client.post(
            "/webhooks/telegram", headers=_HEADERS, json=update
        ).status_code == 200

    assert len(inbox.enqueued) == 3


def test_webhook_acknowledges_unsupported_text_without_persisting_or_waking_worker() -> None:
    inbox = _InboxStub()
    runner = _RunnerStub()
    client = _client(inbox=inbox, runner=runner)

    for text in ("/adicionar", "/start@outro_bot", "olá"):
        update = {
            **_VALID_UPDATE,
            "update_id": _VALID_UPDATE["update_id"] + len(inbox.enqueued) + 1,
            "message": {**_VALID_UPDATE["message"], "text": text},
        }
        response = client.post(
            "/webhooks/telegram",
            headers=_HEADERS,
            json=update,
        )
        assert response.status_code == 200

    assert inbox.enqueued == []
    assert runner.notifications == 0


def test_repeated_update_is_acknowledged_without_duplicate_persistence() -> None:
    inbox = _InboxStub()
    client = _client(inbox=inbox)

    first = client.post("/webhooks/telegram", headers=_HEADERS, json=_VALID_UPDATE)
    repeated = client.post(
        "/webhooks/telegram", headers=_HEADERS, json=_VALID_UPDATE
    )

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert len(inbox.enqueued) == 1


def test_database_failure_is_not_acknowledged() -> None:
    response = _client(inbox=_InboxStub(error=True)).post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=_VALID_UPDATE,
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


def test_persisted_update_wakes_configured_worker_runner() -> None:
    runner = _RunnerStub()

    response = _client(inbox=_InboxStub(), runner=runner).post(
        "/webhooks/telegram",
        headers=_HEADERS,
        json=_VALID_UPDATE,
    )

    assert response.status_code == 200
    assert runner.notifications == 1
