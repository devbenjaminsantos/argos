"""Validação da árvore de migrações e do primeiro schema."""

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint

from argos.infrastructure.database.models import Base


def _alembic_config() -> Config:
    return Config("alembic.ini")


def test_migrations_have_a_single_head() -> None:
    scripts = ScriptDirectory.from_config(_alembic_config())

    assert scripts.get_heads() == ["20260910_02"]


def test_initial_migration_compiles_for_postgresql(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv("ARGOS_ENVIRONMENT", "test")
    monkeypatch.setenv(
        "ARGOS_MIGRATION_DATABASE_URL",
        "postgresql+psycopg://argos-migration:secret@localhost:5432/argos",
    )

    command.upgrade(_alembic_config(), "head", sql=True)
    sql = capsys.readouterr().out

    assert "CREATE TABLE processed_telegram_updates" in sql
    assert "DROP TABLE processed_telegram_updates" in sql
    assert "CREATE TABLE telegram_update_inbox" in sql
    assert "update_id BIGINT NOT NULL" in sql
    assert "payload JSONB NOT NULL" in sql
    assert "lease_token UUID" in sql
    assert "attempt_count INTEGER DEFAULT '0' NOT NULL" in sql
    assert "PRIMARY KEY (update_id)" in sql
    assert "ck_telegram_update_inbox_valid_lifecycle" in sql
    assert "ck_telegram_update_inbox_valid_status" in sql
    assert "GRANT SELECT, INSERT, UPDATE" in sql
    assert "REVOKE ALL PRIVILEGES" in sql
    assert "secret" not in sql


def test_model_matches_durable_inbox_constraints() -> None:
    table = Base.metadata.tables["telegram_update_inbox"]
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert table.primary_key.columns.keys() == ["update_id"]
    assert check_names == {
        "ck_telegram_update_inbox_attempt_count_nonnegative",
        "ck_telegram_update_inbox_valid_lifecycle",
        "ck_telegram_update_inbox_valid_status",
    }
    assert {
        "payload",
        "next_attempt_at",
        "attempt_count",
        "lease_token",
        "lease_expires_at",
        "last_error_code",
    }.issubset(table.columns.keys())
