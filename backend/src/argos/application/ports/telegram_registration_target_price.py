"""Contrato transacional do preço-alvo, ainda sem adaptador."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from argos.application.ports.telegram_messages import TelegramMessage


@dataclass(frozen=True)
class RegistrationTargetPriceReplies:
    accepted: str
    invalid_target_price: str
    no_active_draft: str
    unexpected_state: str


class TelegramRegistrationTargetPriceRepository(Protocol):
    def receive_for_update(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str, target_price_cents: int | None,
        observed_at: datetime, replies: RegistrationTargetPriceReplies,
    ) -> TelegramMessage:
        """Confere lease, identidade, texto e normalização contra a inbox.

        Bloqueia update, proprietário e rascunho na ordem dos passos anteriores.
        Reutiliza resultado durável antes de avaliar o estado atual. Somente
        awaiting_target_price ativo com preço-alvo válido avança para awaiting_interval;
        preserva URL, apelido e demais dados, grava data['target_price_cents'] como inteiro e nova versão,
        sem renovar expires_at. Usa relógio do banco e versão sob bloqueio.
        Respostas negativas preservam o rascunho e também são persistidas.
        Avanço e resposta são atômicos; perda de lease aborta tudo. Não cria
        produto, não envia mensagem externa e não realiza coleta.
        """
        ...
