"""Testes do endpoint público de saúde."""

from fastapi.testclient import TestClient

from argos.config import Settings
from argos.main import create_app


def test_health_reports_only_liveness_information() -> None:
    client = TestClient(create_app(Settings(environment="test")))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "argos",
        "version": "0.1.0",
    }
    correlation_id = response.headers["X-Correlation-ID"]
    assert len(correlation_id) == 32
    int(correlation_id, 16)


def test_unknown_route_uses_safe_error_envelope() -> None:
    client = TestClient(create_app(Settings(environment="test")))

    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Recurso não encontrado.",
            "correlation_id": response.headers["X-Correlation-ID"],
        }
    }


def test_interactive_documentation_is_not_exposed() -> None:
    client = TestClient(create_app(Settings(environment="test")))

    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
