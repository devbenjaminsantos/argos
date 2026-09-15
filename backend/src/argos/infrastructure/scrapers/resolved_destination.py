"""Orquestra resolução validada; resolvedor real ainda não composto."""
import time
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit
from argos.domain.safe_fetch import FetchPolicyError, validate_fetch_url, validate_resolved_addresses


class DestinationResolver(Protocol):
    def resolve(self, hostname: str, *, timeout: float) -> list[str]:
        """Retorna o conjunto completo de A/AAAA dentro do timeout.

        Implementação deve interromper I/O ao expirar; não retornar resposta
        truncada. Nenhuma segunda resolução é permitida na conexão.
        """
        ...


@dataclass(frozen=True, slots=True)
class ResolvedDestination:
    url: str
    addresses: tuple[str, ...]
    deadline: float


def resolve_destination(url: str, resolver: DestinationResolver, *, deadline: float) -> ResolvedDestination:
    normalized = validate_fetch_url(url)
    started = time.monotonic()
    remaining = deadline - started
    if remaining <= 0:
        raise FetchPolicyError("timeout")
    hostname = urlsplit(normalized).hostname
    try:
        addresses = resolver.resolve(hostname, timeout=min(3.0, remaining))
    except TimeoutError:
        raise FetchPolicyError("timeout") from None
    except Exception:
        raise FetchPolicyError("dns_failed") from None
    if time.monotonic() >= min(deadline, started + 3.0):
        raise FetchPolicyError("timeout")
    approved = validate_resolved_addresses(addresses)
    return ResolvedDestination(normalized, approved, deadline)
