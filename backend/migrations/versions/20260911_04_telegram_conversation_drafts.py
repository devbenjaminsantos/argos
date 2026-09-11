"""Cria rascunhos conversacionais por proprietário.

Revision ID: 20260911_04
Revises: 20260910_03
Create Date: 2026-09-11
"""

from collections.abc import Sequence
from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260911_04"
down_revision: str | Sequence[str] | None = "20260910_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_conversation_drafts",
        sa.Column("telegram_user_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("state", sa.String(length=40), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_telegram_conversation_drafts_valid_expiry")),
        sa.CheckConstraint("state IN ('awaiting_url', 'awaiting_alias', 'awaiting_target_price', 'awaiting_interval', 'awaiting_confirmation', 'awaiting_product_to_remove', 'awaiting_removal_confirmation')", name=op.f("ck_telegram_conversation_drafts_valid_state")),
        sa.ForeignKeyConstraint(["telegram_user_id"], ["telegram_users.telegram_user_id"], name=op.f("fk_telegram_conversation_drafts_telegram_user_id_telegram_users"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("telegram_user_id", name=op.f("pk_telegram_conversation_drafts")),
    )
    op.create_index("ix_telegram_conversation_drafts_expires_at", "telegram_conversation_drafts", ["expires_at"])
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.telegram_conversation_drafts TO argos_runtime")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.telegram_conversation_drafts FROM PUBLIC, anon, authenticated, service_role")


def downgrade() -> None:
    if not context.is_offline_mode() and op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM telegram_conversation_drafts)")):
        raise RuntimeError("telegram_conversation_drafts contém dados; downgrade destrutivo recusado.")
    op.drop_index("ix_telegram_conversation_drafts_expires_at", table_name="telegram_conversation_drafts")
    op.drop_table("telegram_conversation_drafts")
