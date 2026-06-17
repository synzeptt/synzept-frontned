"""chief of staff phase 12

Revision ID: 033_chief_of_staff_phase12
Revises: 032_relationship_context_graph
Create Date: 2026-06-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.database.types import JSONB, UUID


revision: str = "033_chief_of_staff_phase12"
down_revision: Union[str, tuple[str, str]] = "032_relationship_context_graph"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chief_of_staff_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("snapshot_type", sa.String(length=40), nullable=False, server_default="daily"),
        sa.Column("executive_brief", JSONB(), nullable=False, server_default="{}"),
        sa.Column("opportunities", JSONB(), nullable=False, server_default="[]"),
        sa.Column("risks", JSONB(), nullable=False, server_default="[]"),
        sa.Column("priorities", JSONB(), nullable=False, server_default="[]"),
        sa.Column("strategic_suggestions", JSONB(), nullable=False, server_default="[]"),
        sa.Column("momentum", JSONB(), nullable=False, server_default="{}"),
        sa.Column("founder_report", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "snapshot_date", "snapshot_type", name="uq_chief_of_staff_snapshot"),
    )
    op.create_index("ix_chief_of_staff_snapshots_user_id", "chief_of_staff_snapshots", ["user_id"])
    op.create_index("ix_chief_of_staff_snapshots_snapshot_date", "chief_of_staff_snapshots", ["snapshot_date"])
    op.create_index("ix_chief_of_staff_snapshots_snapshot_type", "chief_of_staff_snapshots", ["snapshot_type"])

    op.create_table(
        "commitments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False, server_default="conversation"),
        sa.Column("source_id", UUID(as_uuid=True), nullable=True),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        sa.Column("goal_id", UUID(as_uuid=True), sa.ForeignKey("goals.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="open"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence", JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for column in ("user_id", "source_type", "source_id", "project_id", "goal_id", "status", "due_at"):
        op.create_index(f"ix_commitments_{column}", "commitments", [column])


def downgrade() -> None:
    for column in ("due_at", "status", "goal_id", "project_id", "source_id", "source_type", "user_id"):
        op.drop_index(f"ix_commitments_{column}", table_name="commitments")
    op.drop_table("commitments")
    op.drop_index("ix_chief_of_staff_snapshots_snapshot_type", table_name="chief_of_staff_snapshots")
    op.drop_index("ix_chief_of_staff_snapshots_snapshot_date", table_name="chief_of_staff_snapshots")
    op.drop_index("ix_chief_of_staff_snapshots_user_id", table_name="chief_of_staff_snapshots")
    op.drop_table("chief_of_staff_snapshots")
