"""widen timeline event type constraint

Revision ID: 029_timeline_event_types
Revises: 028_notifications
Create Date: 2026-06-12
"""

from alembic import op


revision = "029_timeline_event_types"
down_revision = "028_notifications"
branch_labels = None
depends_on = None


EVENT_TYPES = (
    "'milestone', 'decision', 'learning', 'achievement', 'progress', "
    "'launch', 'strategy_change', 'customer', 'major_milestone'"
)
LEGACY_EVENT_TYPES = "'milestone', 'decision', 'learning', 'achievement', 'progress'"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE timeline_events DROP CONSTRAINT IF EXISTS ck_timeline_events_type")
        op.execute(
            f"ALTER TABLE timeline_events ADD CONSTRAINT ck_timeline_events_type CHECK (event_type IN ({EVENT_TYPES}))"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE timeline_events DROP CONSTRAINT IF EXISTS ck_timeline_events_type")
        op.execute(
            f"ALTER TABLE timeline_events ADD CONSTRAINT ck_timeline_events_type CHECK (event_type IN ({LEGACY_EVENT_TYPES}))"
        )
