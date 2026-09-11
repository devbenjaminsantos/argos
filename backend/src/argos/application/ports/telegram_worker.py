"""Contrato de ciclo de vida do consumidor Telegram."""

from typing import Protocol


class TelegramWorkerRunner(Protocol):
    """Runner despertável composto pela entrada HTTP."""

    async def start(self) -> None: ...

    async def stop(self) -> None: ...

    def notify(self) -> None: ...
