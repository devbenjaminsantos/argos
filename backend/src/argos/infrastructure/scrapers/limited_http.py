"""GET HTML limitado com revalidação completa por redirecionamento."""
import http.client
import socket
import threading
import time
from dataclasses import dataclass
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
class _Redirect:
    url: str


def fetch_html_once(url: str, *, resolver=None) -> bytes:
    """Uma coleta, sem retries, com até três redirecionamentos."""
    deadline = time.monotonic() + TOTAL_TIMEOUT_SECONDS
    resolver = resolver or SystemDestinationResolver()
    current = validate_fetch_url(url)
    seen: set[str] = set()
    for hop in range(4):
        if current in seen:
            raise FetchPolicyError("redirect_rejected")
        seen.add(current)
        result = _fetch_hop(current, resolver=resolver, deadline=deadline)
        if isinstance(result, bytes):
            return result
        if hop == 3:
            raise FetchPolicyError("redirect_limit")
        current = result.url
    raise FetchPolicyError("redirect_limit")


def _fetch_hop(url: str, *, resolver, deadline: float) -> bytes | _Redirect:
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
            if response.status != 200:
                raise FetchPolicyError("redirect_rejected" if 300 <= response.status < 400 else "http_failed")
            if response.getheader("Content-Type", "").split(";",1)[0].strip().lower() != "text/html":
                raise FetchPolicyError("invalid_content_type")
            if response.getheader("Content-Encoding", "identity").strip().lower() not in ("", "identity"):
                raise FetchPolicyError("unsupported_encoding")
            length = response.getheader("Content-Length")
            if length is not None:
                try:
                    declared = int(length)
                except ValueError:
                    raise FetchPolicyError("http_failed") from None
                if declared < 0:
                    raise FetchPolicyError("http_failed")
                if declared > MAX_BODY_BYTES:
                    raise FetchPolicyError("body_too_large")
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
            return bytes(body)
        except FetchPolicyError:
            raise
        except Exception:
            raise FetchPolicyError("timeout" if time.monotonic() >= deadline else "transport_failed") from None
        finally:
            timer.cancel()
            if response is not None:
                response.close()
            connection.close()
