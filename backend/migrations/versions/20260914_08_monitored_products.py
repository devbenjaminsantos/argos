"""Produtos confirmados com slots limitados por proprietário."""
from alembic import context,op
import sqlalchemy as sa

revision="20260914_08"
down_revision="20260913_07"
branch_labels=None
depends_on=None


def upgrade():
    op.create_table("monitored_products",
        sa.Column("id",sa.UUID(),nullable=False),
        sa.Column("telegram_user_id",sa.BigInteger(),nullable=False),
        sa.Column("slot",sa.Integer(),nullable=False),
        sa.Column("product_key",sa.String(64),nullable=False),
        sa.Column("url",sa.String(2048),nullable=False),
        sa.Column("alias",sa.String(60),nullable=False),
        sa.Column("target_price_cents",sa.BigInteger(),nullable=False),
        sa.Column("interval_hours",sa.Integer(),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),
        sa.PrimaryKeyConstraint("id",name="pk_monitored_products"),
        sa.ForeignKeyConstraint(["telegram_user_id"],["telegram_users.telegram_user_id"],name="fk_monitored_products_telegram_user_id_telegram_users"),
        sa.UniqueConstraint("telegram_user_id","slot",name="uq_monitored_products_owner_slot"),
        sa.UniqueConstraint("telegram_user_id","product_key",name="uq_monitored_products_owner_key"),
        sa.CheckConstraint("slot BETWEEN 1 AND 3",name=op.f("ck_monitored_products_valid_slot")),
        sa.CheckConstraint("product_key ~ '^MLB(U)?[0-9]+$'",name=op.f("ck_monitored_products_valid_product_key")),
        sa.CheckConstraint("length(alias) BETWEEN 1 AND 60",name=op.f("ck_monitored_products_valid_alias")),
        sa.CheckConstraint("target_price_cents BETWEEN 1 AND 999999999",name=op.f("ck_monitored_products_valid_target_price")),
        sa.CheckConstraint("interval_hours IN (12,24)",name=op.f("ck_monitored_products_valid_interval")),
    )
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.monitored_products FROM PUBLIC, anon, authenticated, service_role")
    op.execute("GRANT SELECT, INSERT ON TABLE public.monitored_products TO argos_runtime")


def downgrade():
    if not context.is_offline_mode() and op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM monitored_products)")):
        raise RuntimeError("Produtos existentes; downgrade destrutivo recusado.")
    op.drop_table("monitored_products")
