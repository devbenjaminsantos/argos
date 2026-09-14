"""Histórico, grants de coluna e reversão protegida em PostgreSQL real."""
import os
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from alembic import command
from alembic.config import Config
from tests.infrastructure.database.test_monitored_products_integration import add
from tests.infrastructure.database.test_telegram_registration_integration import context

pytestmark=pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None,reason="PostgreSQL de teste ausente.")


def test_removed_product_frees_slot_and_key_but_preserves_history(context):
    add(context)
    with context[0].begin() as c:
        c.execute(text("UPDATE monitored_products SET removed_at=clock_timestamp()"))
    add(context)
    with pytest.raises(IntegrityError):
        add(context)
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products"))==2
        assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NULL"))==1


def test_runtime_can_only_update_removal_column(context):
    add(context)
    with context[0].begin() as c:
        c.execute(text("SET LOCAL ROLE argos_runtime"))
        c.execute(text("UPDATE monitored_products SET removed_at=clock_timestamp() WHERE telegram_user_id=700"))
    for sql in ("UPDATE monitored_products SET alias='changed'", "UPDATE monitored_products SET target_price_cents=1", "DELETE FROM monitored_products", "TRUNCATE monitored_products"):
        with pytest.raises(DBAPIError):
            with context[0].begin() as c:
                c.execute(text("SET LOCAL ROLE argos_runtime"))
                c.execute(text(sql))


def test_downgrade_with_history_is_refused_and_revision_preserved(context,monkeypatch):
    monkeypatch.setenv("ARGOS_ENVIRONMENT","test")
    monkeypatch.setenv("ARGOS_MIGRATION_DATABASE_URL",os.getenv("ARGOS_TEST_DATABASE_URL"))
    add(context,removed_at=context[1])
    with pytest.raises(RuntimeError,match="downgrade destrutivo recusado"):
        command.downgrade(Config("alembic.ini"),"20260914_08")
    with context[0].connect() as c:
        assert c.scalar(text("SELECT version_num FROM alembic_version"))=='20260914_09'
        assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NOT NULL"))==1


def test_upgrade_and_downgrade_preserve_active_products(context,monkeypatch):
    monkeypatch.setenv("ARGOS_ENVIRONMENT","test")
    monkeypatch.setenv("ARGOS_MIGRATION_DATABASE_URL",os.getenv("ARGOS_TEST_DATABASE_URL"))
    add(context)
    config=Config("alembic.ini")
    try:
        command.downgrade(config,"20260914_08")
        with context[0].connect() as c:
            assert c.scalar(text("SELECT count(*) FROM monitored_products"))==1
            assert not c.scalar(text("SELECT has_table_privilege('argos_runtime','monitored_products','UPDATE')"))
        command.upgrade(config,"head")
        with context[0].connect() as c:
            assert c.scalar(text("SELECT count(*) FROM monitored_products WHERE removed_at IS NULL"))==1
            assert c.scalar(text("SELECT has_column_privilege('argos_runtime','monitored_products','removed_at','UPDATE')"))
    finally:
        command.upgrade(config,"head")
