"""DNS do sistema em subprocesso encerrado ao expirar o prazo."""
import json
import math
import subprocess
import sys
from argos.domain.safe_fetch import ALLOWED_FETCH_HOSTS

_SCRIPT = """import json,socket,sys
records=socket.getaddrinfo(sys.argv[1],443,socket.AF_UNSPEC,socket.SOCK_STREAM)
print(json.dumps([record[4][0] for record in records]))
"""


class SystemDestinationResolver:
    """Isola getaddrinfo bloqueante; run mata e aguarda filho no timeout."""
    def resolve(self, hostname: str, *, timeout: float) -> list[str]:
        if hostname not in ALLOWED_FETCH_HOSTS:
            raise ValueError("host_not_allowed")
        if isinstance(timeout, bool) or not math.isfinite(timeout) or not 0 < timeout <= 3:
            raise ValueError("invalid_timeout")
        try:
            result = subprocess.run([sys.executable, "-I", "-c", _SCRIPT, hostname],
                capture_output=True, text=True, timeout=timeout, check=True)
            addresses = json.loads(result.stdout)
            if not isinstance(addresses, list) or not all(isinstance(a, str) for a in addresses):
                raise ValueError()
            return addresses
        except subprocess.TimeoutExpired:
            raise TimeoutError("dns_timeout") from None
        except Exception:
            raise RuntimeError("dns_failed") from None
