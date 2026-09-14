"""Seleção do passo de texto e resposta durável sob o lease da inbox."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Engine, func, insert, select, update

from argos.application.ports.telegram_messages import TelegramMessage
from argos.application.ports.telegram_registration_url import RegistrationURLReplies
from argos.application.ports.telegram_registration_interval import RegistrationIntervalReplies
from argos.application.ports.telegram_registration_target_price import RegistrationTargetPriceReplies
from argos.application.ports.telegram_registration_alias import RegistrationAliasReplies
from argos.domain.collection_interval import parse_collection_interval_hours
from argos.domain.target_price import parse_target_price_cents, format_target_price_brl
from argos.domain.product_alias import normalize_product_alias
from argos.domain.mercado_livre_url import normalize_mercado_livre_product_url
from argos.infrastructure.database.models import (
    TelegramConversationDraftRecord, TelegramRegistrationResult,
    TelegramUpdateInbox, TelegramUserRecord,
)


class PostgreSQLTelegramRegistrationTextRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def receive_for_update(
        self, *, update_id: int, lease_token: UUID, telegram_user_id: int,
        chat_id: int, text: str,
        observed_at: datetime, url_replies: RegistrationURLReplies, alias_replies: RegistrationAliasReplies,
        price_replies: RegistrationTargetPriceReplies,
        interval_replies: RegistrationIntervalReplies,
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
            reply = url_replies.no_active_draft
            if user is not None and draft is not None and draft["expires_at"] > effective_at:
                state = draft["state"]
                steps = {
                    "awaiting_url": (normalize_mercado_livre_product_url, "url", "awaiting_alias", url_replies.accepted, url_replies.invalid_url),
                    "awaiting_alias": (normalize_product_alias, "alias", "awaiting_target_price", alias_replies.accepted, alias_replies.invalid_alias),
                    "awaiting_target_price": (parse_target_price_cents, "target_price_cents", "awaiting_interval", price_replies.accepted, price_replies.invalid_target_price),
                }
                steps["awaiting_interval"] = (parse_collection_interval_hours, "interval_hours", "awaiting_confirmation", interval_replies.accepted, interval_replies.invalid_interval)
                step = steps.get(state)
                value = None
                reply = alias_replies.unexpected_state
                if step is not None:
                    normalizer, key, following, accepted, invalid = step
                    try:
                        value = normalizer(text)
                    except ValueError:
                        pass
                    reply = invalid
                if value is not None:
                    changed = connection.scalar(update(table).where(
                        table.telegram_user_id == telegram_user_id,
                        table.version == draft["version"],
                        table.state == state,
                        table.expires_at > effective_at,
                    ).values(
                        state=following,
                        data={**draft["data"], key: value},
                        updated_at=effective_at, version=uuid4(),
                    ).returning(table.telegram_user_id))
                    if changed is None:
                        raise RuntimeError("Versão do rascunho perdida.")
                    reply = accepted.format(price_brl=format_target_price_brl(value)) if state == "awaiting_target_price" else accepted
            connection.execute(insert(TelegramRegistrationResult).values(
                update_id=update_id, telegram_user_id=telegram_user_id,
                chat_id=chat_id, reply_text=reply, created_at=current,
            ))
            if connection.scalar(select(func.clock_timestamp())) >= inbox["lease_expires_at"]:
                raise RuntimeError("Lease de cadastro expirou durante a transação.")
            return TelegramMessage(chat_id=chat_id, text=reply)
