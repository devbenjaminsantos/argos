"""Repositório PostgreSQL de rascunhos conversacionais."""

from datetime import datetime
from uuid import uuid4
from typing import Any

from sqlalchemy import Engine, delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Row

from argos.application.ports.telegram_conversations import TelegramConversationDraft
from argos.infrastructure.database.models import TelegramConversationDraftRecord
from argos.domain.telegram_conversation import validate_conversation_transition


class PostgreSQLTelegramConversationDraftRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def begin(
        self, *, telegram_user_id: int, observed_at: datetime, expires_at: datetime
    ) -> TelegramConversationDraft | None:
        _validate_time(observed_at)
        _validate_time(expires_at)
        if telegram_user_id <= 0 or expires_at <= observed_at:
            raise ValueError("Proprietário ou expiração inválidos.")
        table = TelegramConversationDraftRecord
        values = dict(telegram_user_id=telegram_user_id, state="awaiting_url",
                      data={}, created_at=observed_at, updated_at=observed_at,
                      expires_at=expires_at, version=uuid4())
        statement = insert(table).values(**values).on_conflict_do_update(
            index_elements=["telegram_user_id"],
            set_={key: value for key, value in values.items() if key != "telegram_user_id"},
            where=table.expires_at <= observed_at,
        ).returning(*table.__table__.columns)
        with self._engine.begin() as connection:
            row = connection.execute(statement).one_or_none()
        return None if row is None else _to_draft(row)

    def advance(
        self, *, expected: TelegramConversationDraft, state: str,
        data: dict[str, object], observed_at: datetime
    ) -> TelegramConversationDraft | None:
        _validate_time(observed_at)
        validate_conversation_transition(expected.state, state)
        if observed_at <= expected.updated_at:
            raise ValueError("Atualização deve avançar o horário da versão.")
        table = TelegramConversationDraftRecord
        statement = update(table).where(
            table.telegram_user_id == expected.telegram_user_id,
            table.version == expected.version,
            table.created_at == expected.created_at,
            table.updated_at == expected.updated_at,
            table.state == expected.state,
            table.expires_at > observed_at,
        ).values(state=state, data=data, updated_at=observed_at, version=uuid4()).returning(
            *table.__table__.columns
        )
        with self._engine.begin() as connection:
            row = connection.execute(statement).one_or_none()
        return None if row is None else _to_draft(row)

    def get_active(self, *, telegram_user_id: int, observed_at: datetime) -> TelegramConversationDraft | None:
        statement = select(
            TelegramConversationDraftRecord.telegram_user_id,
            TelegramConversationDraftRecord.state,
            TelegramConversationDraftRecord.data,
            TelegramConversationDraftRecord.created_at,
            TelegramConversationDraftRecord.updated_at,
            TelegramConversationDraftRecord.expires_at,
            TelegramConversationDraftRecord.version,
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
        version=row.version,
    )



def _validate_time(value: datetime) -> None:
    if value.utcoffset() is None:
        raise ValueError("Horário deve possuir fuso.")
