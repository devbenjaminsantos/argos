"""Cria a reserva de updates processados do Telegram.

Revision ID: 20260821_01
Revises: None
Create Date: 2026-08-21
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260821_01"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processed_telegram_updates",
        sa.Column("update_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "(status = 'claimed' AND completed_at IS NULL AND failure_code IS NULL) "
            "OR (status = 'completed' AND completed_at IS NOT NULL "
            "AND failure_code IS NULL) "
            "OR (status = 'failed' AND completed_at IS NULL "
            "AND failure_code IS NOT NULL)",
            name=op.f("ck_processed_telegram_updates_valid_result"),
        ),
        sa.CheckConstraint(
            "status IN ('claimed', 'completed', 'failed')",
            name=op.f("ck_processed_telegram_updates_valid_status"),
        ),
        sa.PrimaryKeyConstraint(
            "update_id",
            name=op.f("pk_processed_telegram_updates"),
        ),
    )


def downgrade() -> None:
    op.drop_table("processed_telegram_updates")
