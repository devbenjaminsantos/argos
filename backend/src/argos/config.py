"""Configuração do processo obtida exclusivamente do ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração tipada sem valores secretos versionados."""

    model_config = SettingsConfigDict(
        env_prefix="ARGOS_",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    telegram_bot_token: SecretStr | None = None
    telegram_webhook_secret: SecretStr | None = None
    telegram_webhook_max_body_bytes: int = Field(
        default=65_536,
        ge=1_024,
        le=1_048_576,
    )
    telegram_request_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=30,
    )
    telegram_worker_lease_seconds: int = Field(default=30, ge=5, le=300)
    telegram_worker_retry_seconds: int = Field(default=30, ge=1, le=3_600)
    telegram_worker_poll_seconds: float = Field(default=10.0, gt=0, le=60)
    database_url: SecretStr | None = None
    migration_database_url: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Carrega uma única configuração validada por processo."""

    return Settings()
