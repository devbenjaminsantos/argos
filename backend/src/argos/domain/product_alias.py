"""Normalização do apelido escolhido pelo proprietário."""

import unicodedata


def normalize_product_alias(raw: str) -> str:
    if not isinstance(raw, str) or any(unicodedata.category(c).startswith("C") for c in raw):
        raise ValueError("Apelido inválido.")
    alias = " ".join(unicodedata.normalize("NFC", raw).split())
    if not 1 <= len(alias) <= 60 or alias.startswith("/") or "://" in alias or alias.lower().startswith("www."):
        raise ValueError("Apelido inválido.")
    return alias
