from datetime import UTC,datetime
from uuid import uuid4
import pytest
from argos.application.errors import ApplicationError
from argos.application.use_cases.select_removal_product import SelectTelegramRemovalProduct,format_removal_proposal

@pytest.mark.parametrize('changes',[{'telegram_user_id':True},{'chat_id':0},{'text':'/remover'},{'text':''},{'lease_token':None}])
def test_invalid_input_never_reaches_repository(changes):
    class Repository:
        def select_for_update(self,**kwargs):
            pytest.fail('Repository must not be called')
    args=dict(update_id=1,lease_token=uuid4(),telegram_user_id=700,chat_id=800,text='1',observed_at=datetime.now(UTC))
    with pytest.raises(ApplicationError):
        SelectTelegramRemovalProduct(Repository()).execute(**(args|changes))


def test_proposal_contains_full_code_and_cancel():
    version=uuid4()
    reply=format_removal_proposal(1,'á'*60,999999999,24,version)
    assert version.hex in reply and '/cancelar' in reply and len(reply)<4096
