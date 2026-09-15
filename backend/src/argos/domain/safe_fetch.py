"""Política pura de destinos; não resolve DNS nem abre conexões."""
import ipaddress
from urllib.parse import urlsplit
from argos.domain.mercado_livre_url import normalize_mercado_livre_product_url

ALLOWED_FETCH_HOSTS = frozenset({"mercadolivre.com.br", "www.mercadolivre.com.br", "produto.mercadolivre.com.br"})
MAX_DNS_ADDRESSES = 16
# Faixas especiais recusadas explicitamente, inclusive as classificações
# que podem variar entre versões do módulo ipaddress.
_DENIED = tuple(ipaddress.ip_network(value) for value in (
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
    "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
    "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
    "224.0.0.0/4", "240.0.0.0/4", "::/128", "::1/128", "64:ff9b::/96",
    "64:ff9b:1::/48", "100::/64", "2001::/23", "2001:db8::/32",
    "2002::/16", "fc00::/7", "fe80::/10", "ff00::/8",
))


class FetchPolicyError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def validate_fetch_url(raw: str) -> str:
    if not isinstance(raw, str):
        raise FetchPolicyError("invalid_url")
    try:
        normalized = normalize_mercado_livre_product_url(raw)
    except ValueError:
        raise FetchPolicyError("invalid_url") from None
    if urlsplit(normalized).hostname not in ALLOWED_FETCH_HOSTS:
        raise FetchPolicyError("host_not_allowed")
    return normalized


def validate_resolved_addresses(addresses: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Valida o conjunto inteiro antes de fornecer candidatos ao transporte."""
    if not isinstance(addresses, (list, tuple)) or not 1 <= len(addresses) <= MAX_DNS_ADDRESSES:
        raise FetchPolicyError("dns_failed")
    approved = []
    for raw in addresses:
        if not isinstance(raw, str) or "%" in raw:
            raise FetchPolicyError("forbidden_address")
        try:
            address = ipaddress.ip_address(raw)
        except ValueError:
            raise FetchPolicyError("forbidden_address") from None
        candidate = address.ipv4_mapped if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped else address
        if (not candidate.is_global or candidate.is_multicast
            or any(candidate.version == network.version and candidate in network for network in _DENIED)):
            raise FetchPolicyError("forbidden_address")
        # Canonicalize mapped IPv4 to avoid ambiguous transport interpretation.
        approved.append(str(candidate))
    return tuple(dict.fromkeys(approved))
