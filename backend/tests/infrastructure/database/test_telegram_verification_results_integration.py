"""Checkpoint da resposta de verificação contra PostgreSQL real."""

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, text

from argos.application.ports.telegram_messages import TelegramMessage
from argos.infrastructure.database.telegram_verification_results import (
    PostgreSQLTelegramVerificationResults,
)

_URL = os.getenv("ARGOS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(_URL is None, reason="PostgreSQL de teste ausente.")
PRODUCT_ID = UUID("12345678-1234-5678-9234-567812345678")
COMMAND = f"/verificar {PRODUCT_ID}"


@pytest.fixture
def context():
    engine = create_engine(_URL)
    now = datetime.now(UTC)
    lease = uuid4()
    cleanup = (
        "TRUNCATE product_price_observations, monitored_products, "
        "telegram_registration_results, telegram_update_inbox, "
        "telegram_conversation_drafts, telegram_users"
    )
    payload = (
        '{"message":{"from":{"id":700},'
        '"chat":{"id":800,"type":"private"},'
        f'"text":"{COMMAND}"}}}}'
    )
    with engine.begin() as connection:
        connection.execute(text(cleanup))
        connection.execute(text(
            "INSERT INTO telegram_update_inbox "
            "(update_id,payload,status,received_at,next_attempt_at,lease_token,lease_expires_at) "
            "VALUES (1,CAST(:payload AS jsonb),'processing',:now,:now,:lease,:expires)"
        ), {"payload": payload, "now": now, "lease": lease,
            "expires": now + timedelta(minutes=5)})
    try:
        yield engine, lease
    finally:
        with engine.begin() as connection:
            connection.execute(text(cleanup))
        engine.dispose()


def arguments(context, **changes):
    return dict(
        update_id=1, lease_token=context[1], telegram_user_id=700,
        chat_id=800, text=COMMAND,
    ) | changes


def test_absent_result_is_reported_without_creating_row(context):
    repository = PostgreSQLTelegramVerificationResults(context[0])
    assert repository.find_for_claim(**arguments(context)) is None


def test_saved_result_is_recovered_unchanged(context):
    repository = PostgreSQLTelegramVerificationResults(context[0])
    reply = TelegramMessage(chat_id=800, text="Preço verificado.")
    assert repository.save_for_claim(
        **arguments(context), reply=reply,
    ) == reply
    assert repository.find_for_claim(**arguments(context)) == reply


def test_equal_replay_is_idempotent_and_divergent_reply_fails(context):
    repository = PostgreSQLTelegramVerificationResults(context[0])
    reply = TelegramMessage(chat_id=800, text="Preço verificado.")
    repository.save_for_claim(**arguments(context), reply=reply)
    assert repository.save_for_claim(**arguments(context), reply=reply) == reply
    with pytest.raises(RuntimeError, match="Resposta de verificação divergente"):
        repository.save_for_claim(
            **arguments(context),
            reply=TelegramMessage(chat_id=800, text="Outro resultado."),
        )


@pytest.mark.parametrize("changes", [
    {"lease_token": uuid4()}, {"telegram_user_id": 701},
    {"chat_id": 801}, {"text": COMMAND + " "},
])
def test_divergent_claim_or_payload_cannot_read_or_save(context, changes):
    repository = PostgreSQLTelegramVerificationResults(context[0])
    with pytest.raises(RuntimeError, match="Claim ou payload"):
        repository.find_for_claim(**arguments(context, **changes))
    with pytest.raises(RuntimeError, match="Claim ou payload"):
        repository.save_for_claim(
            **arguments(context, **changes),
            reply=TelegramMessage(chat_id=changes.get("chat_id", 800), text="Resposta"),
        )


def test_expired_lease_cannot_save_result(context):
    with context[0].begin() as connection:
        connection.execute(text(
            "UPDATE telegram_update_inbox "
            "SET lease_expires_at=clock_timestamp()-interval '1 second'"
        ))
    with pytest.raises(RuntimeError, match="Claim ou payload"):
        PostgreSQLTelegramVerificationResults(context[0]).save_for_claim(
            **arguments(context), reply=TelegramMessage(chat_id=800, text="Resposta"),
        )
