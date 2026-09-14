from datetime import UTC, datetime
from uuid import uuid4
import pytest
from argos.application.errors import ApplicationError
from argos.application.use_cases.list_products import ListTelegramProducts, format_products


def test_bounded_plain_text_with_three_maximum_aliases():
    reply = format_products([(i, "á"*60,999999999,24) for i in (1,2,3)])
    assert len(reply)<4096
    assert "R$ 9.999.999,99" in reply
    assert "ainda não estão disponíveis" in reply


@pytest.mark.parametrize("changes",[{"telegram_user_id":True},{"chat_id":0},{"update_id":-1},{"lease_token":None},{"text":"/remover"},{"observed_at":datetime(2026,9,14)}])
def test_invalid_command_or_identity_never_reaches_repository(changes):
    class Repository:
        def list_for_update(self, **kwargs):
            pytest.fail("Repository must not be called")
    args=dict(update_id=1,lease_token=uuid4(),telegram_user_id=700,chat_id=800,text="/produtos",observed_at=datetime.now(UTC))
    with pytest.raises(ApplicationError):
        ListTelegramProducts(Repository()).execute(**(args|changes))
