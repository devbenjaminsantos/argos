import pytest
from argos.domain.product_alias import normalize_product_alias


@pytest.mark.parametrize("raw,expected", [("  Caneca   Hello Kitty  ", "Caneca Hello Kitty"), ("Cafe\u0301", "Café"), ("Caneca ☕", "Caneca ☕"), ("x" * 60, "x" * 60)])
def test_normalizes_alias(raw, expected):
    assert normalize_product_alias(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "x" * 61, "A\nB", "A\tB", "A\x00B", "A\u200bB", "/cancelar", "https://example.com", "www.example.com", None])
def test_rejects_invalid_alias(raw):
    with pytest.raises(ValueError):
        normalize_product_alias(raw)
