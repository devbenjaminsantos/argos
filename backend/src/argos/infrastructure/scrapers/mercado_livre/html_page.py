"""Leitura inerte do HTML já limitado pelo transporte."""
from dataclasses import dataclass, field
from html.parser import HTMLParser

from argos.infrastructure.scrapers.limited_http import FetchedHTML
from argos.infrastructure.scrapers.mercado_livre.json_ld import extract_json_ld_price, to_price_cents

_UTF8_ALIASES = frozenset({None, "utf-8", "utf8"})


class ProductPageError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ParsedProductPage:
    title: str = field(repr=False)
    json_ld_scripts: tuple[str, ...] = field(repr=False)
    meta_prices: tuple[str | None, ...] = field(repr=False)


@dataclass(frozen=True)
class ExtractedPageBasics:
    title: str = field(repr=False)
    price_cents: int | None = field(repr=False)
    source: str | None = field(repr=False)


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.body_parts: list[str] = []
        self.scripts: list[str] = []
        self.meta: dict[str, str] = {}
        self._body_length = 0
        self._title_depth = 0
        self._h1_depth = 0
        self._body_depth = 0
        self._ignored_depth = 0
        self._json_script = False
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.casefold()
        values = {key.casefold(): (value or "") for key, value in attrs}
        if tag == "title":
            self._title_depth += 1
        elif tag == "h1" and "ui-pdp-title" in values.get("class", "").split():
            self._h1_depth += 1
        elif tag == "meta":
            key = (values.get("itemprop") or values.get("property") or "").casefold()
            if key and key not in self.meta:
                self.meta[key] = values.get("content", "")
        elif tag == "body":
            self._body_depth += 1
        elif tag in ("script", "style"):
            self._ignored_depth += 1
            if tag == "script" and values.get("type", "").strip().casefold() == "application/ld+json":
                self._json_script = True
                self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        elif tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
        elif tag == "body" and self._body_depth:
            self._body_depth -= 1
        elif tag in ("script", "style") and self._ignored_depth:
            if tag == "script" and self._json_script:
                self.scripts.append("".join(self._script_parts))
                self._json_script = False
                self._script_parts = []
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._json_script:
            self._script_parts.append(data)
        elif not self._ignored_depth:
            if self._title_depth:
                self.title_parts.append(data)
            if self._h1_depth:
                self.h1_parts.append(data)
            if self._body_depth and self._body_length < 2_000:
                remaining = 2_000 - self._body_length
                value = data[:remaining]
                self.body_parts.append(value)
                self._body_length += len(value)


def parse_product_page(fetched: FetchedHTML) -> ParsedProductPage:
    charset = fetched.charset.casefold() if isinstance(fetched.charset, str) else fetched.charset
    if charset not in _UTF8_ALIASES:
        raise ProductPageError("unsupported_charset")
    try:
        source = fetched.html.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError:
        raise ProductPageError("invalid_charset") from None
    parser = _PageParser()
    try:
        parser.feed(source)
        parser.close()
    except (ValueError, RecursionError):
        raise ProductPageError("invalid_html") from None
    document_title = " ".join("".join(parser.title_parts).split())
    visible = " ".join("".join(parser.body_parts).split()).casefold()[:2_000]
    if ("captcha" in document_title.casefold()
        or "não conseguimos confirmar que você é humano" in visible
        or "verifique se você é humano" in visible):
        raise ProductPageError("access_blocked")
    h1 = " ".join("".join(parser.h1_parts).split())
    og_title = " ".join(parser.meta.get("og:title", "").split())
    title = (h1 or og_title or document_title or "Produto do Mercado Livre")[:180]
    prices = tuple(parser.meta.get(key) for key in (
        "price", "product:price:amount", "og:price:amount",
    ))
    return ParsedProductPage(title=title, json_ld_scripts=tuple(parser.scripts), meta_prices=prices)


def extract_json_ld_from_page(fetched: FetchedHTML) -> int | None:
    """Bloqueio é classificado antes de qualquer preço estruturado."""
    page = parse_product_page(fetched)
    return extract_json_ld_price(list(page.json_ld_scripts))


def extract_page_basics(fetched: FetchedHTML) -> ExtractedPageBasics:
    """JSON-LD tem prioridade; metadados são fallback ordenado."""
    page = parse_product_page(fetched)
    price = extract_json_ld_price(list(page.json_ld_scripts))
    if price is not None:
        return ExtractedPageBasics(page.title, price, "json-ld")
    for value in page.meta_prices:
        price = to_price_cents(value)
        if price is not None:
            return ExtractedPageBasics(page.title, price, "meta")
    return ExtractedPageBasics(page.title, None, None)
