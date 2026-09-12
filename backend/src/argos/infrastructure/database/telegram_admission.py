"""Admissão serializada por proprietário na mesma transação da inbox."""

from datetime import datetime, timedelta

from sqlalchemy import Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.telegram_admission import TelegramAdmissionResult
from argos.infrastructure.database.models import (
    TelegramAdmissionOwner,
    TelegramAdmissionRecord,
    TelegramUpdateInbox,
)


class PostgreSQLTelegramAdmissionRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def admit(
        self, *, update_id: int, telegram_user_id: int,
        payload: dict[str, object], received_at: datetime,
        maximum_commands: int, window: timedelta,
    ) -> TelegramAdmissionResult:
        if maximum_commands <= 0 or window <= timedelta(0) or received_at.utcoffset() is None:
            raise ValueError("Política ou horário de admissão inválido.")
        with self._engine.begin() as connection:
            connection.execute(
                insert(TelegramAdmissionOwner)
                .values(telegram_user_id=telegram_user_id, observed_at=received_at)
                .on_conflict_do_nothing(index_elements=["telegram_user_id"])
            )
            previous = connection.scalar(
                select(TelegramAdmissionOwner.observed_at)
                .where(TelegramAdmissionOwner.telegram_user_id == telegram_user_id)
                .with_for_update()
            )
            effective_at = max(received_at, previous)
            # Updates anteriores à ativação do limite já estão deduplicados.
            if connection.scalar(select(TelegramUpdateInbox.update_id).where(
                TelegramUpdateInbox.update_id == update_id
            )) is not None:
                return TelegramAdmissionResult.DUPLICATE
            reserved = connection.scalar(
                insert(TelegramAdmissionRecord)
                .values(update_id=update_id, telegram_user_id=telegram_user_id,
                        decided_at=effective_at, decision="rate_limited")
                .on_conflict_do_nothing(index_elements=["update_id"])
                .returning(TelegramAdmissionRecord.update_id)
            )
            if reserved is None:
                return TelegramAdmissionResult.DUPLICATE
            connection.execute(update(TelegramAdmissionOwner).where(
                TelegramAdmissionOwner.telegram_user_id == telegram_user_id
            ).values(observed_at=effective_at))
            count = connection.scalar(select(func.count()).select_from(
                TelegramAdmissionRecord
            ).where(
                TelegramAdmissionRecord.telegram_user_id == telegram_user_id,
                TelegramAdmissionRecord.decision == "admitted",
                TelegramAdmissionRecord.decided_at > effective_at - window,
                TelegramAdmissionRecord.decided_at <= effective_at,
            ))
            if count >= maximum_commands:
                return TelegramAdmissionResult.RATE_LIMITED
            inserted = connection.scalar(
                insert(TelegramUpdateInbox)
                .values(update_id=update_id, payload=payload, status="pending",
                        received_at=effective_at, next_attempt_at=effective_at)
                .on_conflict_do_nothing(index_elements=["update_id"])
                .returning(TelegramUpdateInbox.update_id)
            )
            if inserted is None:
                # Um produtor legado pode disputar o update fora deste contrato.
                # Reverter a reserva inteira evita decisão inconsistente.
                raise RuntimeError("Update disputado por produtor fora da admissão.")
            connection.execute(update(TelegramAdmissionRecord).where(
                TelegramAdmissionRecord.update_id == update_id
            ).values(decision="admitted"))
            return TelegramAdmissionResult.ADMITTED
