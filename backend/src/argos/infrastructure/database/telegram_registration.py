"""Início de cadastro e resultado persistidos na mesma transação."""
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration import BeginRegistrationReplies
from argos.infrastructure.database.models import (
    TelegramUpdateInbox, TelegramUserRecord, TelegramConversationDraftRecord,
    TelegramRegistrationResult,
)


class PostgreSQLTelegramRegistrationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def begin_for_update(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, observed_at: datetime,
        draft_lifetime: timedelta, replies: BeginRegistrationReplies,
    ) -> TelegramMessage:
        if observed_at.utcoffset() is None or not timedelta(0) < draft_lifetime <= timedelta(days=1):
            raise ValueError("Horário ou duração inválidos.")
        with self._engine.begin() as connection:
            inbox = connection.execute(select(TelegramUpdateInbox).where(
                TelegramUpdateInbox.update_id == update_id
            ).with_for_update()).mappings().one_or_none()
            current = connection.scalar(select(func.clock_timestamp()))
            if (inbox is None or inbox["status"] != "processing"
                or inbox["lease_token"] != lease_token
                or inbox["lease_expires_at"] <= current):
                raise RuntimeError("Lease de cadastro perdido.")
            message = inbox["payload"].get("message", {})
            if (message.get("from", {}).get("id") != telegram_user_id
                or message.get("chat", {}).get("id") != chat_id
                or message.get("chat", {}).get("type") != "private"
                or message.get("text", "").strip().casefold() != "/adicionar"):
                raise RuntimeError("Identidade ou comando de cadastro divergente.")
            result = connection.execute(select(TelegramRegistrationResult).where(
                TelegramRegistrationResult.update_id == update_id
            )).mappings().one_or_none()
            if result is not None:
                if result["telegram_user_id"] != telegram_user_id or result["chat_id"] != chat_id:
                    raise RuntimeError("Resultado de cadastro divergente.")
                return TelegramMessage(chat_id=result["chat_id"], text=result["reply_text"])
            user = connection.scalar(select(TelegramUserRecord.telegram_user_id).where(
                TelegramUserRecord.telegram_user_id == telegram_user_id
            ).with_for_update())
            reply = replies.registration_required
            if user is not None:
                effective_at = max(current, observed_at)
                draft = TelegramConversationDraftRecord
                created = connection.scalar(insert(draft).values(
                    telegram_user_id=telegram_user_id, state="awaiting_url", data={},
                    created_at=effective_at, updated_at=effective_at,
                    expires_at=effective_at + draft_lifetime, version=uuid4(),
                ).on_conflict_do_update(index_elements=["telegram_user_id"],
                    set_={"state": "awaiting_url", "data": {}, "created_at": effective_at,
                          "updated_at": effective_at, "expires_at": effective_at + draft_lifetime,
                          "version": uuid4()}, where=draft.expires_at <= effective_at,
                ).returning(draft.telegram_user_id))
                reply = replies.started if created is not None else replies.already_active
            connection.execute(insert(TelegramRegistrationResult).values(
                update_id=update_id, telegram_user_id=telegram_user_id,
                chat_id=chat_id, reply_text=reply, created_at=current,
            ))
            if connection.scalar(select(func.clock_timestamp())) >= inbox["lease_expires_at"]:
                raise RuntimeError("Lease de cadastro expirou durante a transação.")
            return TelegramMessage(chat_id=chat_id, text=reply)
