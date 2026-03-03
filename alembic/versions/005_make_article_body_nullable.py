"""Make article body nullable

Revision ID: 005
Revises: 004
Create Date: 2026-02-20 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("articles", "body", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE articles SET body = '' WHERE body IS NULL")
    op.alter_column("articles", "body", existing_type=sa.Text(), nullable=False)
