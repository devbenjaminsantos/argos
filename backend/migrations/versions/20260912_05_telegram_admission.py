"""Admissão atômica e limite por proprietário.

Revision ID: 20260912_05
Revises: 20260911_04
"""

from alembic import context, op
import sqlalchemy as sa

revision = "20260912_05"
down_revision = "20260911_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_admission_owners",
        sa.Column("telegram_user_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("telegram_user_id > 0", name=op.f("ck_telegram_admission_owners_positive_user_id")),
        sa.PrimaryKeyConstraint("telegram_user_id", name=op.f("pk_telegram_admission_owners")),
    )
    op.create_table(
        "telegram_admissions",
        sa.Column("update_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(16), nullable=False),
        sa.CheckConstraint("decision IN ('admitted', 'rate_limited')", name=op.f("ck_telegram_admissions_valid_decision")),
        sa.ForeignKeyConstraint(["telegram_user_id"], ["telegram_admission_owners.telegram_user_id"], name=op.f("fk_telegram_admissions_telegram_user_id_telegram_admission_owners")),
        sa.PrimaryKeyConstraint("update_id", name=op.f("pk_telegram_admissions")),
    )
    op.create_index("ix_telegram_admissions_owner_window", "telegram_admissions",
                    ["telegram_user_id", "decided_at"], postgresql_where=sa.text("decision = 'admitted'"))
    for table in ("telegram_admission_owners", "telegram_admissions"):
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM PUBLIC, anon, authenticated, service_role")
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON TABLE public.{table} TO argos_runtime")


def downgrade() -> None:
    if not context.is_offline_mode():
        for table in ("telegram_admissions", "telegram_admission_owners"):
            if op.get_bind().scalar(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table})")):
                raise RuntimeError("Admissão contém dados; downgrade destrutivo recusado.")
    op.drop_index("ix_telegram_admissions_owner_window", table_name="telegram_admissions")
    op.drop_table("telegram_admissions")
    op.drop_table("telegram_admission_owners")
