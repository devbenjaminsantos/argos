"""Versão opaca para proteger rascunhos de updates obsoletos."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260913_06"
down_revision = "20260912_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("telegram_conversation_drafts", sa.Column(
        "version", UUID(as_uuid=True), nullable=False,
        server_default=sa.text("gen_random_uuid()"),
    ))


def downgrade() -> None:
    op.drop_column("telegram_conversation_drafts", "version")
