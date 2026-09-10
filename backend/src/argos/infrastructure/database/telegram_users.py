"""Repositório PostgreSQL de identidades Telegram."""

from datetime import datetime
from typing import Any

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Row

from argos.application.ports.telegram_users import TelegramUser
from argos.infrastructure.database.models import TelegramUserRecord


class PostgreSQLTelegramUserRepository:
    """Persiste o proprietário separadamente do destino de mensagens."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def upsert(
        self,
        *,
        telegram_user_id: int,
        chat_id: int,
        observed_at: datetime,
    ) -> TelegramUser:
        incoming = insert(TelegramUserRecord).values(
            telegram_user_id=telegram_user_id,
            chat_id=chat_id,
            created_at=observed_at,
            updated_at=observed_at,
        )
        statement = (
            incoming.on_conflict_do_update(
                index_elements=["telegram_user_id"],
                set_={
                    "chat_id": incoming.excluded.chat_id,
                    "updated_at": incoming.excluded.updated_at,
                },
                where=(
                    incoming.excluded.updated_at
                    > TelegramUserRecord.updated_at
                ),
            )
            .returning(
                TelegramUserRecord.telegram_user_id,
                TelegramUserRecord.chat_id,
                TelegramUserRecord.created_at,
                TelegramUserRecord.updated_at,
            )
        )

        with self._engine.begin() as connection:
            record = connection.execute(statement).one_or_none()
            if record is None:
                record = connection.execute(
                    select(
                        TelegramUserRecord.telegram_user_id,
                        TelegramUserRecord.chat_id,
                        TelegramUserRecord.created_at,
                        TelegramUserRecord.updated_at,
                    ).where(
                        TelegramUserRecord.telegram_user_id == telegram_user_id
                    )
                ).one()
        return _to_user(record)

    def get_by_owner(self, *, telegram_user_id: int) -> TelegramUser | None:
        statement = select(
            TelegramUserRecord.telegram_user_id,
            TelegramUserRecord.chat_id,
            TelegramUserRecord.created_at,
            TelegramUserRecord.updated_at,
        ).where(TelegramUserRecord.telegram_user_id == telegram_user_id)
        with self._engine.connect() as connection:
            record = connection.execute(statement).one_or_none()
        return None if record is None else _to_user(record)


def _to_user(record: Row[Any]) -> TelegramUser:
    return TelegramUser(
        telegram_user_id=record.telegram_user_id,
        chat_id=record.chat_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
