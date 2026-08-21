"""Verificações estáticas da imagem antes do build em um daemon Docker."""

from pathlib import Path


def _read(name: str) -> str:
    return Path(name).read_text(encoding="utf-8")


def test_container_pins_base_image_and_uses_postgresql_driver() -> None:
    dockerfile = _read("Dockerfile")
    lockfile = _read("requirements.runtime.lock")

    assert "python:3.14.6-slim-bookworm@sha256:" in dockerfile
    assert "msodbcsql" not in dockerfile
    assert "packages.microsoft.com" not in dockerfile
    assert "psycopg-binary==" in lockfile
    assert "sqlalchemy==" in lockfile.lower()


def test_container_includes_versioned_migrations() -> None:
    dockerfile = _read("Dockerfile")

    assert "COPY alembic.ini ./" in dockerfile
    assert "COPY migrations ./migrations" in dockerfile


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
