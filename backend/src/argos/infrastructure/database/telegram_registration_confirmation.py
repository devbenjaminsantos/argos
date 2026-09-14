"""Confirmação e correção e resposta durável sob o lease da inbox."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Engine, delete, func, insert, select, update

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_confirmation import RegistrationConfirmationReplies
from argos.domain.products.registration import validate_product_registration, parse_registration_confirmation, mercado_livre_product_key
from argos.infrastructure.database.models import (
    TelegramConversationDraftRecord, TelegramRegistrationResult,
    TelegramUpdateInbox, TelegramUserRecord, MonitoredProductRecord,
)


class PostgreSQLTelegramRegistrationConfirmationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def confirm_for_update(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str,
        observed_at: datetime, replies: RegistrationConfirmationReplies,
    ) -> TelegramMessage:
        if observed_at.utcoffset() is None:
            raise ValueError("Horário deve possuir fuso.")
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
                or message.get("text") != text or not isinstance(text, str)
                or not text.strip() or text.strip().startswith("/")):
                raise RuntimeError("Identidade ou texto de cadastro divergente.")
            result = connection.execute(select(TelegramRegistrationResult).where(
                TelegramRegistrationResult.update_id == update_id
            )).mappings().one_or_none()
            if result is not None:
                if result["telegram_user_id"] != telegram_user_id or result["chat_id"] != chat_id:
                    raise RuntimeError("Resultado de cadastro divergente.")
                return TelegramMessage(chat_id=chat_id, text=result["reply_text"])
            user = connection.scalar(select(TelegramUserRecord.telegram_user_id).where(
                TelegramUserRecord.telegram_user_id == telegram_user_id
            ).with_for_update())
            table = TelegramConversationDraftRecord
            draft = connection.execute(select(table).where(
                table.telegram_user_id == telegram_user_id
            ).with_for_update()).mappings().one_or_none()
            current = connection.scalar(select(func.clock_timestamp()))
            effective_at = max(current, observed_at, draft["updated_at"] if draft else current)
            reply = replies.no_active_draft
            if user is not None and draft is not None and draft["expires_at"] > effective_at:
                if draft["state"] != "awaiting_confirmation":
                    reply = replies.unexpected_state
                else:
                    try:
                        action = parse_registration_confirmation(text)
                    except ValueError:
                        action = None
                    if action is None:
                        reply = replies.invalid_action
                    elif action == "corrigir":
                        connection.execute(update(table).where(
                            table.telegram_user_id == telegram_user_id,
                            table.version == draft["version"],
                        ).values(state="awaiting_url", data={}, updated_at=effective_at, version=uuid4()))
                        reply = replies.corrected
                    else:
                        try:
                            proposal = validate_product_registration(draft["data"])
                            key = mercado_livre_product_key(proposal.url)
                        except ValueError:
                            proposal = None
                        reply = replies.invalid_data
                        if proposal is not None:
                            products = connection.execute(select(
                                MonitoredProductRecord.slot, MonitoredProductRecord.product_key,
                            ).where(MonitoredProductRecord.telegram_user_id == telegram_user_id)).all()
                            if any(product.product_key == key for product in products):
                                reply = replies.duplicate
                            else:
                                used = {product.slot for product in products}
                                slot = next((slot for slot in (1,2,3) if slot not in used), None)
                                reply = replies.limit_reached
                                if slot is not None:
                                    connection.execute(insert(MonitoredProductRecord).values(
                                        id=uuid4(), telegram_user_id=telegram_user_id, slot=slot,
                                        product_key=key, url=proposal.url, alias=proposal.alias,
                                        target_price_cents=proposal.target_price_cents,
                                        interval_hours=proposal.interval_hours, created_at=current,
                                    ))
                                    removed = connection.scalar(delete(table).where(
                                        table.telegram_user_id == telegram_user_id,
                                        table.version == draft["version"],
                                    ).returning(table.telegram_user_id))
                                    if removed is None:
                                        raise RuntimeError("Versão do rascunho perdida.")
                                    reply = replies.created
            connection.execute(insert(TelegramRegistrationResult).values(
                update_id=update_id, telegram_user_id=telegram_user_id,
                chat_id=chat_id, reply_text=reply, created_at=current,
            ))
            if connection.scalar(select(func.clock_timestamp())) >= inbox["lease_expires_at"]:
                raise RuntimeError("Lease de cadastro expirou durante a transação.")
            return TelegramMessage(chat_id=chat_id, text=reply)
