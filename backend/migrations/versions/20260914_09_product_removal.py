"""Histórico de produtos removidos e unicidade somente dos ativos."""
from alembic import context, op
import sqlalchemy as sa

revision = "20260914_09"
down_revision = "20260914_08"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("monitored_products", sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True))
    for suffix, column in (("slot", "slot"), ("key", "product_key")):
        name = f"uq_monitored_products_owner_{suffix}"
        op.drop_constraint(name, "monitored_products", type_="unique")
        op.create_index(name, "monitored_products", ["telegram_user_id", column],
                        unique=True, postgresql_where=sa.text("removed_at IS NULL"))
    op.execute("GRANT UPDATE (removed_at) ON TABLE public.monitored_products TO argos_runtime")


def downgrade():
    if context.is_offline_mode():
        raise RuntimeError("Downgrade exige inspeção online para preservar histórico.")
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM monitored_products WHERE removed_at IS NOT NULL)")):
        raise RuntimeError("Histórico de remoção existente; downgrade destrutivo recusado.")
    op.execute("REVOKE UPDATE (removed_at) ON TABLE public.monitored_products FROM argos_runtime")
    for suffix, column in (("slot", "slot"), ("key", "product_key")):
        name = f"uq_monitored_products_owner_{suffix}"
        op.drop_index(name, table_name="monitored_products")
        op.create_unique_constraint(name, "monitored_products", ["telegram_user_id", column])
    op.drop_column("monitored_products", "removed_at")
