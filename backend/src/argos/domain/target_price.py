"""Preço-alvo em BRL convertido exatamente para centavos."""

import re

MAX_TARGET_PRICE_CENTS = 999_999_999
_PRICE = re.compile(r"(?:R\$ ?)?([0-9]+|[1-9][0-9]{0,2}(?:\.[0-9]{3})+)(?:,([0-9]{1,2}))?")


def parse_target_price_cents(raw: str) -> int:
    if not isinstance(raw, str) or len(raw) > 64:
        raise ValueError("Preço-alvo inválido.")
    match = _PRICE.fullmatch(raw.strip())
    if match is None:
        raise ValueError("Preço-alvo inválido.")
    whole, decimal = match.groups()
    cents = int(whole.replace(".", "")) * 100 + int((decimal or "").ljust(2, "0"))
    if not 1 <= cents <= MAX_TARGET_PRICE_CENTS:
        raise ValueError("Preço-alvo inválido.")
    return cents


def format_target_price_brl(cents: int) -> str:
    if not isinstance(cents, int) or isinstance(cents, bool) or not 1 <= cents <= MAX_TARGET_PRICE_CENTS:
        raise ValueError("Preço-alvo inválido.")
    return f"R$ {cents // 100:,}".replace(",", ".") + f",{cents % 100:02d}"
