"""Ponto de composição da API do Argos."""

from fastapi import FastAPI

from argos import __version__
from argos.api.error_handlers import register_error_handlers
from argos.api.middleware import add_correlation_id
from argos.api.routes.health import router as health_router
from argos.api.routes.telegram import router as telegram_router
from argos.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Cria uma instância isolada da aplicação para runtime e testes."""

    resolved_settings = settings or get_settings()
    app = FastAPI(
        title="Argos API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = resolved_settings
    app.middleware("http")(add_correlation_id)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(telegram_router)
    return app


app = create_app()
