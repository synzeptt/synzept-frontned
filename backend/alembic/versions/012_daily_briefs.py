"""Persisted V2 daily briefs.

Revision ID: 012
Revises: 011
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_briefs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("brief_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("open_loops", sa.JSON(), nullable=False),
        sa.Column("next_step", sa.Text(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "brief_date", name="uq_daily_briefs_user_date"),
    )
    op.create_index("ix_daily_briefs_user_id", "daily_briefs", ["user_id"])
    op.create_index("ix_daily_briefs_brief_date", "daily_briefs", ["brief_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_briefs_brief_date", table_name="daily_briefs")
    op.drop_index("ix_daily_briefs_user_id", table_name="daily_briefs")
    op.drop_table("daily_briefs")
