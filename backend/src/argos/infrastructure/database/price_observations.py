"""Persistência PostgreSQL idempotente das observações de preço."""

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
