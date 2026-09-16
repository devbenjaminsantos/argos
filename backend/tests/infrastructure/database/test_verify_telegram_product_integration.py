"""Orquestração recuperável de `/verificar` em PostgreSQL real."""

import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import insert, text

from argos.application.ports.product_collection import CollectedProduct
from argos.application.use_cases.verify_product import VerifyProduct
from argos.application.use_cases.verify_telegram_product import VerifyTelegramProduct
from argos.config import Settings
from argos.infrastructure.database.models import MonitoredProductRecord
from argos.infrastructure.database.price_observations import (
    PostgreSQLPriceObservationRepository,
)
from argos.infrastructure.database.product_verification import (
    PostgreSQLProductVerificationTargets,
)
from argos.infrastructure.database.telegram_verification_results import (
    PostgreSQLTelegramVerificationResults,
)
from argos.telegram_worker import build_worker
from tests.infrastructure.database.test_telegram_verification_results_integration import (
    COMMAND,
    PRODUCT_ID,
    context,
)

pytestmark = pytest.mark.skipif(
    os.getenv("ARGOS_TEST_DATABASE_URL") is None,
    reason="PostgreSQL de teste ausente.",
)


class Collector:
    def __init__(self, engine, *, expire_lease=False, forbidden=False):
        self.engine = engine
        self.expire_lease = expire_lease
        self.forbidden = forbidden
        self.calls = 0

    def collect(self, url):
        self.calls += 1
        if self.forbidden:
            raise AssertionError("A recuperação não pode repetir a coleta.")
        if self.expire_lease:
            with self.engine.begin() as connection:
                connection.execute(text(
                    "UPDATE telegram_update_inbox "
                    "SET lease_expires_at=clock_timestamp()-interval '1 second'"
                ))
        return CollectedProduct(
            store="mercado-livre", external_id="MLB123", url=url,
            title="Caneca atual", price_cents=14_999, source="meta",
        )


def prepare(context, collector):
    engine, lease = context
    now = datetime.now(UTC)
    with engine.begin() as connection:
        connection.execute(text(
            "INSERT INTO telegram_users VALUES (700,800,:now,:now)"
        ), {"now": now})
        connection.execute(insert(MonitoredProductRecord).values(
            id=PRODUCT_ID, telegram_user_id=700, slot=1,
            product_key="MLB123", url="https://mercadolivre.com.br/p/MLB123",
            alias="Caneca", target_price_cents=15_000, interval_hours=12,
            created_at=now, removed_at=None,
        ))
    observations = PostgreSQLPriceObservationRepository(engine)
    use_case = VerifyTelegramProduct(
        verifier=VerifyProduct(
            PostgreSQLProductVerificationTargets(engine), collector,
            observations,
        ),
        observations=observations,
        results=PostgreSQLTelegramVerificationResults(engine),
    )
    return use_case, now, lease


def execute(use_case, now, lease):
    return use_case.execute(
        update_id=1, lease_token=lease, telegram_user_id=700,
        chat_id=800, text=COMMAND, observed_at=now,
    )


def test_success_replay_uses_durable_reply_without_second_collection(context):
    collector = Collector(context[0])
    use_case, now, lease = prepare(context, collector)
    first = execute(use_case, now, lease)
    replay = execute(use_case, now, lease)
    assert replay == first
    assert collector.calls == 1
    with context[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT count(*) FROM product_price_observations"
        )) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM telegram_registration_results"
        )) == 1


def test_retry_after_lease_loss_recovers_observation_without_collection(context):
    collector = Collector(context[0], expire_lease=True)
    use_case, now, lease = prepare(context, collector)
    with pytest.raises(RuntimeError, match="Claim ou payload"):
        execute(use_case, now, lease)
    assert collector.calls == 1

    recovered_lease = uuid4()
    with context[0].begin() as connection:
        connection.execute(text(
            "UPDATE telegram_update_inbox SET lease_token=:lease, "
            "lease_expires_at=clock_timestamp()+interval '5 minutes'"
        ), {"lease": recovered_lease})
    recovery_collector = Collector(context[0], forbidden=True)
    observations = PostgreSQLPriceObservationRepository(context[0])
    recovered = VerifyTelegramProduct(
        verifier=VerifyProduct(
            PostgreSQLProductVerificationTargets(context[0]),
            recovery_collector, observations,
        ),
        observations=observations,
        results=PostgreSQLTelegramVerificationResults(context[0]),
    )
    reply = execute(recovered, now + timedelta(seconds=1), recovered_lease)
    assert "R$ 149,99" in reply.text
    assert recovery_collector.calls == 0


def test_composed_worker_sends_checkpointed_reply_and_completes_inbox(context):
    collector = Collector(context[0])
    _, now, _ = prepare(context, collector)
    with context[0].begin() as connection:
        connection.execute(text(
            "UPDATE telegram_update_inbox SET status='pending', "
            "lease_token=NULL, lease_expires_at=NULL, next_attempt_at=:now"
        ), {"now": now})

    class Sender:
        def __init__(self):
            self.messages = []

        def send(self, message):
            self.messages.append(message)

    sender = Sender()
    worker = build_worker(
        Settings(environment="test"), engine=context[0],
        sender=sender, collector=collector,
    )
    assert worker.process_next(now=now)
    assert collector.calls == 1
    assert len(sender.messages) == 1
    assert "R$ 149,99" in sender.messages[0].text
    with context[0].connect() as connection:
        assert connection.scalar(text(
            "SELECT status FROM telegram_update_inbox WHERE update_id=1"
        )) == "completed"
        assert connection.scalar(text(
            "SELECT count(*) FROM product_price_observations"
        )) == 1
        assert connection.scalar(text(
            "SELECT count(*) FROM telegram_registration_results"
        )) == 1
