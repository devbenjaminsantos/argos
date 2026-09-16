"""Observações append-only de preço ou falha explícita."""
from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260916_10"
down_revision = "20260914_09"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_monitored_products_id_owner", "monitored_products",
        ["id", "telegram_user_id"],
    )
    op.create_table(
        "product_price_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_price_cents", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("price_cents", sa.BigInteger(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.CheckConstraint("telegram_user_id > 0", name=op.f("ck_product_price_observations_positive_owner")),
        sa.CheckConstraint("target_price_cents BETWEEN 1 AND 999999999", name=op.f("ck_product_price_observations_valid_target_price")),
        sa.CheckConstraint(
            "(status = 'success' AND price_cents BETWEEN 1 AND 999999999 "
            "AND source IN ('json-ld','meta','visible-dom') AND error_code IS NULL) OR "
            "(status = 'failure' AND price_cents IS NULL AND source IS NULL "
            "AND error_code ~ '^[a-z][a-z0-9_]{0,63}$')",
            name=op.f("ck_product_price_observations_valid_outcome"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id", "telegram_user_id"],
            ["monitored_products.id", "monitored_products.telegram_user_id"],
            name="fk_product_price_observations_product_owner",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_product_price_observations")),
    )
    op.create_index(
        "ix_product_price_observations_owner_product_time",
        "product_price_observations",
        ["telegram_user_id", "product_id", "observed_at"],
    )
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.product_price_observations FROM PUBLIC, anon, authenticated, service_role")
    op.execute("GRANT SELECT, INSERT ON TABLE public.product_price_observations TO argos_runtime")


def downgrade():
    if context.is_offline_mode():
        raise RuntimeError("Downgrade exige inspeção online para preservar observações.")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM product_price_observations)")):
        raise RuntimeError("Observações existentes; downgrade destrutivo recusado.")
    op.execute("REVOKE ALL PRIVILEGES ON TABLE public.product_price_observations FROM argos_runtime")
    op.drop_index("ix_product_price_observations_owner_product_time", table_name="product_price_observations")
    op.drop_table("product_price_observations")
    op.drop_constraint("uq_monitored_products_id_owner", "monitored_products", type_="unique")
