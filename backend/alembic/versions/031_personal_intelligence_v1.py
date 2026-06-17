"""personal intelligence v1 continuity fields

Revision ID: 031_personal_intelligence_v1
Revises: 030_merge_v2_core_and_launch
Create Date: 2026-06-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.database.types import JSONB


revision: str = "031_personal_intelligence_v1"
down_revision: Union[str, tuple[str, str]] = "030_merge_v2_core_and_launch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column in (
        "current_mission",
        "active_projects",
        "open_loops",
        "recent_progress",
        "recent_decisions",
        "next_suggested_actions",
    ):
        op.add_column("user_understanding", sa.Column(column, JSONB(), nullable=False, server_default=sa.text("'{}'")))
    op.add_column("decisions", sa.Column("reason", sa.Text(), nullable=False, server_default=""))
    op.add_column("decisions", sa.Column("outcome", sa.Text(), nullable=False, server_default=""))
    op.add_column("decisions", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("decisions", "decided_at")
    op.drop_column("decisions", "outcome")
    op.drop_column("decisions", "reason")
    for column in (
        "next_suggested_actions",
        "recent_decisions",
        "recent_progress",
        "open_loops",
        "active_projects",
        "current_mission",
    ):
        op.drop_column("user_understanding", column)
