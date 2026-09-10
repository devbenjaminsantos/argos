"""Testes da composição one-shot do worker."""

import pytest
from sqlalchemy import create_engine

from argos.config import Settings
from argos.telegram_worker import build_worker


def test_real_sender_requires_token_before_processing() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with pytest.raises(RuntimeError, match="ARGOS_TELEGRAM_BOT_TOKEN"):
            build_worker(Settings(environment="test"), engine=engine)
    finally:
        engine.dispose()
