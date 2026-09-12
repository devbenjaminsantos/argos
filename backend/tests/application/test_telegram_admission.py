"""Validação da política de admissão sem banco ou rede."""

from datetime import UTC, datetime, timedelta

import pytest

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_admission import TelegramAdmissionResult
from argos.application.use_cases.admit_telegram_update import AdmitTelegramUpdate


class ForbiddenRepository:
    def admit(self, **kwargs: object):
        pytest.fail("Entrada inválida não pode acessar persistência.")


@pytest.mark.parametrize("result", list(TelegramAdmissionResult))
def test_preserves_atomic_repository_decision(result: TelegramAdmissionResult) -> None:
    class Repository:
        def admit(self, **kwargs: object) -> TelegramAdmissionResult:
            assert kwargs["maximum_commands"] == 10
            assert kwargs["window"] == timedelta(seconds=60)
            return result

    assert AdmitTelegramUpdate(Repository()).execute(
        update_id=1,
        telegram_user_id=700,
        payload={},
        received_at=datetime.now(UTC),
    ) is result


@pytest.mark.parametrize("maximum_commands", [0, -1, True, 1.5])
def test_rejects_invalid_limit(maximum_commands) -> None:
    with pytest.raises(ValueError):
        AdmitTelegramUpdate(ForbiddenRepository(), maximum_commands=maximum_commands)


@pytest.mark.parametrize("window", [timedelta(0), timedelta(seconds=-1)])
def test_rejects_nonpositive_window(window: timedelta) -> None:
    with pytest.raises(ValueError):
        AdmitTelegramUpdate(ForbiddenRepository(), window=window)


@pytest.mark.parametrize(
    ("update_id", "owner", "received_at"),
    [
        (True, 700, datetime.now(UTC)),
        (1, True, datetime.now(UTC)),
        (1, 0, datetime.now(UTC)),
        (1, -1, datetime.now(UTC)),
        (1, 700, datetime(2026, 9, 12)),
    ],
)
def test_invalid_input_cannot_consume_quota(update_id, owner, received_at) -> None:
    with pytest.raises(ApplicationError):
        AdmitTelegramUpdate(ForbiddenRepository()).execute(
            update_id=update_id,
            telegram_user_id=owner,
            payload={},
            received_at=received_at,
        )
