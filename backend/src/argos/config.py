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
    database_url: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Carrega uma única configuração validada por processo."""

    return Settings()
