"""Composição interna do transporte seguro com o extrator Mercado Livre."""
from collections.abc import Callable

from argos.application.ports.product_collection import CollectedProduct, ProductCollectionError
from argos.domain.safe_fetch import FetchPolicyError
from argos.infrastructure.scrapers.limited_http import FetchedHTML, fetch_html_once
from argos.infrastructure.scrapers.mercado_livre.html_page import ProductPageError, extract_product
from argos.infrastructure.scrapers.mercado_livre.json_ld import StructuredPriceError


class MercadoLivreCollector:
    def __init__(self, *,
                 fetcher: Callable[[str], FetchedHTML] = fetch_html_once,
                 extractor: Callable[[FetchedHTML], CollectedProduct] = extract_product) -> None:
        self._fetcher = fetcher
        self._extractor = extractor

    def collect(self, url: str) -> CollectedProduct:
        """Executa uma tentativa; retries pertencem ao futuro job."""
        try:
            fetched = self._fetcher(url)
            result = self._extractor(fetched)
            if not isinstance(result, CollectedProduct):
                raise TypeError("Extrator retornou resultado inválido.")
            return result
        except (FetchPolicyError, ProductPageError, StructuredPriceError) as error:
            raise ProductCollectionError(error.code) from None
