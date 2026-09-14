"""Avanço do preço-alvo e resposta durável sob o lease da inbox."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Engine, func, insert, select, update

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_target_price import RegistrationTargetPriceReplies
from argos.domain.target_price import parse_target_price_cents
from argos.infrastructure.database.models import (
    TelegramConversationDraftRecord, TelegramRegistrationResult,
    TelegramUpdateInbox, TelegramUserRecord,
)


class PostgreSQLTelegramRegistrationTargetPriceRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def receive_for_update(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str, target_price_cents: int | None,
        observed_at: datetime, replies: RegistrationTargetPriceReplies,
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
            try:
                verified_cents = parse_target_price_cents(text)
            except ValueError:
                verified_cents = None
            if (target_price_cents is not None and (not isinstance(target_price_cents, int) or isinstance(target_price_cents, bool))) or verified_cents != target_price_cents:
                raise RuntimeError("Apelido normalizado divergente.")
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
                if draft["state"] != "awaiting_target_price":
                    reply = replies.unexpected_state
                elif verified_cents is None:
                    reply = replies.invalid_target_price
                else:
                    changed = connection.scalar(update(table).where(
                        table.telegram_user_id == telegram_user_id,
                        table.version == draft["version"],
                        table.state == "awaiting_target_price",
                        table.expires_at > effective_at,
                    ).values(
                        state="awaiting_interval", data={**draft["data"], "target_price_cents": verified_cents},
                        updated_at=effective_at, version=uuid4(),
                    ).returning(table.telegram_user_id))
                    if changed is None:
                        raise RuntimeError("Versão do rascunho perdida.")
                    reply = replies.accepted
            connection.execute(insert(TelegramRegistrationResult).values(
                update_id=update_id, telegram_user_id=telegram_user_id,
                chat_id=chat_id, reply_text=reply, created_at=current,
            ))
            if connection.scalar(select(func.clock_timestamp())) >= inbox["lease_expires_at"]:
                raise RuntimeError("Lease de cadastro expirou durante a transação.")
            return TelegramMessage(chat_id=chat_id, text=reply)
