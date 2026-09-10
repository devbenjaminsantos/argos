"""Composição do worker Telegram executado uma vez por processo."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from argos.application.ports.telegram_messages import TelegramMessageSender
from argos.application.services.telegram_worker import TelegramInboxWorker
from argos.application.use_cases.start import StartTelegramConversation
from argos.config import Settings
from argos.infrastructure.database.config import create_database_engine
from argos.infrastructure.database.telegram_inbox import PostgreSQLTelegramInbox
from argos.infrastructure.database.telegram_users import (
    PostgreSQLTelegramUserRepository,
)
from argos.infrastructure.telegram.bot_api import TelegramBotAPI


def build_worker(
    settings: Settings,
    *,
    engine: Engine,
    sender: TelegramMessageSender | None = None,
) -> TelegramInboxWorker:
    """Compõe adaptadores sem iniciar loops ou chamadas externas."""

    if sender is None:
        if settings.telegram_bot_token is None:
            raise RuntimeError("ARGOS_TELEGRAM_BOT_TOKEN não configurado.")
        sender = TelegramBotAPI(
            settings.telegram_bot_token,
            timeout_seconds=settings.telegram_request_timeout_seconds,
        )

    users = PostgreSQLTelegramUserRepository(engine)
    return TelegramInboxWorker(
        inbox=PostgreSQLTelegramInbox(engine),
        start=StartTelegramConversation(users),
        sender=sender,
        lease_duration=timedelta(
            seconds=settings.telegram_worker_lease_seconds
        ),
        retry_delay=timedelta(
            seconds=settings.telegram_worker_retry_seconds
        ),
    )


def run_once(
    settings: Settings | None = None,
    *,
    sender: TelegramMessageSender | None = None,
    now: datetime | None = None,
) -> bool:
    """Processa no máximo uma entrega e sempre encerra o pool do processo."""

    resolved_settings = settings or Settings()
    engine = create_database_engine(resolved_settings)
    try:
        worker = build_worker(
            resolved_settings,
            engine=engine,
            sender=sender,
        )
        return worker.process_next(now=now or datetime.now(UTC))
    finally:
        engine.dispose()


def main() -> int:
    """Entrypoint pequeno para executores externos e jobs manuais."""

    run_once()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
