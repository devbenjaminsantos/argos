"""Ponto de composição da API do Argos."""

from fastapi import FastAPI

from argos import __version__
from argos.api.error_handlers import register_error_handlers
from argos.api.middleware import add_correlation_id
from argos.api.routes.health import router as health_router


def create_app() -> FastAPI:
    """Cria uma instância isolada da aplicação para runtime e testes."""

    app = FastAPI(
        title="Argos API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.middleware("http")(add_correlation_id)
    register_error_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
