"""extend user understanding for personal operating system

Revision ID: 036_personal_os
Revises: 035_memory_trust_system
Create Date: 2026-06-17 00:00:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "036_personal_os"
down_revision = "035_memory_trust_system"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.user_understanding ADD COLUMN IF NOT EXISTS current_mission JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE public.user_understanding ADD COLUMN IF NOT EXISTS current_focus JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE public.user_understanding ADD COLUMN IF NOT EXISTS active_projects JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE public.user_understanding ADD COLUMN IF NOT EXISTS open_loops JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE public.user_understanding ADD COLUMN IF NOT EXISTS recent_progress JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE public.user_understanding ADD COLUMN IF NOT EXISTS recent_decisions JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE public.user_understanding ADD COLUMN IF NOT EXISTS next_suggested_actions JSONB NOT NULL DEFAULT '{}'::jsonb")


def downgrade() -> None:
    op.execute("ALTER TABLE public.user_understanding DROP COLUMN IF EXISTS next_suggested_actions")
    op.execute("ALTER TABLE public.user_understanding DROP COLUMN IF EXISTS recent_decisions")
    op.execute("ALTER TABLE public.user_understanding DROP COLUMN IF EXISTS recent_progress")
    op.execute("ALTER TABLE public.user_understanding DROP COLUMN IF EXISTS open_loops")
    op.execute("ALTER TABLE public.user_understanding DROP COLUMN IF EXISTS active_projects")
    op.execute("ALTER TABLE public.user_understanding DROP COLUMN IF EXISTS current_focus")
    op.execute("ALTER TABLE public.user_understanding DROP COLUMN IF EXISTS current_mission")
