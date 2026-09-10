"""Cria a identidade Telegram persistente.

Revision ID: 20260910_03
Revises: 20260910_02
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import context, op
import sqlalchemy as sa

revision: str = "20260910_03"
down_revision: str | Sequence[str] | None = "20260910_02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "telegram_users",
        sa.Column(
            "telegram_user_id",
            sa.BigInteger(),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "telegram_user_id > 0",
            name=op.f("ck_telegram_users_positive_user_id"),
        ),
        sa.CheckConstraint(
            "chat_id > 0",
            name=op.f("ck_telegram_users_positive_chat_id"),
        ),
        sa.PrimaryKeyConstraint(
            "telegram_user_id",
            name=op.f("pk_telegram_users"),
        ),
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE ON TABLE public.telegram_users "
        "TO argos_runtime"
    )
    op.execute(
        "REVOKE ALL PRIVILEGES ON TABLE public.telegram_users "
        "FROM PUBLIC, anon, authenticated, service_role"
    )


def downgrade() -> None:
    if not context.is_offline_mode():
        has_rows = op.get_bind().scalar(
            sa.text("SELECT EXISTS (SELECT 1 FROM telegram_users)")
        )
        if has_rows:
            raise RuntimeError(
                "telegram_users contém dados; downgrade destrutivo recusado."
            )

    op.drop_table("telegram_users")
