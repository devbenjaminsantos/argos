"""Validação sintática de anúncio, sem DNS ou acesso à rede."""

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_PRODUCT_PATH = re.compile(r"^/(?:MLB-\d+(?:-[^/]*)?|(?:[^/]+/)?p/MLB\d+)/?$", re.IGNORECASE)
_HOST = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*mercadolivre\.com\.br$")
_TRACKING = {
    "matt_tool", "matt_word", "matt_source", "matt_campaign", "matt_ad_group",
    "matt_match_type", "matt_network", "matt_device", "matt_creative",
    "matt_keyword", "gclid", "fbclid",
}


def normalize_mercado_livre_product_url(raw_url: str) -> str:
    """Rejeita URLs ambíguas; preserva parâmetros funcionais do anúncio."""
    value = raw_url.strip()
    if not value or len(value) > 2048 or any(ord(c) <= 32 or ord(c) == 127 for c in value) or "\\" in value:
        raise ValueError("URL de produto inválida.")
    try:
        url = urlsplit(value)
        hostname = (url.hostname or "").lower()
        if (
            url.scheme != "https" or not _HOST.fullmatch(hostname)
            or url.username is not None or url.password is not None
            or url.port not in (None, 443)
            or url.netloc.endswith(":")
            or not _PRODUCT_PATH.fullmatch(url.path)
        ):
            raise ValueError("URL de produto inválida.")
        query = urlencode([
            (key, val) for key, val in parse_qsl(url.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in _TRACKING
        ])
        return urlunsplit(("https", hostname, url.path, query, ""))
    except ValueError:
        raise ValueError("URL de produto inválida.") from None
