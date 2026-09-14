"""Cancelamento e resposta persistidos na mesma transação."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Engine, delete, func, select
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_cancellation import CancellationReplies
from argos.infrastructure.database.models import (
    TelegramUpdateInbox, TelegramUserRecord, TelegramConversationDraftRecord,
    TelegramRegistrationResult,
)


class PostgreSQLTelegramCancellationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def cancel_for_update(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, observed_at: datetime, replies: CancellationReplies,
    ) -> TelegramMessage:
        if observed_at.utcoffset() is None:
            raise ValueError("Horário inválido.")
        with self._engine.begin() as connection:
            inbox = connection.execute(select(TelegramUpdateInbox).where(
                TelegramUpdateInbox.update_id == update_id
            ).with_for_update()).mappings().one_or_none()
            current = connection.scalar(select(func.clock_timestamp()))
            if (inbox is None or inbox["status"] != "processing"
                or inbox["lease_token"] != lease_token
                or inbox["lease_expires_at"] <= current):
                raise RuntimeError("Lease de cancelamento perdido.")
            message = inbox["payload"].get("message", {})
            if (message.get("from", {}).get("id") != telegram_user_id
                or message.get("chat", {}).get("id") != chat_id
                or message.get("chat", {}).get("type") != "private"
                or message.get("text", "").strip().casefold() != "/cancelar"):
                raise RuntimeError("Identidade ou comando de cancelamento divergente.")
            result = connection.execute(select(TelegramRegistrationResult).where(
                TelegramRegistrationResult.update_id == update_id
            )).mappings().one_or_none()
            if result is not None:
                if result["telegram_user_id"] != telegram_user_id or result["chat_id"] != chat_id:
                    raise RuntimeError("Resultado de cancelamento divergente.")
                return TelegramMessage(chat_id=result["chat_id"], text=result["reply_text"])
            user = connection.scalar(select(TelegramUserRecord.telegram_user_id).where(
                TelegramUserRecord.telegram_user_id == telegram_user_id
            ).with_for_update())
            reply = replies.nothing_to_cancel
            if user is not None:
                draft = connection.execute(select(TelegramConversationDraftRecord).where(
                    TelegramConversationDraftRecord.telegram_user_id == telegram_user_id
                ).with_for_update()).mappings().one_or_none()
                if draft is not None:
                    removed = connection.scalar(delete(TelegramConversationDraftRecord).where(
                        TelegramConversationDraftRecord.telegram_user_id == telegram_user_id,
                        TelegramConversationDraftRecord.version == draft["version"],
                    ).returning(TelegramConversationDraftRecord.telegram_user_id))
                    if removed is None:
                        raise RuntimeError("Versão do rascunho perdida.")
                    reply = replies.cancelled
            connection.execute(insert(TelegramRegistrationResult).values(
                update_id=update_id, telegram_user_id=telegram_user_id,
                chat_id=chat_id, reply_text=reply, created_at=current,
            ))
            if connection.scalar(select(func.clock_timestamp())) >= inbox["lease_expires_at"]:
                raise RuntimeError("Lease de cancelamento expirou durante a transação.")
            return TelegramMessage(chat_id=chat_id, text=reply)
