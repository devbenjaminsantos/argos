from types import SimpleNamespace
from uuid import UUID

import pytest

from argos.infrastructure.database.product_verification import PostgreSQLProductVerificationTargets

PRODUCT_ID = UUID("12345678-1234-5678-1234-567812345678")


class Result:
    def __init__(self, row): self.row = row
    def one_or_none(self): return self.row


class Connection:
    def __init__(self, row): self.row = row; self.statements = []
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def execute(self, statement):
        self.statements.append(statement)
        return Result(self.row)


class Engine:
    def __init__(self, row): self.connection = Connection(row)
    def connect(self): return self.connection


def test_maps_only_selected_target_fields():
    row = SimpleNamespace(id=PRODUCT_ID, product_key="MLB123",
                          url="https://mercadolivre.com.br/p/MLB123",
                          alias="Caneca", target_price_cents=15_000)
    engine = Engine(row)
    result = PostgreSQLProductVerificationTargets(engine).find_active(
        telegram_user_id=700, product_id=PRODUCT_ID)
    assert result.product_id == PRODUCT_ID
    assert result.product_key == "MLB123"
    sql = str(engine.connection.statements[0])
    assert "telegram_user_id" in sql
    assert "removed_at IS NULL" in sql


def test_none_is_preserved_without_fallback_query():
    engine = Engine(None)
    result = PostgreSQLProductVerificationTargets(engine).find_active(
        telegram_user_id=700, product_id=PRODUCT_ID)
    assert result is None
    assert len(engine.connection.statements) == 1


@pytest.mark.parametrize("owner,product_id", [
    (0, PRODUCT_ID), (True, PRODUCT_ID), (700, "bad"),
])
def test_invalid_input_does_not_open_connection(owner, product_id):
    engine = Engine(None)
    with pytest.raises(ValueError, match="Consulta de alvo inválida"):
        PostgreSQLProductVerificationTargets(engine).find_active(
            telegram_user_id=owner, product_id=product_id)
    assert engine.connection.statements == []
