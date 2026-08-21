"""Validação e criação da conexão PostgreSQL."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError

from argos.config import Settings

_POSTGRESQL_DRIVERS = frozenset({"postgresql", "postgresql+psycopg"})
_SECURE_SSL_MODES = frozenset({"require", "verify-ca", "verify-full"})


class DatabaseConfigurationError(RuntimeError):
    """Configuração de banco ausente, incompatível ou insegura."""


def build_database_url(settings: Settings) -> URL:
    """Normaliza a URL para psycopg sem expor a credencial em erros."""

    configured = settings.database_url
    if configured is None:
        raise DatabaseConfigurationError("ARGOS_DATABASE_URL não configurada.")

    try:
        url = make_url(configured.get_secret_value())
    except ArgumentError as error:
        raise DatabaseConfigurationError(
            "ARGOS_DATABASE_URL possui formato inválido."
        ) from error

    if url.drivername not in _POSTGRESQL_DRIVERS:
        raise DatabaseConfigurationError(
            "ARGOS_DATABASE_URL deve usar PostgreSQL com psycopg."
        )

    url = url.set(drivername="postgresql+psycopg")
    sslmode = url.query.get("sslmode")
    if settings.environment == "production" and sslmode not in _SECURE_SSL_MODES:
        raise DatabaseConfigurationError(
            "ARGOS_DATABASE_URL deve exigir TLS em produção."
        )

    return url


def create_database_engine(settings: Settings) -> Engine:
    """Cria o engine síncrono compartilhado por API, job e migrações."""

    return create_engine(
        build_database_url(settings),
        pool_pre_ping=True,
    )
