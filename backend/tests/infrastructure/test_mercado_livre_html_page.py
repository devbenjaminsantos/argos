from pathlib import Path
import json

import pytest

from argos.infrastructure.scrapers.limited_http import FetchedHTML
from argos.infrastructure.scrapers.mercado_livre.html_page import (
    ProductPageError, extract_json_ld_from_page, extract_page_basics, extract_product,
    parse_product_page,
)

FIXTURES = Path(__file__).parents[1] / "fixtures/mercado_livre"
URL = "https://www.mercadolivre.com.br/notebook/p/MLB123456"


def fetched(name: str, *, charset: str | None = "UTF-8") -> FetchedHTML:
    return FetchedHTML((FIXTURES / name).read_bytes(), URL, charset)


def test_reads_json_ld_inertly_from_utf8_fixture():
    page = parse_product_page(fetched("json_ld_priority.html"))
    assert page.title == "Notebook de teste"
    assert len(page.json_ld_scripts) == 1
    assert extract_json_ld_from_page(fetched("json_ld_priority.html")) == 349_990


def test_blocking_precedes_a_price_present_in_page():
    with pytest.raises(ProductPageError, match="access_blocked"):
        extract_json_ld_from_page(fetched("access_blocked.html"))


def test_decodes_entities_before_block_detection():
    html = b"<html><body>verifique se voc&ecirc; &eacute; humano</body></html>"
    with pytest.raises(ProductPageError, match="access_blocked"):
        parse_product_page(FetchedHTML(html, URL, None))


@pytest.mark.parametrize("charset", ["iso-8859-1", "us-ascii", "utf-16", ""])
def test_rejects_unsupported_declared_charset(charset):
    with pytest.raises(ProductPageError, match="unsupported_charset"):
        parse_product_page(fetched("json_ld_priority.html", charset=charset))


def test_rejects_bytes_incompatible_with_utf8():
    value = FetchedHTML(b"<html><body>caf\xe9</body></html>", URL, "utf-8")
    with pytest.raises(ProductPageError, match="invalid_charset"):
        parse_product_page(value)


def test_script_text_does_not_trigger_blocking_or_execute_markup():
    html = b'''<html><head><script type="application/ld+json">
      {"@type":"Product","offers":{"price":"10.00"},
       "description":"verifique se voc\\u00ea \\u00e9 humano <img onerror=alert(1)>"}
    </script></head><body>Produto normal</body></html>'''
    assert extract_json_ld_from_page(FetchedHTML(html, URL, None)) == 1_000


def test_body_scan_is_limited_but_detects_phrase_at_boundary():
    phrase = "verifique se você é humano"
    html = ("<html><body>" + "x" * (2_000 - len(phrase)) + phrase
            + "ignored" * 10_000 + "</body></html>").encode()
    with pytest.raises(ProductPageError, match="access_blocked"):
        parse_product_page(FetchedHTML(html, URL, "utf8"))


def test_repr_does_not_expose_untrusted_content():
    page = parse_product_page(FetchedHTML(b"<title>secret</title>", URL, None))
    assert repr(page) == "ParsedProductPage()"


def test_json_ld_has_priority_over_meta_price():
    result = extract_page_basics(fetched("json_ld_priority.html"))
    assert result == type(result)("Notebook de teste", 349_990, "json-ld")
    assert repr(result) == "ExtractedPageBasics()"


def test_malformed_json_falls_back_to_ordered_meta_price():
    result = extract_page_basics(fetched("malformed_json_meta.html"))
    assert result == type(result)("Caneca de teste", 15_000, "meta")


def test_h1_title_is_plain_text_and_has_priority():
    result = extract_page_basics(fetched("visible_price.html"))
    assert result.title == "Notebook"
    assert result.price_cents == 219_990
    assert result.source == "visible-dom"


def test_document_title_and_default_are_fallbacks():
    assert extract_page_basics(fetched("missing_price.html")).title == "Produto sem preço"
    empty = FetchedHTML(b"<html><body></body></html>", URL, None)
    assert extract_page_basics(empty).title == "Produto do Mercado Livre"


