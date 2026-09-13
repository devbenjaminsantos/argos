"""Entrada inválida não pode criar rascunho nem consumir um update."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.use_cases.begin_registration import BeginTelegramRegistration

_LEASE = UUID("00000000-0000-0000-0000-000000000001")
_INPUT = dict(update_id=1, lease_token=_LEASE, telegram_user_id=700,
              chat_id=800, text="/adicionar", observed_at=datetime(2026, 9, 13, tzinfo=UTC))


class ForbiddenRepository:
    def begin_for_update(self, **kwargs):
        pytest.fail("Não deveria acessar persistência.")


@pytest.mark.parametrize("changes", [
    {"update_id": -1}, {"update_id": True}, {"telegram_user_id": False},
    {"telegram_user_id": 0}, {"chat_id": -1}, {"lease_token": "invalid"},
    {"observed_at": datetime(2026, 9, 13)}, {"text": "/start"},
])
def test_invalid_input_never_reaches_repository(changes):
    with pytest.raises(ApplicationError):
        BeginTelegramRegistration(ForbiddenRepository()).execute(**(_INPUT | changes))


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-1), timedelta(days=2)])
def test_invalid_expiration_policy_is_rejected(lifetime):
    with pytest.raises(ValueError):
        BeginTelegramRegistration(ForbiddenRepository(), draft_lifetime=lifetime)


def test_returns_persisted_reply_without_rebuilding_it():
    persisted = TelegramMessage(chat_id=800, text="Resposta original persistida.")
    class Repository:
        def begin_for_update(self, **kwargs):
            assert kwargs["lease_token"] == _LEASE
            assert kwargs["draft_lifetime"] == timedelta(minutes=15)
            return persisted
    assert BeginTelegramRegistration(Repository()).execute(
        **(_INPUT | {"text": "  /ADICIONAR  "})
    ) is persisted


def test_lost_lease_failure_is_propagated_without_fallback_mutation():
    class Repository:
        def begin_for_update(self, **kwargs):
            raise RuntimeError("lease perdido")
    with pytest.raises(RuntimeError, match="lease perdido"):
        BeginTelegramRegistration(Repository()).execute(**_INPUT)
