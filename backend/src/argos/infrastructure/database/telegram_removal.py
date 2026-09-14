"""Início de cadastro e resultado persistidos na mesma transação."""
from argos.application.use_cases.begin_removal import format_removal_selection
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_removal import BeginRemovalReplies
from argos.infrastructure.database.models import (
    TelegramUpdateInbox, TelegramUserRecord, TelegramConversationDraftRecord,
    TelegramRegistrationResult, MonitoredProductRecord,
)


class PostgreSQLTelegramRemovalRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def begin_for_update(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, observed_at: datetime,
        draft_lifetime: timedelta, replies: BeginRemovalReplies,
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
                or message.get("text", "").strip().casefold() != "/remover"):
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
                table = TelegramConversationDraftRecord
                draft = connection.execute(select(table).where(
                    table.telegram_user_id == telegram_user_id
                ).with_for_update()).mappings().one_or_none()
                current = connection.scalar(select(func.clock_timestamp()))
                effective_at = max(current, observed_at, draft["updated_at"] if draft else current)
                reply = replies.already_active
                if draft is None or draft["expires_at"] <= effective_at:
                    product = MonitoredProductRecord
                    products = connection.execute(select(product.id, product.slot,
                        product.alias, product.target_price_cents, product.interval_hours
                    ).where(product.telegram_user_id == telegram_user_id,
                            product.removed_at.is_(None)).order_by(product.slot).limit(3)).all()
                    reply = replies.empty
                    if products:
                        mapping = {str(row.slot): str(row.id) for row in products}
                        values = dict(telegram_user_id=telegram_user_id,
                            state="awaiting_product_to_remove", data={"products_by_slot": mapping},
                            created_at=effective_at, updated_at=effective_at,
                            expires_at=effective_at + draft_lifetime, version=uuid4())
                        connection.execute(insert(table).values(**values).on_conflict_do_update(
                            index_elements=["telegram_user_id"],
                            set_={k: v for k,v in values.items() if k != "telegram_user_id"},
                            where=table.expires_at <= effective_at))
                        reply = format_removal_selection([(row.slot, row.alias,
                            row.target_price_cents, row.interval_hours) for row in products])
            connection.execute(insert(TelegramRegistrationResult).values(
                update_id=update_id, telegram_user_id=telegram_user_id,
                chat_id=chat_id, reply_text=reply, created_at=current,
            ))
            if connection.scalar(select(func.clock_timestamp())) >= inbox["lease_expires_at"]:
                raise RuntimeError("Lease de cadastro expirou durante a transação.")
            return TelegramMessage(chat_id=chat_id, text=reply)
