"""Configuração do processo obtida exclusivamente do ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
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
    database_url: SecretStr | None = None


@lru_cache
def get_settings() -> Settings:
    """Carrega uma única configuração validada por processo."""

    return Settings()
