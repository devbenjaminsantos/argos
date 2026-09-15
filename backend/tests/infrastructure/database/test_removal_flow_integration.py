"""Fluxo HTTP até remoção lógica, com saída Telegram falsa."""
import os
from datetime import UTC,datetime
import pytest
from sqlalchemy import text
from fastapi.testclient import TestClient
from pydantic import SecretStr
from tests.infrastructure.database.test_telegram_registration_integration import context
from tests.infrastructure.database.test_monitored_products_integration import add
from argos.config import Settings
from argos.main import create_app
from argos.telegram_worker import build_worker
from argos.application.use_cases.admit_telegram_update import AdmitTelegramUpdate
from argos.infrastructure.database.telegram_admission import PostgreSQLTelegramAdmissionRepository

pytestmark=pytest.mark.skipif(os.getenv('ARGOS_TEST_DATABASE_URL') is None,reason='PostgreSQL de teste ausente.')

@pytest.mark.parametrize('decision',['remove','cancel'])
def test_http_removal_and_cancel_with_repeated_updates(context,decision):
    engine=context[0]
    add(context)
    with engine.begin() as c:
        c.execute(text('DELETE FROM telegram_update_inbox'))
        c.execute(text('DELETE FROM telegram_admissions'))
        c.execute(text('DELETE FROM telegram_admission_owners'))
    class Sender:
        def __init__(self): self.messages=[]
        def send(self,message): self.messages.append(message)
    sender=Sender()
    settings=Settings(environment='test',telegram_webhook_secret=SecretStr('integration-secret'))
    worker=build_worker(settings,engine=engine,sender=sender)
    app=create_app(settings,telegram_admission=AdmitTelegramUpdate(PostgreSQLTelegramAdmissionRepository(engine)))
    try:
        with TestClient(app) as client:
            def send(id,raw):
                payload={'update_id':id,'message':{'message_id':1,'from':{'id':700},'chat':{'id':800,'type':'private'},'text':raw}}
                for _ in range(2):
                    assert client.post('/webhooks/telegram',headers={'X-Telegram-Bot-Api-Secret-Token':'integration-secret'},json=payload).status_code==200
                assert worker.process_next(now=datetime.now(UTC))
                assert not worker.process_next(now=datetime.now(UTC))
            send(10,'/remover')
            assert 'Caneca' in sender.messages[-1].text
            send(11,'1')
            with engine.connect() as c:
                version=c.scalar(text('SELECT version FROM telegram_conversation_drafts'))
            assert version.hex in sender.messages[-1].text
            send(12,'/cancelar' if decision=='cancel' else f'remover {version.hex}')
            send(13,'/produtos')
            assert ('Caneca' in sender.messages[-1].text)==(decision=='cancel')
            with engine.connect() as c:
                assert c.scalar(text('SELECT count(*) FROM monitored_products'))==1
                assert c.scalar(text('SELECT count(*) FROM monitored_products WHERE removed_at IS NOT NULL'))==(decision=='remove')
                assert c.scalar(text('SELECT count(*) FROM telegram_conversation_drafts'))==0
                assert c.scalar(text("SELECT count(*) FROM telegram_update_inbox WHERE status='completed'"))==4
    finally:
        with engine.begin() as c:
            c.execute(text('DELETE FROM telegram_admissions'))
            c.execute(text('DELETE FROM telegram_admission_owners'))
