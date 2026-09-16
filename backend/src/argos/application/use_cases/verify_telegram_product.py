"""Contrato Telegram de verificação, ainda sem ativação no worker."""

from dataclasses import dataclass
from datetime import datetime
import re
from uuid import UUID, uuid5

from argos.application.errors import ApplicationError
from argos.application.ports.price_observations import (
    PriceObservation,
    PriceObservationRepository,
)
from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_verification_results import (
    TelegramVerificationResults,
)
from argos.application.use_cases.verify_product import VerifyProduct
from argos.domain.target_price import format_target_price_brl

_OBSERVATION_NAMESPACE = UUID("a3000000-0000-4000-8000-000000000000")
_COMMAND = re.compile(r"/verificar[ \t]+([^ \t\r\n]+)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class VerifyTelegramProductRequest:
    product_id: UUID
    observation_id: UUID


def is_verify_product_input(text: str) -> bool:
    if not isinstance(text, str):
        return False
    value = text.strip().casefold()
    return (
        value == "/verificar"
        or value.startswith("/verificar ")
        or value.startswith("/verificar\t")
    )


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


_FAILURE_MESSAGES = {
    "invalid_verify_command": "Envie /verificar seguido do código completo do produto.",
    "invalid_product_code": "O código completo do produto é inválido.",
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


def format_price_observation(observation: PriceObservation) -> str:
    if observation.status == "failure":
        return format_product_verification_failure(
            ApplicationError(observation.error_code or "collection_failed", "")
        )
    if observation.price_cents is None:
        raise RuntimeError("Observação de sucesso sem preço.")
    current = format_target_price_brl(observation.price_cents)
    target = format_target_price_brl(observation.target_price_cents)
    comparison = (
        "O preço-alvo foi atingido."
        if observation.price_cents <= observation.target_price_cents
        else "O preço-alvo ainda não foi atingido."
    )
    return (
        f"Verificação concluída.\n\nPreço atual: {current}\n"
        f"Preço-alvo: {target}\n\n{comparison}"
    )


class VerifyTelegramProduct:
    """Orquestra recuperação, coleta e checkpoint sem transação longa."""

    def __init__(
        self, *, verifier: VerifyProduct,
        observations: PriceObservationRepository,
        results: TelegramVerificationResults,
    ) -> None:
        self._verifier = verifier
        self._observations = observations
        self._results = results

    def execute(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, text: str,
        observed_at: datetime,
    ) -> TelegramMessage:
        if (not isinstance(lease_token, UUID)
            or not isinstance(telegram_user_id, int)
            or isinstance(telegram_user_id, bool) or telegram_user_id <= 0
            or not isinstance(chat_id, int) or isinstance(chat_id, bool)
            or chat_id <= 0 or not isinstance(observed_at, datetime)
            or observed_at.utcoffset() is None):
            raise ApplicationError("invalid_input", "Update de verificação inválido.")
        claim = dict(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
        )
        existing_reply = self._results.find_for_claim(**claim)
        if existing_reply is not None:
            return existing_reply

        try:
            request = parse_verify_product_command(update_id=update_id, text=text)
        except ApplicationError as error:
            return self._results.save_for_claim(
                **claim,
                reply=TelegramMessage(
                    chat_id=chat_id,
                    text=format_product_verification_failure(error),
                ),
            )
        observation = self._observations.find(
            observation_id=request.observation_id,
            product_id=request.product_id,
            telegram_user_id=telegram_user_id,
        )
        if observation is None:
            try:
                self._verifier.execute(
                    telegram_user_id=telegram_user_id,
                    product_id=request.product_id,
                    observation_id=request.observation_id,
                    observed_at=observed_at,
                )
            except ApplicationError as error:
                observation = self._observations.find(
                    observation_id=request.observation_id,
                    product_id=request.product_id,
                    telegram_user_id=telegram_user_id,
                )
                text_reply = (
                    format_price_observation(observation)
                    if observation is not None
                    else format_product_verification_failure(error)
                )
            else:
                observation = self._observations.find(
                    observation_id=request.observation_id,
                    product_id=request.product_id,
                    telegram_user_id=telegram_user_id,
                )
                if observation is None:
                    raise RuntimeError("Verificação concluída sem observação durável.")
                text_reply = format_price_observation(observation)
        else:
            text_reply = format_price_observation(observation)

        return self._results.save_for_claim(
            **claim, reply=TelegramMessage(chat_id=chat_id, text=text_reply),
        )
