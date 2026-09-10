"""Implementação PostgreSQL da inbox Telegram."""

from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import Engine, and_, case, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.telegram_inbox import ClaimedTelegramUpdate
from argos.infrastructure.database.models import TelegramUpdateInbox


class PostgreSQLTelegramInbox:
    """Inbox com deduplicação e leases decididos pelo PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def enqueue(
        self,
        *,
        update_id: int,
        payload: dict[str, object],
        received_at: datetime,
    ) -> bool:
        statement = (
            insert(TelegramUpdateInbox)
            .values(
                update_id=update_id,
                payload=payload,
                status="pending",
                received_at=received_at,
                next_attempt_at=received_at,
            )
            .on_conflict_do_nothing(index_elements=["update_id"])
            .returning(TelegramUpdateInbox.update_id)
        )
        with self._engine.begin() as connection:
            return connection.scalar(statement) is not None

    def claim_next(
        self,
        *,
        now: datetime,
        lease_duration: timedelta,
    ) -> ClaimedTelegramUpdate | None:
        if lease_duration <= timedelta(0):
            raise ValueError("lease_duration deve ser positiva.")

        eligible = or_(
            and_(
                TelegramUpdateInbox.status == "pending",
                TelegramUpdateInbox.next_attempt_at <= now,
            ),
            and_(
                TelegramUpdateInbox.status == "processing",
                TelegramUpdateInbox.lease_expires_at <= now,
            ),
        )
        available_at = case(
            (
                TelegramUpdateInbox.status == "processing",
                TelegramUpdateInbox.lease_expires_at,
            ),
            else_=TelegramUpdateInbox.next_attempt_at,
        )
        candidate = (
            select(TelegramUpdateInbox.update_id)
            .where(eligible)
            .order_by(
                available_at,
                TelegramUpdateInbox.received_at,
                TelegramUpdateInbox.update_id,
            )
            .with_for_update(skip_locked=True)
            .limit(1)
            .cte("claimable_telegram_update")
        )
        lease_token = uuid4()
        statement = (
            update(TelegramUpdateInbox)
            .where(TelegramUpdateInbox.update_id == candidate.c.update_id)
            .values(
                status="processing",
                attempt_count=TelegramUpdateInbox.attempt_count + 1,
                lease_token=lease_token,
                lease_expires_at=now + lease_duration,
            )
            .returning(
                TelegramUpdateInbox.update_id,
                TelegramUpdateInbox.payload,
                TelegramUpdateInbox.attempt_count,
                TelegramUpdateInbox.lease_token,
                TelegramUpdateInbox.lease_expires_at,
            )
        )
        with self._engine.begin() as connection:
            row = connection.execute(statement).one_or_none()

        if row is None:
            return None
        return ClaimedTelegramUpdate(
            update_id=row.update_id,
            payload=row.payload,
            attempt_count=row.attempt_count,
            lease_token=row.lease_token,
            lease_expires_at=row.lease_expires_at,
        )

    def complete(
        self,
        *,
        update_id: int,
        lease_token: UUID,
        completed_at: datetime,
    ) -> bool:
        statement = (
            update(TelegramUpdateInbox)
            .where(
                TelegramUpdateInbox.update_id == update_id,
                TelegramUpdateInbox.status == "processing",
                TelegramUpdateInbox.lease_token == lease_token,
            )
            .values(
                status="completed",
                lease_token=None,
                lease_expires_at=None,
                completed_at=completed_at,
                last_error_code=None,
            )
            .returning(TelegramUpdateInbox.update_id)
        )
        with self._engine.begin() as connection:
            return connection.scalar(statement) is not None

    def retry(
        self,
        *,
        update_id: int,
        lease_token: UUID,
        next_attempt_at: datetime,
        error_code: str,
    ) -> bool:
        if not error_code or len(error_code) > 64:
            raise ValueError("error_code deve ter entre 1 e 64 caracteres.")

        statement = (
            update(TelegramUpdateInbox)
            .where(
                TelegramUpdateInbox.update_id == update_id,
                TelegramUpdateInbox.status == "processing",
                TelegramUpdateInbox.lease_token == lease_token,
            )
            .values(
                status="pending",
                next_attempt_at=next_attempt_at,
                lease_token=None,
                lease_expires_at=None,
                last_error_code=error_code,
            )
            .returning(TelegramUpdateInbox.update_id)
        )
        with self._engine.begin() as connection:
            return connection.scalar(statement) is not None

    def dead_letter(
        self,
        *,
        update_id: int,
        lease_token: UUID,
        error_code: str,
    ) -> bool:
        if not error_code or len(error_code) > 64:
            raise ValueError("error_code deve ter entre 1 e 64 caracteres.")

        statement = (
            update(TelegramUpdateInbox)
            .where(
                TelegramUpdateInbox.update_id == update_id,
                TelegramUpdateInbox.status == "processing",
                TelegramUpdateInbox.lease_token == lease_token,
            )
            .values(
                status="dead_letter",
                lease_token=None,
                lease_expires_at=None,
                last_error_code=error_code,
            )
            .returning(TelegramUpdateInbox.update_id)
        )
        with self._engine.begin() as connection:
            return connection.scalar(statement) is not None
