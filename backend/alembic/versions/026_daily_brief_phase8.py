"""daily brief phase 8

Revision ID: 026
Revises: 025
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import JSONB, UUID


revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "daily_brief_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("context_snapshot_id", UUID(as_uuid=True), sa.ForeignKey("context_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("brief_date", sa.Date(), nullable=False),
        sa.Column("what_matters_today", JSONB(), nullable=False, server_default="[]"),
        sa.Column("open_loops", JSONB(), nullable=False, server_default="[]"),
        sa.Column("recommended_next_step", JSONB(), nullable=False, server_default="{}"),
        sa.Column("recent_progress", JSONB(), nullable=False, server_default="[]"),
        sa.Column("context_to_remember", JSONB(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "brief_date", name="uq_daily_brief_snapshots_user_date"),
    )
    op.create_index("ix_daily_brief_snapshots_user_id", "daily_brief_snapshots", ["user_id"])
    op.create_index("ix_daily_brief_snapshots_context_snapshot_id", "daily_brief_snapshots", ["context_snapshot_id"])
    op.create_index("ix_daily_brief_snapshots_brief_date", "daily_brief_snapshots", ["brief_date"])


def downgrade() -> None:
    op.drop_index("ix_daily_brief_snapshots_brief_date", table_name="daily_brief_snapshots")
    op.drop_index("ix_daily_brief_snapshots_context_snapshot_id", table_name="daily_brief_snapshots")
    op.drop_index("ix_daily_brief_snapshots_user_id", table_name="daily_brief_snapshots")
    op.drop_table("daily_brief_snapshots")
