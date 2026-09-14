import os
from uuid import uuid4
import pytest
from sqlalchemy import insert,text
from sqlalchemy.exc import IntegrityError
from argos.infrastructure.database.models import MonitoredProductRecord
from tests.infrastructure.database.test_telegram_registration_integration import context

pytestmark=pytest.mark.skipif(os.getenv("ARGOS_TEST_DATABASE_URL") is None,reason="PostgreSQL de teste ausente.")


def add(ctx,slot=1,key="MLB123",**changes):
    engine,now,_=ctx
    with engine.begin() as c:
        c.execute(insert(MonitoredProductRecord).values(**(dict(id=uuid4(),telegram_user_id=700,slot=slot,product_key=key,url="https://mercadolivre.com.br/p/MLB123",alias="Caneca",target_price_cents=15000,interval_hours=12,created_at=now)|changes)))


def test_three_slots_and_duplicate_key_are_enforced(context):
    for slot in (1,2,3): add(context,slot,f"MLB{slot}")
    for slot,key in [(4,"MLB4"),(1,"MLB4"),(2,"MLB1")]:
        with pytest.raises(IntegrityError): add(context,slot,key)
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products"))==3


@pytest.mark.parametrize("changes",[{"telegram_user_id":701},{"alias":""},{"target_price_cents":0},{"interval_hours":6},{"product_key":"evil"}])
def test_invalid_product_cannot_persist(context,changes):
    with pytest.raises(IntegrityError): add(context,**changes)


def test_product_runtime_grants_are_minimal(context):
    with context[0].connect() as c:
        for permission in ("SELECT","INSERT"):
            assert c.scalar(text("SELECT has_table_privilege('argos_runtime','monitored_products',:permission)"),{"permission":permission})
        for permission in ("UPDATE","DELETE"):
            assert not c.scalar(text("SELECT has_table_privilege('argos_runtime','monitored_products',:permission)"),{"permission":permission})
        for role in ("anon","authenticated","service_role"):
            assert not c.scalar(text("SELECT has_table_privilege(:role,'monitored_products','SELECT')"),{"role":role})


def test_same_product_allowed_for_distinct_owners(context):
    add(context)
    with context[0].begin() as c:
        c.execute(text("INSERT INTO telegram_users VALUES (701,801,:now,:now)"),{"now":context[1]})
    add(context,telegram_user_id=701)
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products"))==2


def test_downgrade_refuses_existing_product(context,monkeypatch):
    from alembic import command
    from alembic.config import Config
    monkeypatch.setenv("ARGOS_ENVIRONMENT","test")
    monkeypatch.setenv("ARGOS_MIGRATION_DATABASE_URL",os.getenv("ARGOS_TEST_DATABASE_URL"))
    add(context)
    with pytest.raises(RuntimeError,match="downgrade destrutivo recusado"):
        command.downgrade(Config("alembic.ini"),"20260913_07")
    with context[0].connect() as c:
        assert c.scalar(text("SELECT count(*) FROM monitored_products"))==1
