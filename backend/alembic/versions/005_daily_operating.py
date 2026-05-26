"""Daily operating — morning/evening summary kinds.

Revision ID: 005
Revises: 004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "daily_summaries",
        sa.Column("summary_kind", sa.String(20), server_default="morning", nullable=False),
    )
    op.drop_constraint("uq_daily_summaries_user_date", "daily_summaries", type_="unique")
    op.create_unique_constraint(
        "uq_daily_summaries_user_date_kind",
        "daily_summaries",
        ["user_id", "summary_date", "summary_kind"],
    )
    op.create_index("ix_daily_summaries_kind", "daily_summaries", ["summary_kind"])


def downgrade() -> None:
    op.drop_index("ix_daily_summaries_kind", table_name="daily_summaries")
    op.drop_constraint("uq_daily_summaries_user_date_kind", "daily_summaries", type_="unique")
    op.create_unique_constraint(
        "uq_daily_summaries_user_date",
        "daily_summaries",
        ["user_id", "summary_date"],
    )
    op.drop_column("daily_summaries", "summary_kind")
