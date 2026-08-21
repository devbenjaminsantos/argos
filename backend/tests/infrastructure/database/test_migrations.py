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

    assert scripts.get_heads() == ["20260821_01"]


def test_initial_migration_compiles_for_postgresql(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setenv(
        "ARGOS_DATABASE_URL",
        "postgresql+psycopg://argos:secret@localhost:5432/argos",
    )

    command.upgrade(_alembic_config(), "head", sql=True)
    sql = capsys.readouterr().out

    assert "CREATE TABLE processed_telegram_updates" in sql
    assert "update_id BIGINT NOT NULL" in sql
    assert "PRIMARY KEY (update_id)" in sql
    assert "ck_processed_telegram_updates_valid_result" in sql
    assert "ck_processed_telegram_updates_valid_status" in sql
    assert "DROP TABLE" not in sql
    assert "secret" not in sql


def test_model_matches_deduplication_constraints() -> None:
    table = Base.metadata.tables["processed_telegram_updates"]
    check_names = {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert table.primary_key.columns.keys() == ["update_id"]
    assert check_names == {
        "ck_processed_telegram_updates_valid_result",
        "ck_processed_telegram_updates_valid_status",
    }
