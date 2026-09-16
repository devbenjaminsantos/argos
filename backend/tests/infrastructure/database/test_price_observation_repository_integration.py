"""Idempotência das observações contra PostgreSQL real."""

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, insert, select, text

from argos.application.ports.price_observations import (
    PriceObservation,
    PriceObservationConflictError,
)
from argos.infrastructure.database.models import (
    MonitoredProductRecord,
    ProductPriceObservationRecord,
)
from argos.infrastructure.database.price_observations import (
    PostgreSQLPriceObservationRepository,
)

_URL = os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(_URL is None, reason="PostgreSQL de teste ausente.")


@pytest.fixture
def context():
    engine = create_engine(_URL, pool_size=5, max_overflow=0)
    now = datetime.now(UTC)
    product_id = uuid4()
    cleanup = "TRUNCATE product_price_observations, monitored_products, telegram_users"
    with engine.begin() as connection:
        connection.execute(text(cleanup))
        connection.execute(
            text("INSERT INTO telegram_users VALUES (700,800,:now,:now)"),
            {"now": now},
        )
        connection.execute(insert(MonitoredProductRecord).values(
            id=product_id, telegram_user_id=700, slot=1,
            product_key="MLB123", url="https://mercadolivre.com.br/p/MLB123",
            alias="Caneca", target_price_cents=15_000, interval_hours=12,
            created_at=now, removed_at=None,
        ))
    try:
        yield engine, now, product_id
    finally:
        with engine.begin() as connection:
            connection.execute(text(cleanup))
        engine.dispose()


def observation(context, **changes) -> PriceObservation:
    values = dict(
        observation_id=UUID("a3000000-0000-4000-8000-000000000001"),
        product_id=context[2], telegram_user_id=700,
        observed_at=context[1], target_price_cents=15_000,
        status="success", price_cents=14_999,
        source="json-ld", error_code=None,
    ) | changes
    return PriceObservation(**values)


def count(context) -> int:
    with context[0].connect() as connection:
        return connection.scalar(select(func.count()).select_from(
            ProductPriceObservationRecord
        ))


def test_equal_replay_does_not_duplicate(context):
    repository = PostgreSQLPriceObservationRepository(context[0])
    item = observation(context)
    repository.append(item)
    repository.append(item)
    assert count(context) == 1


def test_divergent_replay_fails_without_changing_history(context):
    repository = PostgreSQLPriceObservationRepository(context[0])
    repository.append(observation(context))
    with pytest.raises(PriceObservationConflictError, match="conteúdo divergente"):
        repository.append(observation(context, price_cents=14_998))
    assert count(context) == 1


def test_concurrent_equal_replays_create_one_row(context):
    repository = PostgreSQLPriceObservationRepository(context[0])
    item = observation(context)
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(repository.append, [item] * 10))
    assert count(context) == 1


def test_concurrent_divergent_replays_have_one_winner(context):
    repository = PostgreSQLPriceObservationRepository(context[0])
    first = observation(context, price_cents=14_999)
    second = observation(context, price_cents=14_998)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(repository.append, item)
                   for item in (first, second)]
    failures = [future.exception() for future in futures
                if future.exception() is not None]
    assert len(failures) == 1
    assert isinstance(failures[0], PriceObservationConflictError)
    assert count(context) == 1
