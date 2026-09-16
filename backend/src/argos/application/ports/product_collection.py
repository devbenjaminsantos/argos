"""Porta de coleta remota independente de HTTP, banco e Telegram."""
from dataclasses import dataclass, field
import re
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class CollectedProduct:
    store: Literal["mercado-livre"]
    external_id: str
    url: str = field(repr=False)
    title: str = field(repr=False)
    price_cents: int
    source: Literal["json-ld", "meta", "visible-dom"]

    def __post_init__(self) -> None:
        if (self.store != "mercado-livre" or not self.external_id
            or not self.url or not self.title
            or not isinstance(self.price_cents, int) or isinstance(self.price_cents, bool)
            or self.price_cents <= 0
            or self.source not in ("json-ld", "meta", "visible-dom")):
            raise ValueError("Produto coletado inválido.")


class ProductCollectionError(Exception):
    """Falha classificada sem URL, HTML ou detalhes de transporte."""
    def __init__(self, code: str) -> None:
        if not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code):
            raise ValueError("Código de coleta inválido.")
        self.code = code
        super().__init__(code)


class ProductCollector(Protocol):
    def collect(self, url: str) -> CollectedProduct: ...
