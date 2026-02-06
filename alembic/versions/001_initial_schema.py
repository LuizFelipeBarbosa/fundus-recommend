"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("url", sa.Text, unique=True, nullable=False),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("authors", sa.ARRAY(sa.Text), server_default="{}"),
        sa.Column("topics", sa.ARRAY(sa.Text), server_default="{}"),
        sa.Column("publisher", sa.String(255), nullable=False),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("publishing_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("crawled_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("cover_image_url", sa.Text, nullable=True),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("dedup_cluster_id", sa.Integer, nullable=True),
    )

    op.create_index("ix_articles_topics", "articles", ["topics"], postgresql_using="gin")
    op.create_index("ix_articles_publishing_date", "articles", ["publishing_date"])
    op.create_index("ix_articles_publisher", "articles", ["publisher"])
    op.create_index("ix_articles_language", "articles", ["language"])

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.UniqueConstraint("user_id", "topic", name="uq_user_topic"),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_table("users")
    op.drop_table("articles")
    op.execute("DROP EXTENSION IF EXISTS vector")
