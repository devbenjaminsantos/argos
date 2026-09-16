"""Persistência PostgreSQL idempotente das observações de preço."""

from uuid import UUID

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert

from argos.application.ports.price_observations import (
    PriceObservation,
    PriceObservationConflictError,
)
from argos.infrastructure.database.models import ProductPriceObservationRecord


class PostgreSQLPriceObservationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def append(self, observation: PriceObservation) -> None:
        values = {
            "id": observation.observation_id,
            "product_id": observation.product_id,
            "telegram_user_id": observation.telegram_user_id,
            "observed_at": observation.observed_at,
            "target_price_cents": observation.target_price_cents,
            "status": observation.status,
            "price_cents": observation.price_cents,
            "source": observation.source,
            "error_code": observation.error_code,
        }
        statement = (
            insert(ProductPriceObservationRecord)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=[ProductPriceObservationRecord.id]
            )
            .returning(ProductPriceObservationRecord.id)
        )

        with self._engine.begin() as connection:
            inserted = connection.scalar(statement)
            if inserted is not None:
                return
            existing = connection.execute(
                select(ProductPriceObservationRecord.__table__).where(
                    ProductPriceObservationRecord.id
                    == observation.observation_id
                )
            ).mappings().one()
            if any(existing[column] != value for column, value in values.items()):
                raise PriceObservationConflictError(
                    "UUID de observação reutilizado com conteúdo divergente."
                )

    def find(
        self, *, observation_id: UUID, product_id: UUID,
        telegram_user_id: int,
    ) -> PriceObservation | None:
        if (not isinstance(observation_id, UUID)
            or not isinstance(product_id, UUID)
            or not isinstance(telegram_user_id, int)
            or isinstance(telegram_user_id, bool)
            or telegram_user_id <= 0):
            raise ValueError("Consulta de observação inválida.")
        table = ProductPriceObservationRecord
        with self._engine.connect() as connection:
            row = connection.execute(
                select(table.__table__).where(
                    table.id == observation_id,
                    table.product_id == product_id,
                    table.telegram_user_id == telegram_user_id,
                )
            ).mappings().one_or_none()
        if row is None:
            return None
        return PriceObservation(
            observation_id=row["id"], product_id=row["product_id"],
            telegram_user_id=row["telegram_user_id"],
            observed_at=row["observed_at"],
            target_price_cents=row["target_price_cents"],
            status=row["status"], price_cents=row["price_cents"],
            source=row["source"], error_code=row["error_code"],
        )
