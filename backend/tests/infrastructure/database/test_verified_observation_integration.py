"""Caminho interno de verificação até a observação PostgreSQL."""

import os
from uuid import uuid4

import pytest
from sqlalchemy import insert, select

from argos.application.errors import ApplicationError
from argos.application.ports.product_collection import (
    CollectedProduct,
    ProductCollectionError,
)
from argos.application.use_cases.verify_product import VerifyProduct
from argos.infrastructure.database.models import (
    MonitoredProductRecord,
    ProductPriceObservationRecord,
)
from argos.infrastructure.database.price_observations import (
    PostgreSQLPriceObservationRepository,
)
from argos.infrastructure.database.product_verification import (
    PostgreSQLProductVerificationTargets,
)
from tests.infrastructure.database.test_telegram_registration_integration import context

pytestmark = pytest.mark.skipif(
    os.getenv("ARGOS_TEST_DATABASE_URL") is None,
    reason="PostgreSQL de teste ausente.",
)

URL = "https://mercadolivre.com.br/p/MLB123"


class Collector:
    def __init__(self, *, error=None):
        self.error = error

    def collect(self, url):
        if self.error is not None:
            raise self.error
        return CollectedProduct(
            store="mercado-livre", external_id="MLB123", url=url,
            title="Caneca atual", price_cents=14_999, source="meta",
        )


def prepare(context, collector):
    product_id = uuid4()
    with context[0].begin() as connection:
        connection.execute(insert(MonitoredProductRecord).values(
            id=product_id, telegram_user_id=700, slot=1,
            product_key="MLB123", url=URL, alias="Caneca",
            target_price_cents=15_000, interval_hours=12,
            created_at=context[1], removed_at=None,
        ))
    use_case = VerifyProduct(
        PostgreSQLProductVerificationTargets(context[0]), collector,
        PostgreSQLPriceObservationRepository(context[0]),
    )
    return product_id, use_case


def persisted(context):
    with context[0].connect() as connection:
        return connection.execute(
            select(ProductPriceObservationRecord.__table__)
        ).mappings().one()


def test_success_is_persisted_before_result(context):
    product_id, use_case = prepare(context, Collector())
    observation_id = uuid4()
    result = use_case.execute(
        telegram_user_id=700, product_id=product_id,
        observation_id=observation_id, observed_at=context[1],
    )
    row = persisted(context)
    assert result.current_price_cents == 14_999
    assert row["id"] == observation_id
    assert row["product_id"] == product_id
    assert row["status"] == "success"
    assert row["price_cents"] == 14_999
    assert row["source"] == "meta"


def test_collection_failure_is_persisted_before_public_error(context):
    product_id, use_case = prepare(
        context, Collector(error=ProductCollectionError("timeout")),
    )
    with pytest.raises(ApplicationError) as raised:
        use_case.execute(
            telegram_user_id=700, product_id=product_id,
            observation_id=uuid4(), observed_at=context[1],
        )
    row = persisted(context)
    assert raised.value.code == "collection_timeout"
    assert row["status"] == "failure"
    assert row["price_cents"] is None
    assert row["source"] is None
    assert row["error_code"] == "collection_timeout"
