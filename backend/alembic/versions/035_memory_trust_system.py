"""memory trust system

Revision ID: 035_memory_trust_system
Revises: 034_autonomous_workspace
Create Date: 2026-06-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.database.types import JSONB, UUID

revision: str = "035_memory_trust_system"
down_revision: str | None = "034_autonomous_workspace"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_trust_events",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("memory_id", UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("caused_by_type", sa.String(length=40), nullable=False, server_default="system"),
        sa.Column("caused_by_id", UUID(as_uuid=True), nullable=True),
        sa.Column("before", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("after", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("metadata", JSONB(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["memory_id"], ["memories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("memory_id", "user_id", "action", "caused_by_type", "caused_by_id"):
        op.create_index(f"ix_memory_trust_events_{column}", "memory_trust_events", [column])


def downgrade() -> None:
    op.drop_table("memory_trust_events")
