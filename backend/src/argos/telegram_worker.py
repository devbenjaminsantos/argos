"""Composição do worker Telegram executado uma vez por processo."""

from argos.application.use_cases.begin_removal import BeginTelegramRemoval
from argos.infrastructure.database.telegram_removal import PostgreSQLTelegramRemovalRepository
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine

from argos.application.ports.product_collection import ProductCollector
from argos.application.ports.telegram_messages import TelegramMessageSender
from argos.application.services.telegram_worker import TelegramInboxWorker
from argos.application.use_cases.begin_registration import BeginTelegramRegistration
from argos.application.use_cases.cancel import CancelTelegramConversation
from argos.application.use_cases.help import HelpTelegramConversation
from argos.application.use_cases.list_products import ListTelegramProducts
from argos.infrastructure.database.telegram_products import PostgreSQLTelegramProductsRepository
from argos.application.use_cases.receive_registration_text import ReceiveTelegramRegistrationText
from argos.application.use_cases.start import StartTelegramConversation
from argos.application.use_cases.verify_product import VerifyProduct
from argos.application.use_cases.verify_telegram_product import VerifyTelegramProduct
from argos.config import Settings
from argos.infrastructure.database.config import create_database_engine
from argos.infrastructure.database.telegram_inbox import PostgreSQLTelegramInbox
from argos.infrastructure.database.telegram_cancellation import PostgreSQLTelegramCancellationRepository
from argos.infrastructure.database.telegram_registration import (
    PostgreSQLTelegramRegistrationRepository,
)
from argos.infrastructure.database.telegram_registration_text import PostgreSQLTelegramRegistrationTextRepository
from argos.infrastructure.database.telegram_users import (
    PostgreSQLTelegramUserRepository,
)
from argos.infrastructure.database.price_observations import (
    PostgreSQLPriceObservationRepository,
)
from argos.infrastructure.database.product_verification import (
    PostgreSQLProductVerificationTargets,
)
from argos.infrastructure.database.telegram_verification_results import (
    PostgreSQLTelegramVerificationResults,
)
from argos.infrastructure.scrapers.mercado_livre.collector import MercadoLivreCollector
from argos.infrastructure.telegram.bot_api import TelegramBotAPI


def build_worker(
    settings: Settings,
    *,
    engine: Engine,
    sender: TelegramMessageSender | None = None,
    collector: ProductCollector | None = None,
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
    observations = PostgreSQLPriceObservationRepository(engine)
    resolved_collector = collector or MercadoLivreCollector()
    return TelegramInboxWorker(
        inbox=PostgreSQLTelegramInbox(engine),
        start=StartTelegramConversation(users),
        help_conversation=HelpTelegramConversation(),
        cancel_conversation=CancelTelegramConversation(PostgreSQLTelegramCancellationRepository(engine)),
        begin_registration=BeginTelegramRegistration(
            PostgreSQLTelegramRegistrationRepository(engine)
        ),
        receive_registration_text=ReceiveTelegramRegistrationText(
            PostgreSQLTelegramRegistrationTextRepository(engine)
        ),
        begin_removal=BeginTelegramRemoval(PostgreSQLTelegramRemovalRepository(engine)),
        list_products=ListTelegramProducts(PostgreSQLTelegramProductsRepository(engine)),
        verify_product=VerifyTelegramProduct(
            verifier=VerifyProduct(
                PostgreSQLProductVerificationTargets(engine),
                resolved_collector, observations,
            ),
            observations=observations,
            results=PostgreSQLTelegramVerificationResults(engine),
        ),
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
