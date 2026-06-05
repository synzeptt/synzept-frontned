"""continuity assistant phase 7

Revision ID: 025
Revises: 024
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import JSONB, UUID


revision = "025"
down_revision = "024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "continuity_assistant_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("context_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("context_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("what_changed", JSONB(), nullable=False, server_default="[]"),
        sa.Column("what_matters", JSONB(), nullable=False, server_default="[]"),
        sa.Column("open_loops", JSONB(), nullable=False, server_default="[]"),
        sa.Column("recent_progress", JSONB(), nullable=False, server_default="[]"),
        sa.Column("recommended_next_step", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_continuity_assistant_snapshots_user_id", "continuity_assistant_snapshots", ["user_id"])
    op.create_index("ix_continuity_assistant_snapshots_context_snapshot_id", "continuity_assistant_snapshots", ["context_snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_continuity_assistant_snapshots_context_snapshot_id", table_name="continuity_assistant_snapshots")
    op.drop_index("ix_continuity_assistant_snapshots_user_id", table_name="continuity_assistant_snapshots")
    op.drop_table("continuity_assistant_snapshots")
