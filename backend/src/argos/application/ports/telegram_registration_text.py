"""Contrato atômico do primeiro avanço do cadastro."""

from argos.application.ports.telegram_registration_interval import RegistrationIntervalReplies
from argos.application.ports.telegram_registration_target_price import RegistrationTargetPriceReplies
from argos.application.ports.telegram_registration_alias import RegistrationAliasReplies
from datetime import datetime
from typing import Protocol
from uuid import UUID

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_url import RegistrationURLReplies


class TelegramRegistrationTextRepository(Protocol):
    def receive_for_update(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str,
        observed_at: datetime, url_replies: RegistrationURLReplies, alias_replies: RegistrationAliasReplies,
        price_replies: RegistrationTargetPriceReplies,
        interval_replies: RegistrationIntervalReplies,
    ) -> TelegramMessage:
        """Reutiliza resultado por update antes de escolher o passo sob bloqueio.

        Confere lease e payload e serializa proprietário e rascunho. awaiting_url
        recebe URL; awaiting_alias recebe apelido. Avanço e resposta são atômicos,
        com nova versão, preservação dos demais dados e expiração original.
        Respostas negativas são duráveis. Não executa efeitos externos.
        """
        ...
