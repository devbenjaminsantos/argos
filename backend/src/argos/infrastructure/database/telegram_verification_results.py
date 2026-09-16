"""Checkpoint PostgreSQL da resposta de verificação Telegram."""

from uuid import UUID

from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.telegram_messages import TelegramMessage
from argos.infrastructure.database.models import (
    TelegramRegistrationResult,
    TelegramUpdateInbox,
)


class PostgreSQLTelegramVerificationResults:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find_for_claim(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, text: str,
    ) -> TelegramMessage | None:
        _validate_arguments(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
        )
        with self._engine.begin() as connection:
            _lock_valid_claim(
                connection, update_id=update_id, lease_token=lease_token,
                telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
            )
            result = connection.execute(
                select(TelegramRegistrationResult).where(
                    TelegramRegistrationResult.update_id == update_id
                )
            ).mappings().one_or_none()
            if result is None:
                return None
            return _same_result(
                result, telegram_user_id=telegram_user_id, chat_id=chat_id,
            )

    def save_for_claim(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, text: str,
        reply: TelegramMessage,
    ) -> TelegramMessage:
        _validate_arguments(
            update_id=update_id, lease_token=lease_token,
            telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
        )
        if (not isinstance(reply, TelegramMessage) or reply.chat_id != chat_id
            or not isinstance(reply.text, str)
            or not 1 <= len(reply.text) <= 4096):
            raise ValueError("Resposta de verificação inválida.")
        with self._engine.begin() as connection:
            current = _lock_valid_claim(
                connection, update_id=update_id, lease_token=lease_token,
                telegram_user_id=telegram_user_id, chat_id=chat_id, text=text,
            )
            statement = (
                insert(TelegramRegistrationResult)
                .values(
                    update_id=update_id, telegram_user_id=telegram_user_id,
                    chat_id=chat_id, reply_text=reply.text, created_at=current,
                )
                .on_conflict_do_nothing(
                    index_elements=[TelegramRegistrationResult.update_id]
                )
            )
            connection.execute(statement)
            result = connection.execute(
                select(TelegramRegistrationResult).where(
                    TelegramRegistrationResult.update_id == update_id
                )
            ).mappings().one()
            saved = _same_result(
                result, telegram_user_id=telegram_user_id, chat_id=chat_id,
            )
            if saved.text != reply.text:
                raise RuntimeError("Resposta de verificação divergente.")
            return saved


def _validate_arguments(
    *, update_id: int, lease_token: UUID,
    telegram_user_id: int, chat_id: int, text: str,
) -> None:
    if (any(not isinstance(value, int) or isinstance(value, bool)
            for value in (update_id, telegram_user_id, chat_id))
        or update_id < 0 or telegram_user_id <= 0 or chat_id <= 0
        or not isinstance(lease_token, UUID)
        or not isinstance(text, str) or not text.strip()):
        raise ValueError("Claim de verificação inválido.")


def _lock_valid_claim(
    connection, *, update_id: int, lease_token: UUID,
    telegram_user_id: int, chat_id: int, text: str,
):
    inbox = connection.execute(
        select(TelegramUpdateInbox)
        .where(TelegramUpdateInbox.update_id == update_id)
        .with_for_update()
    ).mappings().one_or_none()
    current = connection.scalar(select(func.clock_timestamp()))
    message = {} if inbox is None else inbox["payload"].get("message", {})
    if (inbox is None or inbox["status"] != "processing"
        or inbox["lease_token"] != lease_token
        or inbox["lease_expires_at"] <= current
        or message.get("from", {}).get("id") != telegram_user_id
        or message.get("chat", {}).get("id") != chat_id
        or message.get("chat", {}).get("type") != "private"
        or message.get("text") != text):
        raise RuntimeError("Claim ou payload de verificação divergente.")
    return current


def _same_result(result, *, telegram_user_id: int, chat_id: int) -> TelegramMessage:
    if (result["telegram_user_id"] != telegram_user_id
        or result["chat_id"] != chat_id):
        raise RuntimeError("Resultado de verificação divergente.")
    return TelegramMessage(chat_id=chat_id, text=result["reply_text"])
