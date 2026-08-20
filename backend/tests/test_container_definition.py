"""Verificações estáticas da imagem antes do build em um daemon Docker."""

from pathlib import Path


def _read(name: str) -> str:
    return Path(name).read_text(encoding="utf-8")


def test_container_pins_base_image_and_odbc_driver() -> None:
    dockerfile = _read("Dockerfile")

    assert "python:3.14.6-slim-bookworm@sha256:" in dockerfile
    assert "ARG MSODBCSQL_VERSION=18.6.1.1-1" in dockerfile
    assert "msodbcsql18=${MSODBCSQL_VERSION}" in dockerfile
    assert "[ODBC Driver 18 for SQL Server]" in dockerfile


def test_container_runs_unprivileged_and_has_healthcheck() -> None:
    dockerfile = _read("Dockerfile")

    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "http://127.0.0.1:8000/health" in dockerfile
    assert '"--host", "0.0.0.0"' in dockerfile


def test_build_context_excludes_secrets_and_development_files() -> None:
    ignored = set(_read(".dockerignore").splitlines())

    assert ".env" in ignored
    assert ".env.*" in ignored
    assert ".venv" in ignored
    assert "tests" in ignored
