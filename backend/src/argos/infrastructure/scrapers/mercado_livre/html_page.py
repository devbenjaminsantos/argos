"""Leitura inerte do HTML já limitado pelo transporte."""
from dataclasses import dataclass, field
from html.parser import HTMLParser
import re

from argos.application.ports.product_collection import CollectedProduct
from argos.domain.products.registration import mercado_livre_product_key
from argos.infrastructure.scrapers.limited_http import FetchedHTML
from argos.infrastructure.scrapers.mercado_livre.json_ld import extract_json_ld_price, to_price_cents

_UTF8_ALIASES = frozenset({None, "utf-8", "utf8"})
_VOID_ELEMENTS = frozenset({"area", "base", "br", "col", "embed", "hr", "img",
                            "input", "link", "meta", "param", "source", "track", "wbr"})


class ProductPageError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ParsedProductPage:
    title: str = field(repr=False)
    json_ld_scripts: tuple[str, ...] = field(repr=False)
    meta_prices: tuple[str | None, ...] = field(repr=False)
    visible_prices: tuple[tuple[str, str | None], ...] = field(repr=False)
    unavailable: bool = field(repr=False)


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
        self.visible_prices: list[tuple[str, str | None]] = []
        self._elements: list[tuple[str, bool, bool, str | None]] = []
        self._price_scope_depth = 0
        self._money_parts: dict[str, list[str]] | None = None
        self._fraction_depth = 0
        self._cents_depth = 0
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
        classes = frozenset(values.get("class", "").split())
        starts_scope = bool(classes & {
            "ui-pdp-price__second-line", "ui-pdp-price__main-container",
        })
        if starts_scope:
            self._price_scope_depth += 1
        starts_money = self._price_scope_depth > 0 and "andes-money-amount" in classes
        if starts_money and self._money_parts is None:
            self._money_parts = {"fraction": [], "cents": []}
        starts_fraction = self._money_parts is not None and "andes-money-amount__fraction" in classes
        starts_cents = self._money_parts is not None and "andes-money-amount__cents" in classes
        self._fraction_depth += int(starts_fraction)
        self._cents_depth += int(starts_cents)
        if tag not in _VOID_ELEMENTS:
            part = "fraction" if starts_fraction else "cents" if starts_cents else None
            self._elements.append((tag, starts_scope, starts_money, part))
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
        frames = []
        while self._elements:
            frame = self._elements.pop()
            frames.append(frame)
            if frame[0] == tag:
                break
        for _, starts_scope, starts_money, part in frames:
            if part == "fraction":
                self._fraction_depth = max(0, self._fraction_depth - 1)
            elif part == "cents":
                self._cents_depth = max(0, self._cents_depth - 1)
            if starts_money and self._money_parts is not None:
                fraction = "".join(self._money_parts["fraction"])
                cents = "".join(self._money_parts["cents"]) or None
                self.visible_prices.append((fraction, cents))
                self._money_parts = None
                self._fraction_depth = self._cents_depth = 0
            if starts_scope:
                self._price_scope_depth = max(0, self._price_scope_depth - 1)
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
            if self._money_parts is not None:
                if self._fraction_depth:
                    self._money_parts["fraction"].append(data)
                elif self._cents_depth:
                    self._money_parts["cents"].append(data)
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
    unavailable = "produto indisponível" in visible or "anúncio finalizado" in visible
    return ParsedProductPage(title=title, json_ld_scripts=tuple(parser.scripts),
        meta_prices=prices, visible_prices=tuple(parser.visible_prices), unavailable=unavailable)


def _visible_price_cents(fraction: str, cents: str | None) -> int | None:
    integer_digits = re.sub(r"\D", "", fraction)
    if not integer_digits or len(integer_digits) > 10:
        return None
    cents_digits = re.sub(r"\D", "", cents or "")
    if cents is not None and not cents_digits:
        return None
    cents_digits = (cents_digits + "00")[:2]
    value = int(integer_digits) * 100 + int(cents_digits)
    return value if 0 < value <= 999_999_999 else None


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
    for fraction, cents in page.visible_prices:
        price = _visible_price_cents(fraction, cents)
        if price is not None:
            return ExtractedPageBasics(page.title, price, "visible-dom")
    return ExtractedPageBasics(page.title, None, None)


def extract_product(fetched: FetchedHTML) -> CollectedProduct:
    basics = extract_page_basics(fetched)
    if basics.price_cents is None or basics.source is None:
        page = parse_product_page(fetched)
        raise ProductPageError("product_unavailable" if page.unavailable else "price_not_found")
    try:
        external_id = mercado_livre_product_key(fetched.final_url)
    except ValueError:
        raise ProductPageError("invalid_url") from None
    return CollectedProduct(store="mercado-livre", external_id=external_id,
        url=fetched.final_url, title=basics.title,
        price_cents=basics.price_cents, source=basics.source)
