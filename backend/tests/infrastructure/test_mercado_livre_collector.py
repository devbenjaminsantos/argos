from pathlib import Path

import pytest

from argos.application.ports.product_collection import (
    CollectedProduct, ProductCollectionError, ProductCollector,
)
from argos.domain.safe_fetch import FetchPolicyError
from argos.infrastructure.scrapers.limited_http import FetchedHTML
from argos.infrastructure.scrapers.mercado_livre.collector import MercadoLivreCollector
from argos.infrastructure.scrapers.mercado_livre.html_page import ProductPageError, extract_product

URL = "https://www.mercadolivre.com.br/notebook/p/MLB123456"
FIXTURE = Path(__file__).parents[1] / "fixtures/mercado_livre/json_ld_priority.html"


def test_composes_one_fetch_with_extraction_and_satisfies_port():
    calls = []
    fetched = FetchedHTML(FIXTURE.read_bytes(), URL, "utf-8")
    def fetcher(url):
        calls.append(url)
        return fetched
    collector: ProductCollector = MercadoLivreCollector(fetcher=fetcher)
    result = collector.collect(URL)
    assert calls == [URL]
    assert result == CollectedProduct("mercado-livre", "MLB123456", URL,
                                      "Notebook de teste", 349_990, "json-ld")


@pytest.mark.parametrize("failure", [
    FetchPolicyError("forbidden_address"),
    ProductPageError("access_blocked"),
])
def test_classifies_expected_failures_without_retry_or_details(failure):
    calls = []
    def fetcher(url):
        calls.append(url)
        raise failure
    with pytest.raises(ProductCollectionError) as raised:
        MercadoLivreCollector(fetcher=fetcher).collect(URL)
    assert raised.value.code == failure.code
    assert str(raised.value) == failure.code
    assert calls == [URL]


def test_extractor_is_injectable_and_receives_bounded_result():
    fetched = FetchedHTML(b"<html></html>", URL, "utf-8")
    expected = CollectedProduct("mercado-livre", "MLB123456", URL, "Teste", 100, "meta")
    seen = []
    def extractor(value):
        seen.append(value)
        return expected
    result = MercadoLivreCollector(fetcher=lambda _: fetched, extractor=extractor).collect(URL)
    assert result is expected
    assert seen == [fetched]


@pytest.mark.parametrize("changes", [
    {"store": "other"}, {"external_id": ""}, {"url": ""}, {"title": ""},
    {"price_cents": 0}, {"price_cents": True}, {"source": "other"},
])
def test_collected_product_rejects_invalid_results(changes):
    values = dict(store="mercado-livre", external_id="MLB123", url=URL,
                  title="Teste", price_cents=100, source="meta") | changes
    with pytest.raises(ValueError, match="Produto coletado inválido"):
        CollectedProduct(**values)


@pytest.mark.parametrize("code", ["", "Invalid", "bad-code", "https://secret", "x" * 65])
def test_collection_error_rejects_detail_in_code(code):
    with pytest.raises(ValueError, match="Código de coleta inválido"):
        ProductCollectionError(code)


def test_invalid_injected_extractor_result_is_a_programming_error():
    fetched = FetchedHTML(b"", URL)
    collector = MercadoLivreCollector(fetcher=lambda _: fetched, extractor=lambda _: None)
    with pytest.raises(TypeError, match="resultado inválido"):
        collector.collect(URL)
