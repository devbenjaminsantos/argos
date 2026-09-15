import json
from decimal import Decimal
from pathlib import Path
from html.parser import HTMLParser
import pytest
from argos.infrastructure.scrapers.mercado_livre.json_ld import (
    StructuredPriceError, extract_json_ld_price, to_price_cents,
)

@pytest.mark.parametrize('value,expected', [
    ('3499.90', 349990), (150, 15000), (Decimal('0.01'), 1),
    ('9999999.99', 999999999), ('150.000', 15000),
    (True, None), (150.1, None), ('0', None), ('-1', None),
    ('NaN', None), ('Infinity', None), ('1e2', None), ('1,50', None),
    ('1.000000000000000000000000000001', None), ('R$150', None), ('1.001', None), ('10000000', None), (None, None),
])
def test_money(value, expected):
    assert to_price_cents(value) == expected


def product(price='150.00', **offer):
    return {'@type': 'Product', 'offers': {'price': price, **offer}}

@pytest.mark.parametrize('shape', [
    product(), [product()], {'@graph': [product()]},
    {'@type': ['Thing', 'Product'], 'offers': [{'lowPrice': '150.00'}]},
])
def test_supported_shapes(shape):
    assert extract_json_ld_price([json.dumps(shape)]) == 15000


def test_decimal_json_number_and_malformed_script():
    assert extract_json_ld_price(['{broken', '{"@type":"Product","offers":{"price":150.29}}']) == 15029


def test_ignores_non_product_and_invalid_values():
    assert extract_json_ld_price([json.dumps({'@type':'Offer','price':'10'}),
                                  json.dumps(product('0'))]) is None


def test_equal_offers_are_unambiguous():
    assert extract_json_ld_price([json.dumps([product(), product()])]) == 15000


def test_conflicting_offers_fail():
    with pytest.raises(StructuredPriceError, match='ambiguous_price'):
        extract_json_ld_price([json.dumps([product(), product('151')])])

@pytest.mark.parametrize('currency', ['USD', 'brl', '', 123])
def test_currency_failure_is_explicit(currency):
    with pytest.raises(StructuredPriceError, match='unsupported_currency'):
        extract_json_ld_price([json.dumps(product(priceCurrency=currency))])


def test_limits():
    with pytest.raises(StructuredPriceError, match='structured_data_limit'):
        extract_json_ld_price(['{}'] * 33)
    value = product()
    for _ in range(34): value = [value]
    with pytest.raises(StructuredPriceError, match='structured_data_limit'):
        extract_json_ld_price([json.dumps(value)])


def test_prepared_fixture_json_ld_priority():
    class Scripts(HTMLParser):
        active = False
        def __init__(self):
            super().__init__()
            self.values = []
        def handle_starttag(self, tag, attrs):
            self.active = tag == 'script' and dict(attrs).get('type') == 'application/ld+json'
        def handle_data(self, data):
            if self.active: self.values.append(data)
        def handle_endtag(self, tag):
            if tag == 'script': self.active = False
    parser = Scripts()
    root = Path(__file__).parents[1] / 'fixtures/mercado_livre'
    parser.feed((root / 'json_ld_priority.html').read_text())
    assert extract_json_ld_price(parser.values) == 349990
