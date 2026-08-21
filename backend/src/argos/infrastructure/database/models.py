"""Modelos ORM exclusivos da infraestrutura de persistência."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, MetaData, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base dos modelos, com nomes estáveis para constraints."""

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


class ProcessedTelegramUpdate(Base):
    """Reserva persistente usada para deduplicar entregas do Telegram."""

    __tablename__ = "processed_telegram_updates"
    __table_args__ = (
        CheckConstraint(
            "status IN ('claimed', 'completed', 'failed')",
            name="valid_status",
        ),
        CheckConstraint(
            "(status = 'claimed' AND completed_at IS NULL AND failure_code IS NULL) "
            "OR (status = 'completed' AND completed_at IS NOT NULL "
            "AND failure_code IS NULL) "
            "OR (status = 'failed' AND completed_at IS NULL "
            "AND failure_code IS NOT NULL)",
            name="valid_result",
        ),
    )

    update_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="claimed",
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failure_code: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
