from datetime import UTC, datetime
from uuid import uuid4

import pytest

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.use_cases.receive_registration_target_price import ReceiveTelegramRegistrationTargetPrice

_INPUT = dict(update_id=1, lease_token=uuid4(), telegram_user_id=700, chat_id=800,
              text="https://produto.mercadolivre.com.br/MLB-123-produto", observed_at=datetime.now(UTC))


class Repository:
    def __init__(self):
        self.calls = []
        self.reply = TelegramMessage(chat_id=800, text="Resultado original")

    def receive_for_update(self, **kwargs):
        self.calls.append(kwargs)
        return self.reply


def test_passes_identity_raw_text_and_price_and_returns_persisted_reply():
    repo = Repository()
    raw = " R$ 2.500,90 "
    assert ReceiveTelegramRegistrationTargetPrice(repo).execute(**(_INPUT | {"text": raw})) is repo.reply
    call = repo.calls[0]
    for key in ("update_id", "lease_token", "telegram_user_id", "chat_id", "observed_at"):
        assert call[key] == _INPUT[key]
    assert call["text"] == raw
    assert call["target_price_cents"] == 250090


def test_invalid_price_requests_durable_reply():
    repo = Repository()
    assert ReceiveTelegramRegistrationTargetPrice(repo).execute(**_INPUT) is repo.reply
    assert repo.calls[0]["target_price_cents"] is None


@pytest.mark.parametrize("changes", [
    {"update_id": True}, {"update_id": -1}, {"telegram_user_id": 0},
    {"chat_id": False}, {"lease_token": "bad"}, {"text": "/adicionar"},
    {"text": " "}, {"text": None}, {"text": "x" * 4097},
    {"observed_at": datetime(2026, 9, 14)},
])
def test_invalid_input_never_accesses_repository(changes):
    repo = Repository()
    with pytest.raises(ApplicationError):
        ReceiveTelegramRegistrationTargetPrice(repo).execute(**(_INPUT | changes))
    assert repo.calls == []


def test_lost_lease_is_propagated():
    class LostLease:
        def receive_for_update(self, **kwargs):
            raise RuntimeError("Lease perdido")
    with pytest.raises(RuntimeError, match="Lease perdido"):
        ReceiveTelegramRegistrationTargetPrice(LostLease()).execute(**_INPUT)
