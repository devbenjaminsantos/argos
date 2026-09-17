"""GET HTML limitado com revalidação completa por redirecionamento."""
import http.client
import socket
import threading
import time
from dataclasses import dataclass, field
from email.message import Message
from urllib.parse import urljoin, urlsplit
from argos.domain.safe_fetch import FetchPolicyError, validate_fetch_url
from argos.infrastructure.scrapers.resolved_destination import resolve_destination
from argos.infrastructure.scrapers.system_dns import SystemDestinationResolver
from argos.infrastructure.scrapers.pinned_tls import PinnedTLSConnection

TOTAL_TIMEOUT_SECONDS = 15

MAX_BODY_BYTES = 2 * 1024 * 1024


def _interrupt(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass


@dataclass(frozen=True)
class FetchedHTML:
    """Conteúdo limitado e destino efetivamente validado, sem exposição no repr."""
    html: bytes = field(repr=False)
    final_url: str = field(repr=False)
    charset: str | None = field(default=None, repr=False)


@dataclass(frozen=True)
class _Redirect:
    url: str


def fetch_html_once(url: str, *, resolver=None) -> FetchedHTML:
    """Uma coleta, sem retries, com até três redirecionamentos."""
    deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
    resolver = resolver or SystemDestinationResolver()
    current = validate_fetch_url(url)
    seen: set[str] = set()
    for hop in range(4):
        if current in seen:
            raise FetchPolicyError("redirect_rejected")
        seen.add(current)
        try:
            result = _fetch_hop(current, resolver=resolver, deadline=deadline)
        except FetchPolicyError:
            raise
        except Exception:
            code = "timeout" if time.monotonic() >= deadline else "transport_failed"
            raise FetchPolicyError(code) from None
        if isinstance(result, FetchedHTML):
            return result
        if hop == 3:
            raise FetchPolicyError("redirect_limit")
        current = result.url
    raise FetchPolicyError("redirect_limit")


def _fetch_hop(url: str, *, resolver, deadline: float) -> FetchedHTML | _Redirect:
    destination = resolve_destination(url, resolver or SystemDestinationResolver(), deadline=deadline)
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise FetchPolicyError("timeout")
    parsed = urlsplit(destination.url)
    with PinnedTLSConnection(destination.url, destination.addresses[0], timeout=min(5, remaining)) as pinned:
        connection = http.client.HTTPConnection(parsed.hostname)
        connection.sock = pinned.socket  # Already connected: HTTP never resolves hostname.
        timer = threading.Timer(max(0, deadline-time.monotonic()), _interrupt, args=(pinned.socket,))
        timer.daemon = True
        timer.start()
        response = None
        try:
            pinned.socket.settimeout(min(5, max(0.001, deadline-time.monotonic())))
            path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
            connection.request("GET", path, headers={"Host": parsed.hostname,
                "Accept": "text/html", "Accept-Encoding": "identity", "Connection": "close"})
            # Parse directly: getresponse() closes its socket for Connection: close,
            # while streaming still needs timeout control on that socket.
            response = http.client.HTTPResponse(pinned.socket)
            response.begin()
            # Refuse ambiguous framing rather than relying on parser precedence.
            headers = response.getheaders()
            lengths = [value.strip() for key, value in headers if key.lower() == "content-length"]
            transfers = [value.strip().lower() for key, value in headers if key.lower() == "transfer-encoding"]
            content_types = [value.strip() for key, value in headers if key.lower() == "content-type"]
            if len(lengths) > 1 or len(transfers) > 1 or (lengths and transfers):
                raise FetchPolicyError("http_failed")
            if transfers and transfers != ["chunked"]:
                raise FetchPolicyError("http_failed")
            declared = None
            if lengths:
                length = lengths[0]
                if not length or not length.isascii() or not length.isdecimal():
                    raise FetchPolicyError("http_failed")
                declared = int(length)
                if declared > MAX_BODY_BYTES:
                    raise FetchPolicyError("body_too_large")
            if response.status in (301, 302, 303, 307, 308):
                location = response.getheader("Location")
                if not location or len(location) > 2048 or any(ord(c) < 32 or ord(c) == 127 for c in location):
                    raise FetchPolicyError("redirect_rejected")
                try:
                    target = validate_fetch_url(urljoin(destination.url, location))
                except ValueError:
                    raise FetchPolicyError("redirect_rejected") from None
                # Never consume a redirect body; cleanup occurs before the next DNS lookup.
                return _Redirect(target)
            if response.status in (403, 429):
                raise FetchPolicyError("access_blocked")
            if response.status != 200:
                raise FetchPolicyError("redirect_rejected" if 300 <= response.status < 400 else "http_failed")
            if len(content_types) != 1:
                raise FetchPolicyError("invalid_content_type")
            content_type = Message()
            content_type["content-type"] = content_types[0]
            if content_type.get_content_type() != "text/html":
                raise FetchPolicyError("invalid_content_type")
            charset = content_type.get_param("charset")
            if response.getheader("Content-Encoding", "identity").strip().lower() not in ("", "identity"):
                raise FetchPolicyError("unsupported_encoding")
            body = bytearray()
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise FetchPolicyError("timeout")
                pinned.socket.settimeout(min(5, remaining))
                chunk = response.read(min(65536, MAX_BODY_BYTES + 1-len(body)))
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > MAX_BODY_BYTES:
                    raise FetchPolicyError("body_too_large")
            if time.monotonic() >= deadline:
                raise FetchPolicyError("timeout")
            if declared is not None and len(body) != declared:
                raise FetchPolicyError("http_failed")
            return FetchedHTML(html=bytes(body), final_url=destination.url, charset=charset)
        except FetchPolicyError:
            raise
        except http.client.IncompleteRead:
            raise FetchPolicyError("timeout" if time.monotonic() >= deadline else "http_failed") from None
        except Exception:
            raise FetchPolicyError("timeout" if time.monotonic() >= deadline else "transport_failed") from None
        finally:
            timer.cancel()
            if response is not None:
                response.close()
            connection.close()
