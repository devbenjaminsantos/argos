from datetime import datetime, timezone
from uuid import UUID

import pytest

from argos.application.errors import ApplicationError
from argos.application.ports.price_observations import PriceObservation
from argos.application.use_cases.verify_telegram_product import (
    format_price_observation,
    format_product_verification_failure,
    parse_verify_product_command,
)

PRODUCT_ID = UUID("12345678-1234-5678-9234-567812345678")


def test_exact_full_product_code_is_parsed_case_insensitively():
    parsed = parse_verify_product_command(
        update_id=42, text=f"  /VERIFICAR\t{PRODUCT_ID}  ",
    )
    assert parsed.product_id == PRODUCT_ID


def test_observation_id_is_stable_per_update_and_distinct_between_updates():
    first = parse_verify_product_command(
        update_id=42, text=f"/verificar {PRODUCT_ID}",
    )
    replay = parse_verify_product_command(
        update_id=42, text=f"/VERIFICAR {PRODUCT_ID}",
    )
    other = parse_verify_product_command(
        update_id=43, text=f"/verificar {PRODUCT_ID}",
    )
    assert first.observation_id == replay.observation_id
    assert first.observation_id != other.observation_id


@pytest.mark.parametrize("update_id", [-1, True, "42"])
def test_invalid_update_id_is_rejected(update_id):
    with pytest.raises(ApplicationError) as raised:
        parse_verify_product_command(
            update_id=update_id, text=f"/verificar {PRODUCT_ID}",
        )
    assert raised.value.code == "invalid_input"


@pytest.mark.parametrize("text", [
    "/verificar", f"/verificar {PRODUCT_ID} extra", f"x /verificar {PRODUCT_ID}",
    f"/verificar\n{PRODUCT_ID}", "/produtos",
])
def test_incomplete_or_extra_command_is_rejected(text):
    with pytest.raises(ApplicationError) as raised:
        parse_verify_product_command(update_id=42, text=text)
    assert raised.value.code == "invalid_verify_command"


@pytest.mark.parametrize("code", [
    "not-a-uuid", "12345678-1234-5678-9234-56781234567",
    "12345678123456789234567812345678",
])
def test_noncanonical_product_code_is_rejected(code):
    with pytest.raises(ApplicationError) as raised:
        parse_verify_product_command(update_id=42, text=f"/verificar {code}")
    assert raised.value.code == "invalid_product_code"


@pytest.mark.parametrize("reached,expected", [
    (True, "O preço-alvo foi atingido."),
    (False, "O preço-alvo ainda não foi atingido."),
])
def test_success_reply_contains_prices_and_comparison(reached, expected):
    current_price = 349_990 if reached else 350_001
    observation = PriceObservation(
        observation_id=UUID("a3000000-0000-4000-8000-000000000001"),
        product_id=PRODUCT_ID, telegram_user_id=700,
        observed_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        target_price_cents=350_000, status="success",
        price_cents=current_price, source="json-ld",
    )
    reply = format_price_observation(observation)
    assert "Verificação concluída." in reply
    assert ("R$ 3.499,90" if reached else "R$ 3.500,01") in reply
    assert "R$ 3.500,00" in reply
    assert expected in reply
    assert "json-ld" not in reply


@pytest.mark.parametrize("code,expected", [
    ("collection_blocked", "bloqueou temporariamente"),
    ("collection_timeout", "tempo permitido"),
    ("product_identity_changed", "identidade de produto diferente"),
    ("internal_detail", "Não foi possível verificar o produto."),
])
def test_failure_reply_uses_only_allowlisted_public_messages(code, expected):
    error = ApplicationError(code, "detalhe que não deve aparecer")
    reply = format_product_verification_failure(error)
    assert expected in reply
    assert "detalhe que não deve aparecer" not in reply
