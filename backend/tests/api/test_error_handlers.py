"""Testes das traduções centralizadas de erros."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from argos.application.errors import ApplicationError
from argos.config import Settings
from argos.main import create_app


def _app_with_failure_routes() -> FastAPI:
    app = create_app(Settings(environment="test"))

    @app.get("/expected-error")
    async def expected_error() -> None:
        raise ApplicationError("conflict", "A operação está em conflito.")

    @app.get("/validation-error")
    async def validation_error(quantity: int) -> dict[str, int]:
        return {"quantity": quantity}

    @app.get("/unexpected-error")
    async def unexpected_error() -> None:
        raise RuntimeError("sensitive-value-must-not-leak")

    return app


def test_application_error_preserves_only_public_data() -> None:
    client = TestClient(_app_with_failure_routes())

    response = client.get("/expected-error")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert response.json()["error"]["message"] == "A operação está em conflito."


def test_validation_error_does_not_echo_invalid_input() -> None:
    client = TestClient(_app_with_failure_routes())

    response = client.get("/validation-error", params={"quantity": "secret-input"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "secret-input" not in response.text


def test_unexpected_error_does_not_expose_exception_message() -> None:
    client = TestClient(_app_with_failure_routes(), raise_server_exceptions=False)

    response = client.get("/unexpected-error")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "sensitive-value-must-not-leak" not in response.text
