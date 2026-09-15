"""Preço estruturado isolado; não interpreta HTML nem acessa a rede."""
import json
import re
from decimal import Decimal, InvalidOperation, localcontext
from argos.domain.target_price import MAX_TARGET_PRICE_CENTS


class StructuredPriceError(ValueError):
    """Falha sanitizada que não deve ser mascarada por outra fonte de preço."""
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def to_price_cents(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        return None
    text = str(value).strip()
    if len(text) > 32 or not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', text):
        return None
    try:
        amount = Decimal(text)
        if not 0 < amount <= Decimal(MAX_TARGET_PRICE_CENTS) / 100:
            return None
        with localcontext() as context:
            context.prec = 64
            cents = amount * 100
        if cents != cents.to_integral_value():
            return None
        return int(cents)
    except InvalidOperation:
        return None


def _products(value: object, depth: int = 0):
    if depth > 32:
        raise StructuredPriceError('structured_data_limit')
    if isinstance(value, list):
        for item in value:
            yield from _products(item, depth + 1)
    elif isinstance(value, dict):
        kind = value.get('@type')
        if kind == 'Product' or isinstance(kind, list) and 'Product' in kind:
            yield value
        if '@graph' in value:
            yield from _products(value['@graph'], depth + 1)


def extract_json_ld_price(scripts: list[str]) -> int | None:
    """BRL ou moeda ausente; todos os preços candidatos devem concordar."""
    if len(scripts) > 32 or sum(len(script) for script in scripts) > 2 * 1024 * 1024:
        raise StructuredPriceError('structured_data_limit')
    candidates: set[int] = set()
    for script in scripts:
        try:
            value = json.loads(script, parse_float=Decimal, parse_int=Decimal,
                               parse_constant=lambda _: None)
        except (ValueError, RecursionError):
            continue
        for product in _products(value):
            offers = product.get('offers')
            offers = offers if isinstance(offers, list) else [offers]
            for offer in offers:
                if not isinstance(offer, dict):
                    continue
                currency = offer.get('priceCurrency')
                if currency is not None and currency != 'BRL':
                    raise StructuredPriceError('unsupported_currency')
                # A price present but invalid does not authorize lowPrice fallback.
                price = to_price_cents(offer.get('price', offer.get('lowPrice')))
                if price is not None:
                    candidates.add(price)
    if len(candidates) > 1:
        raise StructuredPriceError('ambiguous_price')
    return next(iter(candidates), None)
