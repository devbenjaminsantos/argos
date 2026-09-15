"""Conexão TCP/TLS direta ao endereço aprovado, sem resolução implícita."""
import time
import ipaddress
import socket
import ssl
from urllib.parse import urlsplit
from argos.domain.safe_fetch import validate_fetch_url, validate_resolved_addresses


class PinnedTLSConnection:
    """Recurso TLS; ainda não executa HTTP ou lê conteúdo remoto."""
    def __init__(self, url: str, address: str, *, timeout: float = 5.0):
        self.url = validate_fetch_url(url)
        self.hostname = urlsplit(self.url).hostname
        self.address = validate_resolved_addresses([address])[0]
        if isinstance(timeout, bool) or not 0 < timeout <= 5:
            raise ValueError("Timeout inválido.")
        self.timeout = timeout
        self.socket = None

    def connect(self):
        if self.socket is not None:
            raise RuntimeError("Conexão já aberta.")
        address = ipaddress.ip_address(self.address)
        family = socket.AF_INET if address.version == 4 else socket.AF_INET6
        deadline = time.monotonic() + self.timeout
        raw = socket.socket(family, socket.SOCK_STREAM)
        try:
            raw.settimeout(self.timeout)
            raw.connect((self.address, 443))
            context = ssl.create_default_context()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError()
            raw.settimeout(remaining)
            # Default context validates the certificate and original hostname.
            tls = context.wrap_socket(raw, server_hostname=self.hostname)
            self.socket = tls
            return tls
        except Exception:
            raw.close()
            raise RuntimeError("transport_failed") from None

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()
