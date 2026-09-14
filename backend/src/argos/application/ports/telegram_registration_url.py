"""Contrato atômico do primeiro avanço do cadastro."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from argos.application.ports.telegram_messages import TelegramMessage


@dataclass(frozen=True)
class RegistrationURLReplies:
    accepted: str
    invalid_url: str
    no_active_draft: str
    unexpected_state: str


class TelegramRegistrationURLRepository(Protocol):
    def receive_for_update(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str, normalized_url: str | None,
        observed_at: datetime, replies: RegistrationURLReplies,
    ) -> TelegramMessage:
        """Verifica lease, proprietário e texto contra a inbox na transação.

        Serializa update e proprietário com início/cancelamento. Reutiliza um
        resultado persistido antes de avaliar o estado atual. Sem resultado,
        verifica rascunho, expiração no relógio do banco e versão sob bloqueio.
        Apenas awaiting_url com URL válida avança para awaiting_alias, gravando
        data['url'] e nova versão, sem renovar expires_at. URL inválida, ausência
        ou outro estado preservam o rascunho. Avanço e resposta são atômicos;
        respostas negativas também são duráveis. Lease perdido aborta tudo.
        Não cria usuário/produto, não coleta página e não envia ao Telegram.
        """
        ...
