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
    op.add_column("timeline_events", sa.Column("project_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_timeline_events_project_id_projects",
        "timeline_events",
        "projects",
        ["project_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_timeline_events_project_id", "timeline_events", ["project_id"])
    op.create_check_constraint(
        "ck_timeline_events_type",
        "timeline_events",
        "event_type IN ('milestone', 'decision', 'learning', 'achievement', 'progress')",
    )
    op.create_check_constraint("ck_timeline_events_importance", "timeline_events", "importance >= 0 AND importance <= 1")


def downgrade() -> None:
    op.drop_constraint("ck_timeline_events_importance", "timeline_events", type_="check")
    op.drop_constraint("ck_timeline_events_type", "timeline_events", type_="check")
    op.drop_constraint("fk_timeline_events_project_id_projects", "timeline_events", type_="foreignkey")
    op.drop_index("ix_timeline_events_project_id", table_name="timeline_events")
    op.drop_column("timeline_events", "project_id")
