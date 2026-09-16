"""Leitura PostgreSQL proprietária do alvo ativo de verificação."""
from uuid import UUID

from sqlalchemy import Engine, select

from argos.application.ports.product_verification import ProductVerificationTarget
from argos.infrastructure.database.models import MonitoredProductRecord


class PostgreSQLProductVerificationTargets:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def find_active(self, *, telegram_user_id: int,
                    product_id: UUID) -> ProductVerificationTarget | None:
        if (not isinstance(telegram_user_id, int) or isinstance(telegram_user_id, bool)
            or telegram_user_id <= 0 or not isinstance(product_id, UUID)):
            raise ValueError("Consulta de alvo inválida.")
        product = MonitoredProductRecord
        with self._engine.connect() as connection:
            row = connection.execute(select(
                product.id, product.product_key, product.url,
                product.alias, product.target_price_cents,
            ).where(
                product.id == product_id,
                product.telegram_user_id == telegram_user_id,
                product.removed_at.is_(None),
            )).one_or_none()
        if row is None:
            return None
        return ProductVerificationTarget(
            product_id=row.id, product_key=row.product_key, url=row.url,
            alias=row.alias, target_price_cents=row.target_price_cents,
        )
