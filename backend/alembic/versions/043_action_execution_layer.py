"""add durable AI action execution

Revision ID: 043_action_execution
Revises: 042_teams_notion
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "043_action_execution"
down_revision = "042_teams_notion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "action_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="SET NULL")),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL")),
        sa.Column("action_type", sa.String(60), nullable=False), sa.Column("title", sa.String(300), nullable=False),
        sa.Column("request", sa.Text(), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0"), sa.Column("output", sa.Text()), sa.Column("error", sa.Text()),
        sa.Column("dedupe_key", sa.String(180), nullable=False), sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_action_execution_user_dedupe"),
    )
    for column in ("user_id", "conversation_id", "project_id", "action_type", "status"):
        op.create_index(f"ix_action_executions_{column}", "action_executions", [column])


def downgrade() -> None:
    op.drop_table("action_executions")
