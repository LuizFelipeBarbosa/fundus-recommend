"""Add crawl diagnostics tables

Revision ID: 003
Revises: 002
Create Date: 2026-02-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_label", sa.String(64), nullable=False, server_default="crawl"),
        sa.Column("requested_publishers", postgresql.ARRAY(sa.String(255)), nullable=False, server_default="{}"),
        sa.Column("resolved_publishers", postgresql.ARRAY(sa.String(255)), nullable=False, server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("total_publishers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("succeeded_publishers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_publishers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_publishers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_inserted", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
    )
    op.create_index("ix_crawl_runs_started_at", "crawl_runs", ["started_at"])
    op.create_index("ix_crawl_runs_status", "crawl_runs", ["status"])

    op.create_table(
        "crawl_run_publishers",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("crawl_run_id", sa.Integer, sa.ForeignKey("crawl_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("publisher_id", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("adapter", sa.String(50), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("inserted_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("crawled_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status_histogram", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skip_reason", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_crawl_run_publishers_run_id", "crawl_run_publishers", ["crawl_run_id"])
    op.create_index("ix_crawl_run_publishers_publisher_id", "crawl_run_publishers", ["publisher_id"])
    op.create_index("ix_crawl_run_publishers_started_at", "crawl_run_publishers", ["started_at"])


def downgrade() -> None:
    op.drop_table("crawl_run_publishers")
    op.drop_table("crawl_runs")
