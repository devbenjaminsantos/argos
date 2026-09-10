"""Substitui o marcador mínimo por uma inbox Telegram recuperável.

Revision ID: 20260910_02
Revises: 20260821_01
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260910_02"
down_revision: str | Sequence[str] | None = "20260821_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not context.is_offline_mode():
        has_legacy_rows = op.get_bind().scalar(
            sa.text("SELECT EXISTS (SELECT 1 FROM processed_telegram_updates)")
        )
        if has_legacy_rows:
            raise RuntimeError(
                "processed_telegram_updates contém dados; migração automática recusada."
            )

    op.drop_table("processed_telegram_updates")
    op.create_table(
        "telegram_update_inbox",
        sa.Column("update_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("lease_token", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint("attempt_count >= 0", name=op.f("ck_telegram_update_inbox_attempt_count_nonnegative")),
        sa.CheckConstraint(
            "(status = 'processing' AND lease_token IS NOT NULL "
            "AND lease_expires_at IS NOT NULL AND completed_at IS NULL) "
            "OR (status = 'completed' AND lease_token IS NULL "
            "AND lease_expires_at IS NULL AND completed_at IS NOT NULL) "
            "OR (status IN ('pending', 'dead_letter') "
            "AND lease_token IS NULL AND lease_expires_at IS NULL "
            "AND completed_at IS NULL)",
            name=op.f("ck_telegram_update_inbox_valid_lifecycle"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'dead_letter')",
            name=op.f("ck_telegram_update_inbox_valid_status"),
        ),
        sa.PrimaryKeyConstraint("update_id", name=op.f("pk_telegram_update_inbox")),
    )
    op.create_index(
        "ix_telegram_update_inbox_available",
        "telegram_update_inbox",
        ["next_attempt_at", "received_at"],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "ix_telegram_update_inbox_expired_lease",
        "telegram_update_inbox",
        ["lease_expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'processing'"),
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE public.telegram_update_inbox TO argos_runtime")
    op.execute(
        "REVOKE ALL PRIVILEGES ON TABLE public.telegram_update_inbox "
        "FROM PUBLIC, anon, authenticated, service_role"
    )


def downgrade() -> None:
    if not context.is_offline_mode():
        has_inbox_rows = op.get_bind().scalar(
            sa.text("SELECT EXISTS (SELECT 1 FROM telegram_update_inbox)")
        )
        if has_inbox_rows:
            raise RuntimeError(
                "telegram_update_inbox contém dados; downgrade destrutivo recusado."
            )

    op.drop_index("ix_telegram_update_inbox_expired_lease", table_name="telegram_update_inbox")
    op.drop_index("ix_telegram_update_inbox_available", table_name="telegram_update_inbox")
    op.drop_table("telegram_update_inbox")
    op.create_table(
        "processed_telegram_updates",
        sa.Column("update_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "(status = 'claimed' AND completed_at IS NULL AND failure_code IS NULL) "
            "OR (status = 'completed' AND completed_at IS NOT NULL AND failure_code IS NULL) "
            "OR (status = 'failed' AND completed_at IS NULL AND failure_code IS NOT NULL)",
            name=op.f("ck_processed_telegram_updates_valid_result"),
        ),
        sa.CheckConstraint(
            "status IN ('claimed', 'completed', 'failed')",
            name=op.f("ck_processed_telegram_updates_valid_status"),
        ),
        sa.PrimaryKeyConstraint("update_id", name=op.f("pk_processed_telegram_updates")),
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE public.processed_telegram_updates TO argos_runtime")
    op.execute(
        "REVOKE ALL PRIVILEGES ON TABLE public.processed_telegram_updates "
        "FROM PUBLIC, anon, authenticated, service_role"
    )
