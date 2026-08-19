"""Testes da configuração por ambiente."""

import pytest
from pydantic import ValidationError

from argos.config import Settings


def test_settings_use_safe_development_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARGOS_ENVIRONMENT", raising=False)
    monkeypatch.delenv("ARGOS_TELEGRAM_BOT_TOKEN", raising=False)

    settings = Settings()

    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.telegram_bot_token is None


def test_settings_read_environment_and_mask_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_token = "123456:development-only-token"
    monkeypatch.setenv("ARGOS_ENVIRONMENT", "test")
    monkeypatch.setenv("ARGOS_TELEGRAM_BOT_TOKEN", raw_token)

    settings = Settings()

    assert settings.environment == "test"
    assert settings.telegram_bot_token is not None
    assert settings.telegram_bot_token.get_secret_value() == raw_token
    assert raw_token not in repr(settings)
    assert raw_token not in str(settings.model_dump())


def test_settings_reject_unknown_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ARGOS_ENVIRONMENT", "staging")

    with pytest.raises(ValidationError):
        Settings()
