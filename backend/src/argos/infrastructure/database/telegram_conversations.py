"""Repositório PostgreSQL de rascunhos conversacionais."""

from datetime import datetime
from typing import Any

from sqlalchemy import Engine, delete, select
from sqlalchemy.engine import Row

from argos.application.ports.telegram_conversations import TelegramConversationDraft
from argos.infrastructure.database.models import TelegramConversationDraftRecord


class PostgreSQLTelegramConversationDraftRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get_active(self, *, telegram_user_id: int, observed_at: datetime) -> TelegramConversationDraft | None:
        statement = select(
            TelegramConversationDraftRecord.telegram_user_id,
            TelegramConversationDraftRecord.state,
            TelegramConversationDraftRecord.data,
            TelegramConversationDraftRecord.created_at,
            TelegramConversationDraftRecord.updated_at,
            TelegramConversationDraftRecord.expires_at,
        ).where(
            TelegramConversationDraftRecord.telegram_user_id == telegram_user_id,
            TelegramConversationDraftRecord.expires_at > observed_at,
        )
        with self._engine.connect() as connection:
            row = connection.execute(statement).one_or_none()
        return None if row is None else _to_draft(row)

    def cancel_for_owner(self, *, telegram_user_id: int) -> bool:
        statement = delete(TelegramConversationDraftRecord).where(
            TelegramConversationDraftRecord.telegram_user_id == telegram_user_id
        ).returning(TelegramConversationDraftRecord.telegram_user_id)
        with self._engine.begin() as connection:
            return connection.scalar(statement) is not None


def _to_draft(row: Row[Any]) -> TelegramConversationDraft:
    return TelegramConversationDraft(
        telegram_user_id=row.telegram_user_id,
        state=row.state,
        data=row.data,
        created_at=row.created_at,
        updated_at=row.updated_at,
        expires_at=row.expires_at,
    )
