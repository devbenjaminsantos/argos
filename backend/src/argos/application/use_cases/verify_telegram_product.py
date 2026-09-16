"""Contrato Telegram de verificação, ainda sem ativação no worker."""

from dataclasses import dataclass
import re
from uuid import UUID, uuid5

from argos.application.errors import ApplicationError
from argos.application.use_cases.verify_product import ProductVerification
from argos.domain.target_price import format_target_price_brl

_OBSERVATION_NAMESPACE = UUID("a3000000-0000-4000-8000-000000000000")
_COMMAND = re.compile(r"/verificar[ \t]+([^ \t\r\n]+)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class VerifyTelegramProductRequest:
    product_id: UUID
    observation_id: UUID


def parse_verify_product_command(
    *, update_id: int, text: str,
) -> VerifyTelegramProductRequest:
    if (not isinstance(update_id, int) or isinstance(update_id, bool)
        or update_id < 0 or not isinstance(text, str)):
        raise ApplicationError("invalid_input", "Comando de verificação inválido.")
    match = _COMMAND.fullmatch(text.strip())
    if match is None:
        raise ApplicationError(
            "invalid_verify_command",
            "Envie /verificar seguido do código completo do produto.",
        )
    try:
        product_id = UUID(match.group(1))
    except ValueError:
        raise ApplicationError(
            "invalid_product_code", "O código completo do produto é inválido."
        ) from None
    if str(product_id) != match.group(1).lower():
        raise ApplicationError(
            "invalid_product_code", "O código completo do produto é inválido."
        )
    return VerifyTelegramProductRequest(
        product_id=product_id,
        observation_id=uuid5(_OBSERVATION_NAMESPACE, f"telegram-update:{update_id}"),
    )


def format_product_verification(result: ProductVerification) -> str:
    current = format_target_price_brl(result.current_price_cents)
    target = format_target_price_brl(result.target_price_cents)
    comparison = (
        "O preço-alvo foi atingido."
        if result.target_reached else "O preço-alvo ainda não foi atingido."
    )
    return (
        f"{result.alias}\n\nPreço atual: {current}\n"
        f"Preço-alvo: {target}\n\n{comparison}"
    )


_FAILURE_MESSAGES = {
    "collection_blocked": "O Mercado Livre bloqueou temporariamente a verificação.",
    "product_unavailable": "O produto parece indisponível.",
    "price_not_found": "Não foi possível identificar um preço válido.",
    "collection_timeout": "A verificação excedeu o tempo permitido.",
    "collection_failed": "Não foi possível verificar o produto.",
    "product_identity_changed": "O anúncio respondeu com uma identidade de produto diferente.",
}


def format_product_verification_failure(error: ApplicationError) -> str:
    return _FAILURE_MESSAGES.get(
        error.code, "Não foi possível verificar o produto."
    )
