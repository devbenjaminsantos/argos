from datetime import datetime, timezone
from uuid import uuid4

import pytest

from argos.application.ports.price_observations import PriceObservation

NOW = datetime(2026, 9, 16, tzinfo=timezone.utc)


def values(**changes):
    return dict(observation_id=uuid4(), product_id=uuid4(), telegram_user_id=700,
                observed_at=NOW, target_price_cents=15_000, status="success",
                price_cents=14_999, source="json-ld", error_code=None) | changes


def test_success_and_failure_are_exclusive():
    assert PriceObservation(**values()).price_cents == 14_999
    failure = PriceObservation(**values(
        status="failure", price_cents=None, source=None, error_code="timeout"))
    assert failure.error_code == "timeout"


@pytest.mark.parametrize("changes", [
    {"telegram_user_id": 0}, {"telegram_user_id": True},
    {"observed_at": datetime(2026, 9, 16)}, {"target_price_cents": 0},
    {"price_cents": 0}, {"price_cents": None}, {"source": None},
    {"error_code": "timeout"},
    {"status": "failure", "price_cents": 0, "source": None, "error_code": "timeout"},
    {"status": "failure", "price_cents": None, "source": "meta", "error_code": "timeout"},
    {"status": "failure", "price_cents": None, "source": None, "error_code": "bad-code"},
])
def test_invalid_or_ambiguous_observation_is_rejected(changes):
    with pytest.raises(ValueError, match="Observação de preço inválida"):
        PriceObservation(**values(**changes))
