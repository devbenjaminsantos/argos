"""Contrato atômico de confirmação; implementação ainda pendente."""
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID
from argos.application.ports.telegram_messages import TelegramMessage


@dataclass(frozen=True)
class RegistrationConfirmationReplies:
    created: str
    corrected: str
    duplicate: str
    limit_reached: str
    invalid_data: str
    invalid_action: str
    no_active_draft: str
    unexpected_state: str


class TelegramRegistrationConfirmationRepository(Protocol):
    def confirm_for_update(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str, observed_at: datetime,
        replies: RegistrationConfirmationReplies,
    ) -> TelegramMessage:
        """Confere lease/payload e consulta resultado por update antes do estado.

        Bloqueia update, usuário e rascunho nessa ordem. Exige confirmação ativa
        e revalida dados completos na transação. confirmar verifica unicidade
        por chave Mercado Livre e reserva slot 1..3 sob bloqueio do proprietário;
        cria produto, remove rascunho e grava resposta juntos. Duplicata e limite
        preservam rascunho e têm resposta durável. corrigir limpa os dados,
        reinicia awaiting_url com nova versão e mantém expiração original.
        Replay nunca cria produto ou rascunho novamente. Lease perdido aborta
        tudo. Não realiza coleta nem envio externo; produto usa proprietário,
        nunca chat_id, como autorização.
        """
        ...
