"""Add article_views table

Revision ID: 002
Revises: 001
Create Date: 2026-02-06 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "article_views",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("article_id", sa.Integer, sa.ForeignKey("articles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_article_views_article_id", "article_views", ["article_id"])
    op.create_index("ix_article_views_viewed_at", "article_views", ["viewed_at"])


def downgrade() -> None:
    op.drop_table("article_views")
