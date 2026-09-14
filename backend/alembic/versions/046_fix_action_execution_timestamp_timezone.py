"""fix action execution lifecycle timestamp timezone

Revision ID: 046_fix_action_execution_timestamp_timezone
Revises: 045_action_execution_lifecycle
"""

from alembic import op
import sqlalchemy as sa


revision = "046_fix_action_execution_timestamp_timezone"
down_revision = "045_action_execution_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    for column in ("started_at", "completed_at", "failed_at", "cancelled_at"):
        op.alter_column(
            "action_executions",
            column,
            existing_type=sa.DateTime(timezone=False),
            type_=sa.DateTime(timezone=True),
            existing_nullable=True,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return

    for column in ("cancelled_at", "failed_at", "completed_at", "started_at"):
        op.alter_column(
            "action_executions",
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(timezone=False),
            existing_nullable=True,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )