"""Testes isolados do caso de uso `/cancelar`."""

import pytest
from datetime import UTC, datetime
from uuid import uuid4
from argos.application.ports.telegram_messages import TelegramMessage

from argos.application.errors import ApplicationError
from argos.application.use_cases.cancel import CancelTelegramConversation


class _ConversationsStub:
    def __init__(self, *, exists: bool) -> None:
        self.exists = exists
        self.owners: list[int] = []

    def cancel_for_update(self, *, telegram_user_id: int, chat_id: int, replies, **kwargs):
        self.owners.append(telegram_user_id)
        return TelegramMessage(chat_id=chat_id, text=replies.cancelled if self.exists else replies.nothing_to_cancel)


@pytest.mark.parametrize(
    ("exists", "expected"),
    [
        (True, "Operação cancelada"),
        (False, "Não há nenhuma operação em andamento"),
    ],
)
def test_cancel_is_scoped_to_owner_and_reports_result(
    exists: bool, expected: str
) -> None:
    conversations = _ConversationsStub(exists=exists)

    reply = CancelTelegramConversation(conversations).execute(
        update_id=1, lease_token=uuid4(), observed_at=datetime.now(UTC),
        telegram_user_id=700,
        chat_id=800,
        text="  /CANCELAR  ",
    )

    assert conversations.owners == [700]
    assert reply.chat_id == 800
    assert expected in reply.text


@pytest.mark.parametrize(
    ("telegram_user_id", "chat_id", "text"),
    [(0, 800, "/cancelar"), (700, 0, "/cancelar"), (700, 800, "/start")],
)
def test_cancel_rejects_invalid_input_before_repository(
    telegram_user_id: int, chat_id: int, text: str
) -> None:
    conversations = _ConversationsStub(exists=True)

    with pytest.raises(ApplicationError):
        CancelTelegramConversation(conversations).execute(
            update_id=1, lease_token=uuid4(), observed_at=datetime.now(UTC),
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            text=text,
        )

    assert conversations.owners == []


@pytest.mark.parametrize('changes',[{'telegram_user_id':True},{'update_id':-1},{'lease_token':None},{'observed_at':datetime(2026,9,14)}])
def test_invalid_claim_never_reaches_repository(changes):
    conversations=_ConversationsStub(exists=True)
    args=dict(update_id=1,lease_token=uuid4(),observed_at=datetime.now(UTC),telegram_user_id=700,chat_id=800,text='/cancelar')
    with pytest.raises(ApplicationError):
        CancelTelegramConversation(conversations).execute(**(args|changes))
    assert conversations.owners==[]
