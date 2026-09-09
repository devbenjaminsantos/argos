"""Testes da configuração segura do PostgreSQL."""

from pathlib import Path

import pytest
from pydantic import SecretStr

from argos.config import Settings
from argos.infrastructure.database.config import (
    DatabaseConfigurationError,
    build_database_url,
    build_migration_database_url,
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


def test_database_url_requires_tls_and_ca_in_production(tmp_path: Path) -> None:
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
            f"?sslmode=verify-full&sslrootcert={tmp_path / 'supabase-root.crt'}"
        ),
    )
    (tmp_path / "supabase-root.crt").write_text(
        "test certificate",
        encoding="utf-8",
    )
    without_ca = Settings(
        environment="production",
        database_url=SecretStr(
            "postgresql+psycopg://argos:secret@db.example/argos"
            "?sslmode=verify-full"
        ),
    )
    with_missing_ca = Settings(
        environment="production",
        database_url=SecretStr(
            "postgresql+psycopg://argos:secret@db.example/argos"
            f"?sslmode=verify-full&sslrootcert={tmp_path / 'missing.crt'}"
        ),
    )

    with pytest.raises(DatabaseConfigurationError):
        build_database_url(without_tls)

    with pytest.raises(DatabaseConfigurationError):
        build_database_url(without_ca)

    with pytest.raises(DatabaseConfigurationError):
        build_database_url(with_missing_ca)

    assert build_database_url(with_tls).query["sslmode"] == "verify-full"
    assert build_database_url(with_tls).query["sslrootcert"] == str(
        tmp_path / "supabase-root.crt"
    )

    for sslmode in ("require", "verify-ca"):
        without_hostname_verification = Settings(
            environment="production",
            database_url=SecretStr(
                "postgresql+psycopg://argos:secret@db.example/argos"
                f"?sslmode={sslmode}"
            ),
        )

        with pytest.raises(DatabaseConfigurationError):
            build_database_url(without_hostname_verification)


def test_migration_database_url_is_required_separately_in_production(
    tmp_path: Path,
) -> None:
    cert_path = tmp_path / "supabase-root.crt"
    cert_path.write_text("test certificate", encoding="utf-8")
    runtime = (
        "postgresql://runtime:secret@db.example/argos"
        f"?sslmode=verify-full&sslrootcert={cert_path}"
    )
    migration = (
        "postgresql://migrator:secret@db.example/argos"
        f"?sslmode=verify-full&sslrootcert={cert_path}"
    )

    settings = Settings(
        environment="production",
        database_url=SecretStr(runtime),
        migration_database_url=SecretStr(migration),
    )
    migration_url = build_migration_database_url(settings)

    assert migration_url.username == "migrator"
    assert migration_url.query["sslrootcert"] == str(cert_path)

    without_migration_url = Settings(
        environment="production",
        database_url=SecretStr(runtime),
    )
    with pytest.raises(DatabaseConfigurationError):
        build_migration_database_url(without_migration_url)


def test_migration_database_url_falls_back_to_runtime_in_non_production() -> None:
    settings = Settings(
        environment="test",
        database_url=SecretStr(
            "postgresql://argos:secret@localhost:5432/argos"
        ),
    )

    assert build_migration_database_url(settings).drivername == "postgresql+psycopg"
