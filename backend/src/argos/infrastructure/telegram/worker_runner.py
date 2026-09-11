"""Runner assíncrono do worker síncrono e recuperável."""

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime

from argos.application.services.telegram_worker import TelegramInboxWorker

logger = logging.getLogger(__name__)


class AsyncTelegramWorkerRunner:
    """Drena a inbox sem bloquear o event loop da API."""

    def __init__(
        self,
        worker: TelegramInboxWorker,
        *,
        poll_seconds: float = 10.0,
        error_delay_seconds: float = 5.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if poll_seconds <= 0 or error_delay_seconds <= 0:
            raise ValueError("Intervalos do runner devem ser positivos.")
        self._worker = worker
        self._poll_seconds = poll_seconds
        self._error_delay_seconds = error_delay_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self._wake = asyncio.Event()
        self._stopping = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopping = False
        self._task = asyncio.create_task(
            self._run(),
            name="argos-telegram-worker",
        )

    async def stop(self) -> None:
        task = self._task
        if task is None:
            return
        self._stopping = True
        self._wake.set()
        await task
        self._task = None

    def notify(self) -> None:
        self._wake.set()

    async def _run(self) -> None:
        while not self._stopping:
            self._wake.clear()
            try:
                processed = await asyncio.to_thread(
                    self._worker.process_next,
                    now=self._clock(),
                )
            except Exception as error:
                logger.error(
                    "Telegram worker failed error_type=%s",
                    type(error).__name__,
                )
                await self._wait(self._error_delay_seconds)
                continue

            if processed:
                continue
            await self._wait(self._poll_seconds)

    async def _wait(self, timeout: float) -> None:
        if self._stopping or self._wake.is_set():
            return
        try:
            await asyncio.wait_for(self._wake.wait(), timeout=timeout)
        except TimeoutError:
            pass
