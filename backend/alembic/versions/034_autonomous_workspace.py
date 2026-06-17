"""autonomous workspace execution

Revision ID: 034_autonomous_workspace
Revises: 033_chief_of_staff_phase12
Create Date: 2026-06-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.database.types import JSONB, UUID


revision: str = "034_autonomous_workspace"
down_revision: Union[str, tuple[str, str]] = "033_chief_of_staff_phase12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "execution_plans",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goal_id", UUID(as_uuid=True), sa.ForeignKey("goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("plan", JSONB(), nullable=False, server_default="{}"),
        sa.Column("planned", JSONB(), nullable=False, server_default="[]"),
        sa.Column("completed", JSONB(), nullable=False, server_default="[]"),
        sa.Column("blocked", JSONB(), nullable=False, server_default="[]"),
        sa.Column("metrics", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "goal_id", name="uq_execution_plans_goal"),
    )
    for column in ("user_id", "goal_id", "project_id", "status"):
        op.create_index(f"ix_execution_plans_{column}", "execution_plans", [column])

    op.create_table(
        "autonomous_suggestions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("goal_id", UUID(as_uuid=True), sa.ForeignKey("goals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("suggestion_type", sa.String(length=60), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("evidence", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "project_id", "goal_id", "suggestion_type", "priority", "status"):
        op.create_index(f"ix_autonomous_suggestions_{column}", "autonomous_suggestions", [column])


def downgrade() -> None:
    for column in ("status", "priority", "suggestion_type", "goal_id", "project_id", "user_id"):
        op.drop_index(f"ix_autonomous_suggestions_{column}", table_name="autonomous_suggestions")
    op.drop_table("autonomous_suggestions")
    for column in ("status", "project_id", "goal_id", "user_id"):
        op.drop_index(f"ix_execution_plans_{column}", table_name="execution_plans")
    op.drop_table("execution_plans")
