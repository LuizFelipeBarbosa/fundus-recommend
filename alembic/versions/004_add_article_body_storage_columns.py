"""Add article body storage columns

Revision ID: 004
Revises: 003
Create Date: 2026-02-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("articles", sa.Column("body_snippet", sa.Text(), nullable=False, server_default=""))
    op.add_column("articles", sa.Column("body_storage_key", sa.Text(), nullable=True))
    op.add_column(
        "articles",
        sa.Column("body_storage_provider", sa.String(length=16), nullable=False, server_default="db"),
    )

    op.execute("UPDATE articles SET body_snippet = LEFT(COALESCE(body, ''), 1000) WHERE body_snippet = ''")


def downgrade() -> None:
    op.drop_column("articles", "body_storage_provider")
    op.drop_column("articles", "body_storage_key")
    op.drop_column("articles", "body_snippet")
