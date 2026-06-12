"""timeline phase 3

Revision ID: 021
Revises: 020
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import UUID


revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "timeline_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('milestone', 'decision', 'learning', 'achievement', 'progress', 'launch', 'strategy_change', 'customer', 'major_milestone')",
            name="ck_timeline_events_type",
        ),
        sa.CheckConstraint("importance >= 0 AND importance <= 1", name="ck_timeline_events_importance"),
    )
    op.create_index("ix_timeline_events_user_id", "timeline_events", ["user_id"])
    op.create_index("ix_timeline_events_project_id", "timeline_events", ["project_id"])
    op.create_index("ix_timeline_events_event_type", "timeline_events", ["event_type"])
    op.create_index("ix_timeline_events_event_date", "timeline_events", ["event_date"])


def downgrade() -> None:
    op.drop_index("ix_timeline_events_event_date", table_name="timeline_events")
    op.drop_index("ix_timeline_events_event_type", table_name="timeline_events")
    op.drop_index("ix_timeline_events_project_id", table_name="timeline_events")
    op.drop_index("ix_timeline_events_user_id", table_name="timeline_events")
    op.drop_table("timeline_events")
