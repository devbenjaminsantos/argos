"""Persistência atômica do início do cadastro e da resposta por update."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from argos.application.ports.telegram_messages import TelegramMessage


@dataclass(frozen=True, slots=True)
class BeginRemovalReplies:
    empty: str
    already_active: str
    registration_required: str


class TelegramRemovalRepository(Protocol):
    def begin_for_update(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, observed_at: datetime,
        draft_lifetime: timedelta, replies: BeginRemovalReplies,
    ) -> TelegramMessage:
        """Confere lease/payload e reutiliza resposta por update antes do estado.

        Bloqueia inbox, usuário e rascunho. Preserva operação ativa; sem ativos
        não abre rascunho. Caso contrário, grava mapa slot→UUID da lista exibida
        e awaiting_product_to_remove com prazo limitado, junto com a resposta.
        Não altera produtos ou envia mensagens. Replay preserva versão/prazo.
        """
        ...
