"""Contratos para localizar um produto ativo sem romper o escopo do proprietário."""
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from argos.domain.product_alias import normalize_product_alias
from argos.domain.products.registration import mercado_livre_product_key
from argos.domain.target_price import MAX_TARGET_PRICE_CENTS


@dataclass(frozen=True, slots=True)
class ProductVerificationTarget:
    product_id: UUID
    product_key: str
    url: str = field(repr=False)
    alias: str = field(repr=False)
    target_price_cents: int

    def __post_init__(self) -> None:
        try:
            valid = (
                isinstance(self.product_id, UUID)
                and mercado_livre_product_key(self.url) == self.product_key
                and normalize_product_alias(self.alias) == self.alias
                and isinstance(self.target_price_cents, int)
                and not isinstance(self.target_price_cents, bool)
                and 1 <= self.target_price_cents <= MAX_TARGET_PRICE_CENTS
            )
        except ValueError:
            valid = False
        if not valid:
            raise ValueError("Alvo de verificação inválido.")


class ProductVerificationTargets(Protocol):
    def find_active(self, *, telegram_user_id: int,
                    product_id: UUID) -> ProductVerificationTarget | None:
        """Retorna somente produto ativo pertencente ao usuário informado."""
        ...
