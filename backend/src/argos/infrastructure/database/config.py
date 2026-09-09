"""Validação e criação da conexão PostgreSQL."""

from pathlib import Path

from pydantic import SecretStr
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from argos.config import Settings

_POSTGRESQL_DRIVERS = frozenset({"postgresql", "postgresql+psycopg"})
_SECURE_SSL_MODES = frozenset({"verify-full"})


class DatabaseConfigurationError(RuntimeError):
    """Configuração de banco ausente, incompatível ou insegura."""


def _build_url(
    configured: SecretStr | None,
    *,
    setting_name: str,
    settings: Settings,
) -> URL:
    """Normaliza uma URL PostgreSQL sem expor a credencial em erros."""

    if configured is None:
        raise DatabaseConfigurationError(f"{setting_name} não configurada.")

    try:
        url = make_url(configured.get_secret_value())
    except ArgumentError as error:
        raise DatabaseConfigurationError(
            f"{setting_name} possui formato inválido."
        ) from error

    if url.drivername not in _POSTGRESQL_DRIVERS:
        raise DatabaseConfigurationError(
            f"{setting_name} deve usar PostgreSQL com psycopg."
        )

    url = url.set(drivername="postgresql+psycopg")
    sslmode = url.query.get("sslmode")
    if settings.environment == "production":
        if sslmode not in _SECURE_SSL_MODES:
            raise DatabaseConfigurationError(
                f"{setting_name} deve usar sslmode=verify-full em produção."
            )

        sslrootcert = url.query.get("sslrootcert")
        if not sslrootcert:
            raise DatabaseConfigurationError(
                f"{setting_name} deve informar sslrootcert em produção."
            )

        root_cert = Path(sslrootcert).expanduser()
        if not root_cert.is_file():
            raise DatabaseConfigurationError(
                f"O arquivo sslrootcert de {setting_name} não existe."
            )

    return url


def build_database_url(settings: Settings) -> URL:
    """Normaliza a URL do runtime para psycopg."""

    return _build_url(
        settings.database_url,
        setting_name="ARGOS_DATABASE_URL",
        settings=settings,
    )


def build_migration_database_url(settings: Settings) -> URL:
    """Normaliza a URL exclusiva das migrações para psycopg."""

    configured = settings.migration_database_url
    if configured is None:
        if settings.environment == "production":
            raise DatabaseConfigurationError(
                "ARGOS_MIGRATION_DATABASE_URL deve ser configurada em produção."
            )
        configured = settings.database_url
        setting_name = "ARGOS_DATABASE_URL (fallback de migração)"
    else:
        setting_name = "ARGOS_MIGRATION_DATABASE_URL"

    return _build_url(configured, setting_name=setting_name, settings=settings)


def create_database_engine(settings: Settings) -> Engine:
    """Cria o engine síncrono compartilhado por API, job e migrações."""

    return create_engine(
        build_database_url(settings),
        pool_pre_ping=True,
    )
