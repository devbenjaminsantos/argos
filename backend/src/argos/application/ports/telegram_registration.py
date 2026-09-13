"""Persistência atômica do início do cadastro e da resposta por update."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol
from uuid import UUID

from argos.application.ports.telegram_messages import TelegramMessage


@dataclass(frozen=True, slots=True)
class BeginRegistrationReplies:
    started: str
    already_active: str
    registration_required: str


class TelegramRegistrationRepository(Protocol):
    def begin_for_update(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, observed_at: datetime,
        draft_lifetime: timedelta, replies: BeginRegistrationReplies,
    ) -> TelegramMessage:
        """Valida lease vigente e identidade contra o payload persistido.

        Sob uma única transação, serializa o update e o proprietário, cria
        awaiting_url apenas para usuário registrado sem rascunho ativo (ou
        substitui expirado) e persiste a resposta, inclusive nos outros casos.
        Reprocessar um update retorna a resposta original, sem recriar o
        rascunho, renovar sua expiração ou modificar outra operação.
        Lease perdido ou identidade divergente recusam qualquer mutação;
        exceções revertem resposta e rascunho juntos. Não envia pela Bot API.
        """
        ...
