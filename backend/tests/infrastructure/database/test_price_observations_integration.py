"""Constraints e ACLs das observações append-only em PostgreSQL real."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import IntegrityError

from argos.infrastructure.database.models import (
    MonitoredProductRecord, ProductPriceObservationRecord,
)
from tests.infrastructure.database.test_telegram_registration_integration import context

pytestmark = pytest.mark.skipif(
    os.getenv("ARGOS_TEST_DATABASE_URL") is None,
    reason="PostgreSQL de teste ausente.",
)


def product(ctx, *, owner=700):
    product_id = uuid4()
    with ctx[0].begin() as connection:
        connection.execute(insert(MonitoredProductRecord).values(
            id=product_id, telegram_user_id=owner, slot=1,
            product_key="MLB123", url="https://mercadolivre.com.br/p/MLB123",
            alias="Caneca", target_price_cents=15_000, interval_hours=12,
            created_at=ctx[1], removed_at=None,
        ))
    return product_id


def observation(ctx, product_id, **changes):
    values = dict(
        id=uuid4(), product_id=product_id, telegram_user_id=700,
        observed_at=ctx[1], target_price_cents=15_000,
        status="success", price_cents=14_999, source="json-ld", error_code=None,
    ) | changes
    with ctx[0].begin() as connection:
        connection.execute(insert(ProductPriceObservationRecord).values(**values))
    return values["id"]


def test_success_and_failure_are_persisted_without_zero(context):
    product_id = product(context)
    observation(context, product_id)
    observation(context, product_id, status="failure", price_cents=None,
                source=None, error_code="timeout")
    with context[0].connect() as connection:
        rows = connection.execute(text(
            "SELECT status,price_cents,source,error_code "
            "FROM product_price_observations ORDER BY status"
        )).all()
    assert rows == [("failure", None, None, "timeout"),
                    ("success", 14_999, "json-ld", None)]


@pytest.mark.parametrize("changes", [
    {"price_cents": 0}, {"price_cents": None}, {"source": None},
    {"error_code": "timeout"},
    {"status": "failure", "price_cents": 0, "source": None, "error_code": "timeout"},
    {"status": "failure", "price_cents": None, "source": "meta", "error_code": "timeout"},
    {"status": "failure", "price_cents": None, "source": None, "error_code": "bad-code"},
])
def test_database_rejects_ambiguous_or_zero_outcome(context, changes):
    product_id = product(context)
    with pytest.raises(IntegrityError):
        observation(context, product_id, **changes)


def test_composite_foreign_key_rejects_foreign_owner(context):
    product_id = product(context)
    with context[0].begin() as connection:
        connection.execute(text(
            "INSERT INTO telegram_users VALUES (701,801,:now,:now)"
        ), {"now": context[1]})
    with pytest.raises(IntegrityError):
        observation(context, product_id, telegram_user_id=701)


def test_observation_id_is_idempotency_key(context):
    product_id = product(context)
    observation_id = observation(context, product_id)
    with pytest.raises(IntegrityError):
        observation(context, product_id, id=observation_id)


def test_runtime_grants_are_append_only_and_data_api_roles_cannot_read(context):
    with context[0].connect() as connection:
        for permission in ("SELECT", "INSERT"):
            assert connection.scalar(text(
                "SELECT has_table_privilege('argos_runtime','product_price_observations',:permission)"
            ), {"permission": permission})
        for permission in ("UPDATE", "DELETE", "TRUNCATE"):
            assert not connection.scalar(text(
                "SELECT has_table_privilege('argos_runtime','product_price_observations',:permission)"
            ), {"permission": permission})
        for role in ("anon", "authenticated", "service_role"):
            assert not connection.scalar(text(
                "SELECT has_table_privilege(:role,'product_price_observations','SELECT')"
            ), {"role": role})


def test_downgrade_refuses_existing_observation(context, monkeypatch):
    from alembic import command
    from alembic.config import Config
    monkeypatch.setenv("ARGOS_ENVIRONMENT", "test")
    monkeypatch.setenv("ARGOS_MIGRATION_DATABASE_URL", os.getenv("ARGOS_TEST_DATABASE_URL"))
    observation(context, product(context))
    with pytest.raises(RuntimeError, match="Observações existentes"):
        command.downgrade(Config("alembic.ini"), "20260914_09")