def test_title_is_normalized_and_limited():
    value = ("  Produto   " + "x" * 200).encode()
    result = extract_page_basics(FetchedHTML(b"<h1 class='ui-pdp-title'>" + value + b"</h1>", URL))
    assert result.title.startswith("Produto x")
    assert len(result.title) == 180


def test_first_meta_per_selector_and_selector_order_are_stable():
    html = b'''<meta itemprop="price" content="invalid">
      <meta itemprop="price" content="1.00">
      <meta property="product:price:amount" content="2.00">
      <meta property="og:price:amount" content="3.00">'''
    result = extract_page_basics(FetchedHTML(html, URL))
    assert result.price_cents == 200
    assert result.source == "meta"


def test_visible_price_fixture_closes_extractor_result():
    result = extract_product(fetched("visible_price.html"))
    assert result.store == "mercado-livre"
    assert result.external_id == "MLB123456"
    assert result.url == URL
    assert result.title == "Notebook"
    assert result.price_cents == 219_990
    assert result.source == "visible-dom"
    assert repr(result) == ("CollectedProduct(store='mercado-livre', "
                            "external_id='MLB123456', price_cents=219990, "
                            "source='visible-dom')")


def test_visible_price_outside_main_containers_is_ignored():
    html = b'''<span class="andes-money-amount">
      <span class="andes-money-amount__fraction">99</span>
    </span>'''
    with pytest.raises(ProductPageError, match="price_not_found"):
        extract_product(FetchedHTML(html, URL))


@pytest.mark.parametrize("fraction,cents", [
    ("0", "00"), ("9999999999", "00"), ("abc", "10"), ("10", "abc"),
])
def test_invalid_visible_price_never_becomes_zero(fraction, cents):
    html = f'''<div class="ui-pdp-price__main-container">
      <span class="andes-money-amount">
        <span class="andes-money-amount__fraction">{fraction}</span>
        <span class="andes-money-amount__cents">{cents}</span>
      </span></div>'''.encode()
    with pytest.raises(ProductPageError, match="price_not_found"):
        extract_product(FetchedHTML(html, URL))


def test_first_valid_visible_main_price_is_used():
    html = b'''<div class="ui-pdp-price__second-line">
      <span class="andes-money-amount"><span class="andes-money-amount__fraction">x</span></span>
      <span class="andes-money-amount"><span class="andes-money-amount__fraction">1.234</span>
      <span class="andes-money-amount__cents">5</span></span></div>'''
    result = extract_product(FetchedHTML(html, URL))
    assert result.price_cents == 123_450


def test_unavailable_and_missing_price_are_distinct():
    with pytest.raises(ProductPageError, match="product_unavailable"):
        extract_product(fetched("unavailable.html"))
    with pytest.raises(ProductPageError, match="price_not_found"):
        extract_product(fetched("missing_price.html"))


def test_final_url_is_the_only_identity_source():
    html = b'''<meta property="og:url" content="https://evil.example/MLB-999">
      <meta itemprop="price" content="10.00">'''
    result = extract_product(FetchedHTML(html, "https://produto.mercadolivre.com.br/MLB-456-item"))
    assert result.external_id == "MLB456"
    assert result.url == "https://produto.mercadolivre.com.br/MLB-456-item"


def test_invalid_final_url_fails_explicitly():
    html = b'<meta itemprop="price" content="10.00">'
    with pytest.raises(ProductPageError, match="invalid_url"):
        extract_product(FetchedHTML(html, "https://evil.example/MLB-456"))


@pytest.mark.parametrize("case", json.loads((FIXTURES / "manifest.json").read_text()))
def test_all_prepared_fixture_expectations(case):
    value = FetchedHTML((FIXTURES / case["file"]).read_bytes(), case["final_url"], "utf-8")
    expected = case["expected"]
    if "error" in expected:
        with pytest.raises(ProductPageError, match=expected["error"]):
            extract_product(value)
        return
    result = extract_product(value)
    assert result.title == expected["title"]
    assert result.price_cents == expected["price_cents"]
    assert result.source == expected["source"]
