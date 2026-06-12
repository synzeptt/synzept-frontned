"""Project intelligence, decisions, and open loops.

Revision ID: 013
Revises: 012
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_intelligence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("current_focus", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("recommended_next_step", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'paused', 'completed')", name="ck_project_intelligence_status"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_project_intelligence_project_id"),
    )
    op.create_index("ix_project_intelligence_project_id", "project_intelligence", ["project_id"])
    op.create_index("ix_project_intelligence_status", "project_intelligence", ["status"])

    op.create_table(
        "project_decisions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_project_decisions_status"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_decisions_project_id", "project_decisions", ["project_id"])
    op.create_index("ix_project_decisions_status", "project_decisions", ["status"])

    op.create_table(
        "project_open_loops",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("loop", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('open', 'closed')", name="ck_project_open_loops_status"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_open_loops_project_id", "project_open_loops", ["project_id"])
    op.create_index("ix_project_open_loops_status", "project_open_loops", ["status"])


def downgrade() -> None:
    op.drop_index("ix_project_open_loops_status", table_name="project_open_loops")
    op.drop_index("ix_project_open_loops_project_id", table_name="project_open_loops")
    op.drop_table("project_open_loops")
    op.drop_index("ix_project_decisions_status", table_name="project_decisions")
    op.drop_index("ix_project_decisions_project_id", table_name="project_decisions")
    op.drop_table("project_decisions")
    op.drop_index("ix_project_intelligence_status", table_name="project_intelligence")
    op.drop_index("ix_project_intelligence_project_id", table_name="project_intelligence")
    op.drop_table("project_intelligence")
