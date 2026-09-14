"""Consulta e snapshot da resposta na mesma transação."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.use_cases.list_products import format_products
from argos.infrastructure.database.models import (
    TelegramUpdateInbox, TelegramUserRecord, MonitoredProductRecord,
    TelegramRegistrationResult,
)


class PostgreSQLTelegramProductsRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def list_for_update(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, observed_at: datetime,
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
                raise RuntimeError("Lease de consulta perdido.")
            message = inbox["payload"].get("message", {})
            if (message.get("from", {}).get("id") != telegram_user_id
                or message.get("chat", {}).get("id") != chat_id
                or message.get("chat", {}).get("type") != "private"
                or message.get("text", "").strip().casefold() != "/produtos"):
                raise RuntimeError("Identidade ou comando de consulta divergente.")
            result = connection.execute(select(TelegramRegistrationResult).where(
                TelegramRegistrationResult.update_id == update_id
            )).mappings().one_or_none()
            if result is not None:
                if result["telegram_user_id"] != telegram_user_id or result["chat_id"] != chat_id:
                    raise RuntimeError("Resultado de consulta divergente.")
                return TelegramMessage(chat_id=result["chat_id"], text=result["reply_text"])
            user = connection.scalar(select(TelegramUserRecord.telegram_user_id).where(
                TelegramUserRecord.telegram_user_id == telegram_user_id
            ).with_for_update())
            reply = "Envie /start para registrar seu acesso antes de consultar produtos."
            if user is not None:
                product = MonitoredProductRecord
                rows = connection.execute(select(product.slot, product.alias,
                    product.target_price_cents, product.interval_hours).where(
                    product.telegram_user_id == telegram_user_id, product.removed_at.is_(None)
                ).order_by(product.slot).limit(3)).all()
                reply = format_products([tuple(row) for row in rows])
            connection.execute(insert(TelegramRegistrationResult).values(
                update_id=update_id, telegram_user_id=telegram_user_id,
                chat_id=chat_id, reply_text=reply, created_at=current,
            ))
            if connection.scalar(select(func.clock_timestamp())) >= inbox["lease_expires_at"]:
                raise RuntimeError("Lease de consulta expirou durante a transação.")
            return TelegramMessage(chat_id=chat_id, text=reply)
