"""Endpoints de saúde da aplicação."""

import logging
from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from argos import __version__
from argos.api.schemas import HealthResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Informa somente se o processo HTTP está vivo."""

    return HealthResponse(version=__version__)


@router.get("/health/ready", response_model=HealthResponse)
def readiness(request: Request) -> HealthResponse:
    """Confirma que o processo consegue consultar o PostgreSQL."""

    engine = request.app.state.database_engine
    if engine is None:
        raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE)

    try:
        with engine.connect() as connection:
            if connection.scalar(text("SELECT 1")) != 1:
                raise RuntimeError("A consulta de prontidão retornou valor inesperado.")
    except (SQLAlchemyError, RuntimeError) as error:
        logger.warning("Database readiness failed type=%s", type(error).__name__)
        raise HTTPException(status_code=HTTPStatus.SERVICE_UNAVAILABLE) from error

    return HealthResponse(version=__version__)
