"""project intelligence phase 2

Revision ID: 020
Revises: 019
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

from app.database.types import UUID


revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("current_focus", sa.Text(), nullable=False, server_default=""))
    op.add_column("projects", sa.Column("recommended_next_step", sa.Text(), nullable=False, server_default=""))

    op.create_table(
        "open_loops",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('open', 'completed', 'archived')", name="ck_open_loops_status"),
    )
    op.create_index("ix_open_loops_project_id", "open_loops", ["project_id"])
    op.create_index("ix_open_loops_status", "open_loops", ["status"])

    op.create_table(
        "decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'decided')", name="ck_decisions_status"),
    )
    op.create_index("ix_decisions_project_id", "decisions", ["project_id"])
    op.create_index("ix_decisions_status", "decisions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_decisions_status", table_name="decisions")
    op.drop_index("ix_decisions_project_id", table_name="decisions")
    op.drop_table("decisions")
    op.drop_index("ix_open_loops_status", table_name="open_loops")
    op.drop_index("ix_open_loops_project_id", table_name="open_loops")
    op.drop_table("open_loops")
    op.drop_column("projects", "recommended_next_step")
    op.drop_column("projects", "current_focus")
