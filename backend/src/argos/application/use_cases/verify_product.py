"""Verificação manual interna; não persiste observação nem envia mensagem."""
from dataclasses import dataclass, field
from uuid import UUID

from argos.application.errors import ApplicationError
from argos.application.ports.product_collection import ProductCollectionError, ProductCollector
from argos.application.ports.product_verification import ProductVerificationTargets


@dataclass(frozen=True, slots=True)
class ProductVerification:
    product_id: UUID
    alias: str = field(repr=False)
    title: str = field(repr=False)
    current_price_cents: int
    target_price_cents: int
    target_reached: bool
    source: str


_COLLECTION_ERRORS = {
    "access_blocked": ("collection_blocked", "O Mercado Livre bloqueou temporariamente a verificação."),
    "product_unavailable": ("product_unavailable", "O produto parece indisponível."),
    "price_not_found": ("price_not_found", "Não foi possível identificar um preço válido."),
    "timeout": ("collection_timeout", "A verificação excedeu o tempo permitido."),
}


class VerifyProduct:
    def __init__(self, targets: ProductVerificationTargets,
                 collector: ProductCollector) -> None:
        self._targets = targets
        self._collector = collector

    def execute(self, *, telegram_user_id: int, product_id: UUID) -> ProductVerification:
        if (not isinstance(telegram_user_id, int) or isinstance(telegram_user_id, bool)
            or telegram_user_id <= 0 or not isinstance(product_id, UUID)):
            raise ApplicationError("invalid_input", "Produto para verificação inválido.")
        target = self._targets.find_active(
            telegram_user_id=telegram_user_id, product_id=product_id)
        if target is None:
            # Ausente e pertencente a outro usuário têm a mesma resposta.
            raise ApplicationError("product_not_found", "Produto não encontrado.")
        try:
            collected = self._collector.collect(target.url)
        except ProductCollectionError as error:
            code, message = _COLLECTION_ERRORS.get(
                error.code, ("collection_failed", "Não foi possível verificar o produto."))
            raise ApplicationError(code, message) from None
        if collected.external_id != target.product_key:
            raise ApplicationError(
                "product_identity_changed",
                "O anúncio respondeu com uma identidade de produto diferente.",
            )
        return ProductVerification(
            product_id=target.product_id, alias=target.alias, title=collected.title,
            current_price_cents=collected.price_cents,
            target_price_cents=target.target_price_cents,
            target_reached=collected.price_cents <= target.target_price_cents,
            source=collected.source,
        )
