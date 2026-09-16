"""Leitura do alvo exige proprietário, UUID e estado ativo no mesmo predicado."""
import os
from uuid import uuid4

import pytest
from sqlalchemy import insert, text

from argos.infrastructure.database.models import MonitoredProductRecord
from argos.infrastructure.database.product_verification import PostgreSQLProductVerificationTargets
from tests.infrastructure.database.test_telegram_registration_integration import context

pytestmark = pytest.mark.skipif(
    os.getenv("ARGOS_TEST_DATABASE_URL") is None,
    reason="PostgreSQL de teste ausente.",
)


def insert_product(ctx, *, owner=700, removed=False):
    product_id = uuid4()
    with ctx[0].begin() as connection:
        connection.execute(insert(MonitoredProductRecord).values(
            id=product_id, telegram_user_id=owner, slot=1,
            product_key="MLB123", url="https://mercadolivre.com.br/p/MLB123",
            alias="Caneca", target_price_cents=15_000, interval_hours=12,
            created_at=ctx[1], removed_at=ctx[1] if removed else None,
        ))
    return product_id


def repository(ctx):
    return PostgreSQLProductVerificationTargets(ctx[0])


def test_returns_minimal_active_target_for_owner(context):
    product_id = insert_product(context)
    result = repository(context).find_active(
        telegram_user_id=700, product_id=product_id)
    assert result.product_id == product_id
    assert result.product_key == "MLB123"
    assert result.url == "https://mercadolivre.com.br/p/MLB123"
    assert result.alias == "Caneca"
    assert result.target_price_cents == 15_000


def test_foreign_owner_and_unknown_id_are_indistinguishable(context):
    product_id = insert_product(context)
    targets = repository(context)
    assert targets.find_active(telegram_user_id=701, product_id=product_id) is None
    assert targets.find_active(telegram_user_id=700, product_id=uuid4()) is None


def test_removed_product_is_not_returned(context):
    product_id = insert_product(context, removed=True)
    assert repository(context).find_active(
        telegram_user_id=700, product_id=product_id) is None


def test_same_product_key_for_other_owner_cannot_cross_scope(context):
    own_id = insert_product(context)
    with context[0].begin() as connection:
        connection.execute(text(
            "INSERT INTO telegram_users VALUES (701,801,:now,:now)"
        ), {"now": context[1]})
    foreign_id = insert_product(context, owner=701)
    targets = repository(context)
    assert targets.find_active(telegram_user_id=700, product_id=foreign_id) is None
    assert targets.find_active(telegram_user_id=700, product_id=own_id).product_id == own_id


@pytest.mark.parametrize("owner,product_id", [
    (0, uuid4()), (True, uuid4()), (700, "bad"),
])
def test_invalid_query_is_rejected_before_database(context, owner, product_id):
    with pytest.raises(ValueError, match="Consulta de alvo inválida"):
        repository(context).find_active(
            telegram_user_id=owner, product_id=product_id)


def test_runtime_needs_only_existing_select_grant(context):
    with context[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT has_table_privilege('argos_runtime','monitored_products','SELECT')"
        ))
        for permission in ("UPDATE", "DELETE", "TRUNCATE"):
            assert not connection.scalar(text(
                "SELECT has_table_privilege('argos_runtime','monitored_products',:permission)"
            ), {"permission": permission})
