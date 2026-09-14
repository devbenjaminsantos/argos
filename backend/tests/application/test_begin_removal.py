from datetime import UTC,datetime
from uuid import uuid4
import pytest
from argos.application.errors import ApplicationError
from argos.application.use_cases.begin_removal import BeginTelegramRemoval,format_removal_selection
from argos.application.ports.telegram_messages import TelegramMessage


def test_valid_input_delegates_with_original_identity():
    class Repository:
        def begin_for_update(self,**kwargs):
            assert kwargs['telegram_user_id']==700 and kwargs['chat_id']==800
            return TelegramMessage(chat_id=800,text='empty')
    assert BeginTelegramRemoval(Repository()).execute(update_id=1,lease_token=uuid4(),telegram_user_id=700,chat_id=800,text=' /REMOVER ',observed_at=datetime.now(UTC)).text=='empty'


@pytest.mark.parametrize('changes',[{'telegram_user_id':True},{'chat_id':0},{'update_id':-1},{'lease_token':None},{'text':'/adicionar'},{'observed_at':datetime(2026,9,14)}])
def test_invalid_input_never_calls_repository(changes):
    class Repository:
        def begin_for_update(self,**kwargs):
            pytest.fail('Repository must not be called')
    args=dict(update_id=1,lease_token=uuid4(),telegram_user_id=700,chat_id=800,text='/remover',observed_at=datetime.now(UTC))
    with pytest.raises(ApplicationError):
        BeginTelegramRemoval(Repository()).execute(**(args|changes))


def test_three_maximum_aliases_fit_telegram_message():
    reply=format_removal_selection([(i,'á'*60,999999999,24) for i in (1,2,3)])
    assert len(reply)<4096 and '/cancelar' in reply and 'confirmação' in reply
