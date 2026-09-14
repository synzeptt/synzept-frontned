"""Link workspace activity rows to the real action execution lifecycle.

Revision ID: 044_execution_linked_activity
Revises: 043_action_execution
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision = "044_execution_linked_activity"
down_revision = "043_action_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspace_activities", sa.Column("execution_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "fk_workspace_activities_execution_id",
        "workspace_activities",
        "action_executions",
        ["execution_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_workspace_activities_execution_id", "workspace_activities", ["execution_id"])


def downgrade() -> None:
    op.drop_index("ix_workspace_activities_execution_id", table_name="workspace_activities")
    op.drop_constraint("fk_workspace_activities_execution_id", "workspace_activities", type_="foreignkey")
    op.drop_column("workspace_activities", "execution_id")
