from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from argos.application.errors import ApplicationError
from argos.application.ports.price_observations import PriceObservation
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.use_cases.verify_telegram_product import (
    VerifyTelegramProduct,
    parse_verify_product_command,
)

PRODUCT_ID = UUID("12345678-1234-5678-9234-567812345678")
NOW = datetime(2026, 9, 16, 19, 0, tzinfo=timezone.utc)
COMMAND = f"/verificar {PRODUCT_ID}"


class Results:
    def __init__(self, existing=None, save_error=None, events=None):
        self.existing = existing
        self.save_error = save_error
        self.events = events if events is not None else []
        self.saved = []

    def find_for_claim(self, **values):
        self.events.append("reply:find")
        return self.existing

    def save_for_claim(self, **values):
        self.events.append("reply:save")
        if self.save_error:
            raise self.save_error
        self.saved.append(values["reply"])
        return values["reply"]


class Observations:
    def __init__(self, item=None, events=None):
        self.item = item
        self.events = events if events is not None else []

    def find(self, **values):
        self.events.append("observation:find")
        return self.item

    def append(self, item):
        self.item = item


class Verifier:
    def __init__(self, observations, *, failure=None, events=None):
        self.observations = observations
        self.failure = failure
        self.events = events if events is not None else []
        self.calls = []

    def execute(self, **values):
        self.events.append("collect")
        self.calls.append(values)
        request = parse_verify_product_command(update_id=1, text=COMMAND)
        if self.failure is not None:
            if self.failure.code != "product_not_found":
                self.observations.item = failed(request.observation_id, self.failure.code)
            raise self.failure
        self.observations.item = succeeded(request.observation_id)


def succeeded(observation_id):
    return PriceObservation(
        observation_id=observation_id, product_id=PRODUCT_ID,
        telegram_user_id=700, observed_at=NOW, target_price_cents=15_000,
        status="success", price_cents=14_999, source="meta",
    )


def failed(observation_id, code="collection_timeout"):
    return PriceObservation(
        observation_id=observation_id, product_id=PRODUCT_ID,
        telegram_user_id=700, observed_at=NOW, target_price_cents=15_000,
        status="failure", error_code=code,
    )


def execute(results, observations, verifier, **changes):
    values = dict(
        update_id=1, lease_token=uuid4(), telegram_user_id=700,
        chat_id=800, text=COMMAND, observed_at=NOW,
    ) | changes
    return VerifyTelegramProduct(
        verifier=verifier, observations=observations, results=results,
    ).execute(**values)


def test_durable_reply_short_circuits_observation_and_collection():
    events = []
    reply = TelegramMessage(chat_id=800, text="Resposta original")
    results = Results(existing=reply, events=events)
    observations = Observations(events=events)
    verifier = Verifier(observations, events=events)
    assert execute(results, observations, verifier) == reply
    assert events == ["reply:find"]


def test_durable_observation_short_circuits_collection_and_saves_reply():
    events = []
    request = parse_verify_product_command(update_id=1, text=COMMAND)
    observations = Observations(succeeded(request.observation_id), events)
    results = Results(events=events)
    verifier = Verifier(observations, events=events)
    reply = execute(results, observations, verifier)
    assert events == ["reply:find", "observation:find", "reply:save"]
    assert verifier.calls == []
    assert "R$ 149,99" in reply.text


def test_new_success_collects_once_then_reads_observation_and_saves():
    events = []
    observations = Observations(events=events)
    results = Results(events=events)
    verifier = Verifier(observations, events=events)
    reply = execute(results, observations, verifier)
    assert events == [
        "reply:find", "observation:find", "collect",
        "observation:find", "reply:save",
    ]
    assert len(verifier.calls) == 1
    assert "preço-alvo foi atingido" in reply.text


def test_persisted_collection_failure_is_recovered_and_checkpointed():
    observations = Observations()
    results = Results()
    verifier = Verifier(
        observations,
        failure=ApplicationError("collection_timeout", "detail"),
    )
    reply = execute(results, observations, verifier)
    assert "tempo permitido" in reply.text
    assert len(results.saved) == 1


def test_missing_product_has_safe_durable_reply_without_observation():
    observations = Observations()
    results = Results()
    verifier = Verifier(
        observations,
        failure=ApplicationError("product_not_found", "Produto não encontrado."),
    )
    reply = execute(results, observations, verifier)
    assert reply.text == "Não foi possível verificar o produto."
    assert observations.item is None


def test_lease_loss_after_collection_keeps_observation_for_retry():
    observations = Observations()
    verifier = Verifier(observations)
    with pytest.raises(RuntimeError, match="lease lost"):
        execute(
            Results(save_error=RuntimeError("lease lost")),
            observations, verifier,
        )
    assert observations.item is not None
    retry_results = Results()
    retry_verifier = Verifier(observations)
    execute(retry_results, observations, retry_verifier)
    assert retry_verifier.calls == []


@pytest.mark.parametrize("changes", [
    {"lease_token": "bad"}, {"telegram_user_id": True},
    {"chat_id": 0}, {"observed_at": datetime(2026, 9, 16, 19, 0)},
])
def test_invalid_envelope_stops_before_checkpoints(changes):
    results = Results()
    observations = Observations()
    with pytest.raises(ApplicationError, match="Update de verificação inválido"):
        execute(results, observations, Verifier(observations), **changes)
    assert results.events == []
