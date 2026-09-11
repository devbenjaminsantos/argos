"""Testes do runner assíncrono sem banco ou rede."""

import asyncio
from datetime import UTC, datetime

from argos.infrastructure.telegram.worker_runner import (
    AsyncTelegramWorkerRunner,
)


class _WorkerStub:
    def __init__(self, outcomes: list[bool | Exception]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def process_next(self, *, now: datetime) -> bool:
        self.calls += 1
        outcome = self.outcomes.pop(0) if self.outcomes else False
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


async def _wait_for_calls(worker: _WorkerStub, expected: int) -> None:
    for _attempt in range(100):
        if worker.calls >= expected:
            return
        await asyncio.sleep(0.001)
    raise AssertionError(f"worker recebeu {worker.calls} chamadas; esperado {expected}")


def test_runner_drains_available_updates_and_stops_cleanly() -> None:
    async def scenario() -> None:
        worker = _WorkerStub([True, True, False])
        runner = AsyncTelegramWorkerRunner(
            worker,
            poll_seconds=60,
            error_delay_seconds=60,
            clock=lambda: datetime(2026, 9, 11, tzinfo=UTC),
        )

        await runner.start()
        await _wait_for_calls(worker, 3)
        await runner.stop()

        assert worker.calls == 3

    asyncio.run(scenario())


def test_notify_wakes_idle_runner_without_waiting_for_poll() -> None:
    async def scenario() -> None:
        worker = _WorkerStub([False, False])
        runner = AsyncTelegramWorkerRunner(worker, poll_seconds=60)

        await runner.start()
        await _wait_for_calls(worker, 1)
        runner.notify()
        await _wait_for_calls(worker, 2)
        await runner.stop()

        assert worker.calls == 2

    asyncio.run(scenario())


def test_unexpected_failure_is_delayed_and_runner_survives() -> None:
    async def scenario() -> None:
        worker = _WorkerStub([RuntimeError("sensitive detail"), False])
        runner = AsyncTelegramWorkerRunner(
            worker,
            poll_seconds=60,
            error_delay_seconds=0.001,
        )

        await runner.start()
        await _wait_for_calls(worker, 2)
        await runner.stop()

        assert worker.calls == 2

    asyncio.run(scenario())
