"""Dados e decisão de confirmação, sem efeitos de persistência."""

from dataclasses import dataclass
from typing import Mapping, Literal

from argos.domain.mercado_livre_url import normalize_mercado_livre_product_url
from argos.domain.product_alias import normalize_product_alias
from argos.domain.target_price import MAX_TARGET_PRICE_CENTS


@dataclass(frozen=True)
class ProductRegistration:
    url: str
    alias: str
    target_price_cents: int
    interval_hours: int


def validate_product_registration(data: Mapping[str, object]) -> ProductRegistration:
    url = data.get("url")
    alias = data.get("alias")
    cents = data.get("target_price_cents")
    hours = data.get("interval_hours")
    if (
        not isinstance(url, str) or not isinstance(alias, str)
        or not isinstance(cents, int) or isinstance(cents, bool)
        or not 1 <= cents <= MAX_TARGET_PRICE_CENTS
        or not isinstance(hours, int) or isinstance(hours, bool)
        or hours not in (12,24)
    ):
        raise ValueError("Dados de cadastro inválidos.")
    return ProductRegistration(
        url=normalize_mercado_livre_product_url(url), alias=normalize_product_alias(alias),
        target_price_cents=cents, interval_hours=hours,
    )


def parse_registration_confirmation(text: str) -> Literal["confirmar", "corrigir"]:
    if not isinstance(text, str):
        raise ValueError("Confirmação inválida.")
    action = text.strip().casefold()
    if action == "confirmar":
        return "confirmar"
    if action == "corrigir":
        return "corrigir"
    raise ValueError("Confirmação inválida.")
