"""Contrato transacional do apelido, com adaptador PostgreSQL."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from argos.application.ports.telegram_messages import TelegramMessage


@dataclass(frozen=True)
class RegistrationAliasReplies:
    accepted: str
    invalid_alias: str
    no_active_draft: str
    unexpected_state: str


class TelegramRegistrationAliasRepository(Protocol):
    def receive_for_update(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str, normalized_alias: str | None,
        observed_at: datetime, replies: RegistrationAliasReplies,
    ) -> TelegramMessage:
        """Confere lease, identidade, texto e normalização contra a inbox.

        Bloqueia update, proprietário e rascunho na ordem dos passos anteriores.
        Reutiliza resultado durável antes de avaliar o estado atual. Somente
        awaiting_alias ativo com apelido válido avança para awaiting_target_price;
        preserva data['url'] e demais dados, grava data['alias'] e nova versão,
        sem renovar expires_at. Usa relógio do banco e versão sob bloqueio.
        Respostas negativas preservam o rascunho e também são persistidas.
        Avanço e resposta são atômicos; perda de lease aborta tudo. Não cria
        produto, não envia mensagem externa e não realiza coleta.
        """
        ...
