"""Processamento recuperável de uma entrega da inbox Telegram."""

from datetime import datetime, timedelta
from typing import cast

from argos.application.errors import ApplicationError
from argos.application.ports.telegram_inbox import TelegramInbox
from argos.application.ports.telegram_messages import (
    TelegramDeliveryError,
    TelegramMessageSender,
)
from argos.application.use_cases.begin_registration import BeginTelegramRegistration
from argos.application.use_cases.cancel import CancelTelegramConversation
from argos.application.use_cases.help import HelpTelegramConversation
from argos.application.use_cases.list_products import ListTelegramProducts
from argos.application.use_cases.receive_registration_text import ReceiveTelegramRegistrationText
from argos.application.use_cases.start import StartTelegramConversation


class TelegramInboxWorker:
    """Executa no máximo um update sem manter transação durante o envio."""

    def __init__(
        self,
        *,
        inbox: TelegramInbox,
        start: StartTelegramConversation,
        help_conversation: HelpTelegramConversation,
        cancel_conversation: CancelTelegramConversation,
        begin_registration: BeginTelegramRegistration,
        receive_registration_text: ReceiveTelegramRegistrationText,
        list_products: ListTelegramProducts,
        sender: TelegramMessageSender,
        lease_duration: timedelta = timedelta(seconds=30),
        retry_delay: timedelta = timedelta(seconds=30),
    ) -> None:
        if lease_duration <= timedelta(0) or retry_delay <= timedelta(0):
            raise ValueError("Durações do worker devem ser positivas.")
        self._inbox = inbox
        self._start = start
        self._help = help_conversation
        self._cancel = cancel_conversation
        self._registration = begin_registration
        self._registration_url = receive_registration_text
        self._products = list_products
        self._sender = sender
        self._lease_duration = lease_duration
        self._retry_delay = retry_delay

    def process_next(self, *, now: datetime) -> bool:
        if now.utcoffset() is None:
            raise ValueError("now deve possuir fuso horário.")

        claimed = self._inbox.claim_next(
            now=now,
            lease_duration=self._lease_duration,
        )
        if claimed is None:
            return False

        try:
            telegram_user_id, chat_id, text = _extract_message(claimed.payload)
            command = text.strip().casefold()
            if command == "/ajuda":
                reply = self._help.execute(chat_id=chat_id, text=text)
            elif command == "/produtos":
                reply = self._products.execute(
                    update_id=claimed.update_id, lease_token=claimed.lease_token,
                    telegram_user_id=telegram_user_id, chat_id=chat_id,
                    text=text, observed_at=now,
                )
            elif command == "/cancelar":
                reply = self._cancel.execute(
                    update_id=claimed.update_id, lease_token=claimed.lease_token,
                    observed_at=now,
                    telegram_user_id=telegram_user_id,
                    chat_id=chat_id,
                    text=text,
                )
            elif command == "/adicionar":
                reply = self._registration.execute(
                    update_id=claimed.update_id,
                    lease_token=claimed.lease_token,
                    telegram_user_id=telegram_user_id,
                    chat_id=chat_id,
                    text=text,
                    observed_at=now,
                )
            elif not command.startswith("/"):
                reply = self._registration_url.execute(
                    update_id=claimed.update_id, lease_token=claimed.lease_token,
                    telegram_user_id=telegram_user_id, chat_id=chat_id,
                    text=text, observed_at=now,
                )
            else:
                reply = self._start.execute(
                    telegram_user_id=telegram_user_id,
                    chat_id=chat_id,
                    text=text,
                    observed_at=now,
                )
        except (ApplicationError, ValueError, TypeError, KeyError):
            transitioned = self._inbox.dead_letter(
                update_id=claimed.update_id,
                lease_token=claimed.lease_token,
                error_code="invalid_or_unsupported_update",
            )
            _require_transition(transitioned)
            return True

        try:
            self._sender.send(reply)
        except TelegramDeliveryError as error:
            if error.retryable and not error.outcome_unknown:
                transitioned = self._inbox.retry(
                    update_id=claimed.update_id,
                    lease_token=claimed.lease_token,
                    next_attempt_at=now
                    + (error.retry_after or self._retry_delay),
                    error_code=error.code,
                )
            else:
                transitioned = self._inbox.dead_letter(
                    update_id=claimed.update_id,
                    lease_token=claimed.lease_token,
                    error_code=error.code,
                )
            _require_transition(transitioned)
            return True

        completed = self._inbox.complete(
            update_id=claimed.update_id,
            lease_token=claimed.lease_token,
            completed_at=now,
        )
        _require_transition(completed)
        return True


def _extract_message(payload: dict[str, object]) -> tuple[int, int, str]:
    message = cast(dict[str, object], payload["message"])
    sender = cast(dict[str, object], message["from"])
    chat = cast(dict[str, object], message["chat"])

    telegram_user_id = sender["id"]
    chat_id = chat["id"]
    text = message["text"]
    if (
        not isinstance(telegram_user_id, int)
        or isinstance(telegram_user_id, bool)
        or not isinstance(chat_id, int)
        or isinstance(chat_id, bool)
        or not isinstance(text, str)
    ):
        raise TypeError("Payload Telegram persistido inválido.")
    return telegram_user_id, chat_id, text


def _require_transition(transitioned: bool) -> None:
    if not transitioned:
        raise RuntimeError("Lease da inbox perdido durante processamento.")
