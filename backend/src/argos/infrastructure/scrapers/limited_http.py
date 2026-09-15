"""Um GET HTML limitado; redirects ainda recusados."""
import http.client
import socket
import threading
import time
from urllib.parse import urlsplit
from argos.domain.safe_fetch import FetchPolicyError
from argos.infrastructure.scrapers.resolved_destination import resolve_destination
from argos.infrastructure.scrapers.system_dns import SystemDestinationResolver
from argos.infrastructure.scrapers.pinned_tls import PinnedTLSConnection

MAX_BODY_BYTES = 2 * 1024 * 1024


def _interrupt(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass


def fetch_html_once(url: str, *, resolver=None) -> bytes:
    deadline = time.monotonic() + 15
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
