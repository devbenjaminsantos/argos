"""Middleware HTTP compartilhado pelas rotas."""

from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response


async def add_correlation_id(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Gera um identificador interno, sem confiar em cabeçalhos do cliente."""

    correlation_id = uuid4().hex
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
