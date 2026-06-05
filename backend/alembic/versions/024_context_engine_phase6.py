"""context engine phase 6

Revision ID: 024
Revises: 023
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import JSONB, UUID


revision = "024"
down_revision = "023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "context_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("current_focus", JSONB(), nullable=False, server_default="{}"),
        sa.Column("active_themes", JSONB(), nullable=False, server_default="[]"),
        sa.Column("open_loops", JSONB(), nullable=False, server_default="[]"),
        sa.Column("important_context", JSONB(), nullable=False, server_default="[]"),
        sa.Column("recommended_next_step", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_context_snapshots_user_id", "context_snapshots", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_context_snapshots_user_id", table_name="context_snapshots")
    op.drop_table("context_snapshots")
