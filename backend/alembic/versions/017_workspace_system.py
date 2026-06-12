"""Unified workspace relationships and activity ledger.

Revision ID: 017
Revises: 016
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notes", sa.Column("goal_id", sa.UUID(), nullable=True))
    op.add_column("notes", sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
    op.create_foreign_key("fk_notes_goal_id", "notes", "goals", ["goal_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_notes_goal_id", "notes", ["goal_id"])
    op.create_table(
        "workspace_activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("goal_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("note_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "project_id", "goal_id", "task_id", "note_id", "action", "created_at"):
        op.create_index(f"ix_workspace_activities_{column}", "workspace_activities", [column])


def downgrade() -> None:
    for column in ("created_at", "action", "note_id", "task_id", "goal_id", "project_id", "user_id"):
        op.drop_index(f"ix_workspace_activities_{column}", table_name="workspace_activities")
    op.drop_table("workspace_activities")
    op.drop_index("ix_notes_goal_id", table_name="notes")
    op.drop_constraint("fk_notes_goal_id", "notes", type_="foreignkey")
    op.drop_column("notes", "tags")
    op.drop_column("notes", "goal_id")
