"""Cancelamento e resposta persistidos na mesma transação."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Engine, delete, update, func, select
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.use_cases.select_removal_product import format_removal_proposal
from argos.infrastructure.database.models import (
    TelegramUpdateInbox, TelegramUserRecord, TelegramConversationDraftRecord,
    TelegramRegistrationResult, MonitoredProductRecord,
)


class PostgreSQLTelegramRemovalSelectionRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def select_for_update(
        self, *, update_id: int, lease_token: UUID,
        telegram_user_id: int, chat_id: int, observed_at: datetime, text: str,
    ) -> TelegramMessage:
        if observed_at.utcoffset() is None:
            raise ValueError("Horário inválido.")
        with self._engine.begin() as connection:
            return self.select_in_transaction(connection=connection,
                update_id=update_id, lease_token=lease_token, telegram_user_id=telegram_user_id,
                chat_id=chat_id, text=text, observed_at=observed_at)

    def select_in_transaction(self, *, connection, update_id: int, lease_token: UUID,
                               telegram_user_id: int, chat_id: int, text: str,
                               observed_at: datetime) -> TelegramMessage:
        inbox = connection.execute(select(TelegramUpdateInbox).where(
            TelegramUpdateInbox.update_id == update_id
        ).with_for_update()).mappings().one_or_none()
        current = connection.scalar(select(func.clock_timestamp()))
        if (inbox is None or inbox["status"] != "processing"
            or inbox["lease_token"] != lease_token
            or inbox["lease_expires_at"] <= current):
            raise RuntimeError("Lease de seleção de remoção perdido.")
        message = inbox["payload"].get("message", {})
        if (message.get("from", {}).get("id") != telegram_user_id
            or message.get("chat", {}).get("id") != chat_id
            or message.get("chat", {}).get("type") != "private"
            or message.get("text") != text):
            raise RuntimeError("Identidade ou comando de seleção de remoção divergente.")
        result = connection.execute(select(TelegramRegistrationResult).where(
            TelegramRegistrationResult.update_id == update_id
        )).mappings().one_or_none()
        if result is not None:
            if result["telegram_user_id"] != telegram_user_id or result["chat_id"] != chat_id:
                raise RuntimeError("Resultado de seleção de remoção divergente.")
            return TelegramMessage(chat_id=result["chat_id"], text=result["reply_text"])
        user = connection.scalar(select(TelegramUserRecord.telegram_user_id).where(
            TelegramUserRecord.telegram_user_id == telegram_user_id
        ).with_for_update())
        table = TelegramConversationDraftRecord
        draft = connection.execute(select(table).where(
            table.telegram_user_id == telegram_user_id
        ).with_for_update()).mappings().one_or_none()
        current = connection.scalar(select(func.clock_timestamp()))
        effective = max(current, observed_at, draft["updated_at"] if draft else current)
        reply = "Não há remoção ativa. Use /remover para iniciar."
        if user is not None and draft is not None and draft["expires_at"] > effective:
            reply = "Continue a etapa atual ou use /cancelar."
            if draft["state"] == "awaiting_product_to_remove":
                raw = text.strip()
                reply = "Envie um número da lista entre 1 e 3 ou use /cancelar."
                if raw in ("1", "2", "3") and raw in draft["data"].get("products_by_slot", {}):
                    mapping = draft["data"].get("products_by_slot", {})
                    try:
                        product_id = UUID(mapping[raw])
                    except (KeyError, ValueError, TypeError, AttributeError):
                        product_id = None
                    product = MonitoredProductRecord
                    row = None if product_id is None else connection.execute(select(product).where(
                        product.id == product_id, product.telegram_user_id == telegram_user_id,
                        product.removed_at.is_(None), product.slot == int(raw)
                    ).with_for_update()).mappings().one_or_none()
                    if row is None:
                        connection.execute(delete(table).where(table.telegram_user_id == telegram_user_id,
                            table.version == draft["version"]))
                        reply = "Produto indisponível. Use /remover para consultar uma nova lista."
                    else:
                        version = uuid4()
                        connection.execute(update(table).where(table.telegram_user_id == telegram_user_id,
                            table.version == draft["version"]).values(
                            state="awaiting_removal_confirmation",
                            data={"product_id": str(row["id"]), "slot": row["slot"]},
                            updated_at=effective, version=version))
                        reply = format_removal_proposal(row["slot"], row["alias"],
                            row["target_price_cents"], row["interval_hours"], version)
        connection.execute(insert(TelegramRegistrationResult).values(
            update_id=update_id, telegram_user_id=telegram_user_id,
            chat_id=chat_id, reply_text=reply, created_at=current,
        ))
        if connection.scalar(select(func.clock_timestamp())) >= inbox["lease_expires_at"]:
            raise RuntimeError("Lease de seleção de remoção expirou durante a transação.")
        return TelegramMessage(chat_id=chat_id, text=reply)
