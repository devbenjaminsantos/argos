"""Endpoints de saúde da aplicação."""

from fastapi import APIRouter

from argos import __version__
from argos.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Informa somente se o processo HTTP está vivo."""

    return HealthResponse(version=__version__)
