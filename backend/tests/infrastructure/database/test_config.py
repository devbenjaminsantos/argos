"""Testes da configuração segura do PostgreSQL."""

import pytest
from pydantic import SecretStr

from argos.config import Settings
from argos.infrastructure.database.config import (
    DatabaseConfigurationError,
    build_database_url,
)


def test_database_url_uses_psycopg_and_masks_password() -> None:
    password = "local-password"
    settings = Settings(
        environment="development",
        database_url=SecretStr(
            f"postgresql://argos:{password}@localhost:5432/argos"
        ),
    )

    url = build_database_url(settings)

    assert url.drivername == "postgresql+psycopg"
    assert url.password == password
    assert password not in str(url)


def test_database_url_rejects_non_postgresql_driver() -> None:
    password = "do-not-leak"
    settings = Settings(
        environment="test",
        database_url=SecretStr(f"sqlite:///{password}.db"),
    )

    with pytest.raises(DatabaseConfigurationError) as captured:
        build_database_url(settings)

    assert password not in str(captured.value)


def test_database_url_requires_tls_in_production() -> None:
    without_tls = Settings(
        environment="production",
        database_url=SecretStr(
            "postgresql+psycopg://argos:secret@db.example/argos"
        ),
    )
    with_tls = Settings(
        environment="production",
        database_url=SecretStr(
            "postgresql+psycopg://argos:secret@db.example/argos"
            "?sslmode=require"
        ),
    )

    with pytest.raises(DatabaseConfigurationError):
        build_database_url(without_tls)

    assert build_database_url(with_tls).query["sslmode"] == "require"
