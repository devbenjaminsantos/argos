"""Contrato append-only para sucessos e falhas de coleta."""
from dataclasses import dataclass
from datetime import datetime
import re
from typing import Literal, Protocol
from uuid import UUID

from argos.domain.target_price import MAX_TARGET_PRICE_CENTS


class PriceObservationConflictError(RuntimeError):
    """O UUID já identifica uma observação com conteúdo diferente."""


@dataclass(frozen=True, slots=True)
class PriceObservation:
    observation_id: UUID
    product_id: UUID
    telegram_user_id: int
    observed_at: datetime
    target_price_cents: int
    status: Literal["success", "failure"]
    price_cents: int | None = None
    source: Literal["json-ld", "meta", "visible-dom"] | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        base_valid = (
            isinstance(self.observation_id, UUID)
            and isinstance(self.product_id, UUID)
            and isinstance(self.telegram_user_id, int)
            and not isinstance(self.telegram_user_id, bool)
            and self.telegram_user_id > 0
            and isinstance(self.observed_at, datetime)
            and self.observed_at.utcoffset() is not None
            and isinstance(self.target_price_cents, int)
            and not isinstance(self.target_price_cents, bool)
            and 1 <= self.target_price_cents <= MAX_TARGET_PRICE_CENTS
        )
        success = (
            self.status == "success"
            and isinstance(self.price_cents, int)
            and not isinstance(self.price_cents, bool)
            and 1 <= self.price_cents <= MAX_TARGET_PRICE_CENTS
            and self.source in ("json-ld", "meta", "visible-dom")
            and self.error_code is None
        )
        failure = (
            self.status == "failure"
            and self.price_cents is None and self.source is None
            and isinstance(self.error_code, str)
            and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", self.error_code) is not None
        )
        if not base_valid or not (success or failure):
            raise ValueError("Observação de preço inválida.")


class PriceObservationRepository(Protocol):
    def find(
        self, *, observation_id: UUID, product_id: UUID,
        telegram_user_id: int,
    ) -> PriceObservation | None:
        """Recupera somente quando chave, produto e proprietário coincidem."""
        ...

    def append(self, observation: PriceObservation) -> None:
        """Repete o mesmo UUID/dados sem duplicar; conflito divergente falha."""
        ...
