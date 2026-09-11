"""Ponto de composição da API do Argos."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from sqlalchemy import Engine

from argos import __version__
from argos.api.error_handlers import register_error_handlers
from argos.api.middleware import add_correlation_id
from argos.api.routes.health import router as health_router
from argos.api.routes.telegram import router as telegram_router
from argos.application.ports.telegram_inbox import TelegramInbox
from argos.application.ports.telegram_worker import TelegramWorkerRunner
from argos.config import Settings, get_settings
from argos.infrastructure.database.config import create_database_engine
from argos.infrastructure.database.telegram_inbox import PostgreSQLTelegramInbox
from argos.infrastructure.telegram.worker_runner import AsyncTelegramWorkerRunner
from argos.infrastructure.telegram.webhook_configurator import TelegramWebhookConfigurator
from argos.telegram_worker import build_worker

logger = logging.getLogger(__name__)


def create_app(
    settings: Settings | None = None,
    *,
    telegram_inbox: TelegramInbox | None = None,
    telegram_worker_runner: TelegramWorkerRunner | None = None,
) -> FastAPI:
    """Cria uma instância isolada da aplicação para runtime e testes."""

    resolved_settings = settings or get_settings()
    database_engine: Engine | None = None
    if resolved_settings.database_url is not None:
        database_engine = create_database_engine(resolved_settings)
        if telegram_inbox is None:
            telegram_inbox = PostgreSQLTelegramInbox(database_engine)
        if (
            telegram_worker_runner is None
            and resolved_settings.telegram_bot_token is not None
        ):
            telegram_worker_runner = AsyncTelegramWorkerRunner(
                build_worker(resolved_settings, engine=database_engine),
                poll_seconds=resolved_settings.telegram_worker_poll_seconds,
            )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if resolved_settings.telegram_webhook_url is not None:
            if (
                resolved_settings.telegram_bot_token is None
                or resolved_settings.telegram_webhook_secret is None
                or resolved_settings.telegram_expected_username is None
            ):
                raise RuntimeError("Configuração Telegram incompleta.")
            identity = await asyncio.to_thread(
                TelegramWebhookConfigurator(
                    resolved_settings.telegram_bot_token,
                    timeout_seconds=resolved_settings.telegram_request_timeout_seconds,
                ).configure,
                expected_username=resolved_settings.telegram_expected_username,
                webhook_url=str(resolved_settings.telegram_webhook_url),
                webhook_secret=resolved_settings.telegram_webhook_secret,
            )
            logger.info("Telegram webhook configurado para @%s.", identity.username)
        if telegram_worker_runner is not None:
            await telegram_worker_runner.start()
        try:
            yield
        finally:
            if telegram_worker_runner is not None:
                await telegram_worker_runner.stop()
            if database_engine is not None:
                database_engine.dispose()

    app = FastAPI(
        title="Argos API",
        version=__version__,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = resolved_settings
    app.state.database_engine = database_engine
    app.state.telegram_inbox = telegram_inbox
    app.state.telegram_worker_runner = telegram_worker_runner
    app.middleware("http")(add_correlation_id)
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(telegram_router)
    return app


app = create_app()
