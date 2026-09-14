"""add action execution lifecycle timestamps

Revision ID: 045_action_execution_lifecycle
Revises: 044_execution_linked_activity
"""

from alembic import op
import sqlalchemy as sa

revision = "045_action_execution_lifecycle"
down_revision = "044_execution_linked_activity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for column in ("started_at", "completed_at", "failed_at", "cancelled_at"):
        op.add_column("action_executions", sa.Column(column, sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for column in ("cancelled_at", "failed_at", "completed_at", "started_at"):
        op.drop_column("action_executions", column)
