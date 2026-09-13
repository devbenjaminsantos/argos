"""Resultado imutável do início de cadastro por update."""
from alembic import context, op
import sqlalchemy as sa

revision = "20260913_07"
down_revision = "20260913_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("telegram_registration_results",
        sa.Column("update_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("reply_text", sa.String(4096), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("telegram_user_id > 0 AND chat_id > 0", name=op.f("ck_telegram_registration_results_positive_identity")),
        sa.CheckConstraint("length(reply_text) BETWEEN 1 AND 4096", name=op.f("ck_telegram_registration_results_valid_reply")),
        sa.ForeignKeyConstraint(["update_id"], ["telegram_update_inbox.update_id"], name=op.f("fk_telegram_registration_results_update_id_telegram_update_inbox")),
        sa.PrimaryKeyConstraint("update_id", name=op.f("pk_telegram_registration_results")),
    )
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.telegram_registration_results FROM PUBLIC, anon, authenticated, service_role")
    op.execute("GRANT SELECT, INSERT ON TABLE public.telegram_registration_results TO argos_runtime")


def downgrade() -> None:
    if not context.is_offline_mode() and op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM telegram_registration_results)")):
        raise RuntimeError("Resultados existentes; downgrade destrutivo recusado.")
    op.drop_table("telegram_registration_results")
