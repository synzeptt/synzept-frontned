"""Goals, milestones, and task progress hierarchy.

Revision ID: 016
Revises: 015
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "goals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'completed', 'paused')", name="ck_goals_status"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_goals_user_id", "goals", ["user_id"])
    op.create_index("ix_goals_project_id", "goals", ["project_id"])
    op.create_index("ix_goals_status", "goals", ["status"])
    op.create_index("ix_goals_deleted_at", "goals", ["deleted_at"])

    op.create_table(
        "milestones",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("goal_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress", sa.Float(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('pending', 'in_progress', 'completed')", name="ck_milestones_status"),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_milestones_goal_id", "milestones", ["goal_id"])
    op.create_index("ix_milestones_status", "milestones", ["status"])
    op.create_index("ix_milestones_deleted_at", "milestones", ["deleted_at"])

    op.add_column("tasks", sa.Column("milestone_id", sa.UUID(), nullable=True))
    op.create_foreign_key("fk_tasks_milestone_id", "tasks", "milestones", ["milestone_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_tasks_milestone_id", "tasks", ["milestone_id"])


def downgrade() -> None:
    op.drop_index("ix_tasks_milestone_id", table_name="tasks")
    op.drop_constraint("fk_tasks_milestone_id", "tasks", type_="foreignkey")
    op.drop_column("tasks", "milestone_id")
    op.drop_index("ix_milestones_deleted_at", table_name="milestones")
    op.drop_index("ix_milestones_status", table_name="milestones")
    op.drop_index("ix_milestones_goal_id", table_name="milestones")
    op.drop_table("milestones")
    op.drop_index("ix_goals_deleted_at", table_name="goals")
    op.drop_index("ix_goals_status", table_name="goals")
    op.drop_index("ix_goals_project_id", table_name="goals")
    op.drop_index("ix_goals_user_id", table_name="goals")
    op.drop_table("goals")
