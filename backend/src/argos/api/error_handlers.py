"""Tradução centralizada de exceções para respostas HTTP seguras."""

import logging
from http import HTTPStatus
from types import MappingProxyType
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from argos.api.schemas import ErrorDetail, ErrorResponse
from argos.application.errors import ApplicationError

logger = logging.getLogger(__name__)

_APPLICATION_STATUS = MappingProxyType(
    {
        "invalid_input": HTTPStatus.BAD_REQUEST,
        "not_found": HTTPStatus.NOT_FOUND,
        "conflict": HTTPStatus.CONFLICT,
        "rate_limited": HTTPStatus.TOO_MANY_REQUESTS,
    }
)

_HTTP_ERRORS = MappingProxyType(
    {
        HTTPStatus.NOT_FOUND: ("not_found", "Recurso não encontrado."),
        HTTPStatus.METHOD_NOT_ALLOWED: (
            "method_not_allowed",
            "Método não permitido.",
        ),
        HTTPStatus.REQUEST_ENTITY_TOO_LARGE: (
            "payload_too_large",
            "A requisição excede o tamanho permitido.",
        ),
    }
)


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", uuid4().hex)


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    content = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            correlation_id=_correlation_id(request),
        )
    )
    return JSONResponse(status_code=status_code, content=content.model_dump())


async def handle_application_error(
    request: Request,
    error: ApplicationError,
) -> JSONResponse:
    status = _APPLICATION_STATUS.get(error.code, HTTPStatus.BAD_REQUEST)
    return _error_response(
        request,
        status_code=status,
        code=error.code,
        message=error.public_message,
    )


async def handle_validation_error(
    request: Request,
    _error: RequestValidationError,
) -> JSONResponse:
    return _error_response(
        request,
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        code="validation_error",
        message="Dados da requisição inválidos.",
    )


async def handle_http_error(
    request: Request,
    error: StarletteHTTPException,
) -> JSONResponse:
    code, message = _HTTP_ERRORS.get(
        error.status_code,
        ("http_error", "Não foi possível processar a requisição."),
    )
    return _error_response(
        request,
        status_code=error.status_code,
        code=code,
        message=message,
    )


async def handle_unexpected_error(
    request: Request,
    error: Exception,
) -> JSONResponse:
    correlation_id = _correlation_id(request)
    logger.error(
        "Unhandled error type=%s correlation_id=%s",
        type(error).__name__,
        correlation_id,
    )
    return _error_response(
        request,
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="Ocorreu um erro interno.",
    )


def register_error_handlers(app: FastAPI) -> None:
    """Registra todos os tradutores de erro em um único ponto."""

    app.add_exception_handler(ApplicationError, handle_application_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
