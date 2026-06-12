"""Approval-first learning engine.

Revision ID: 014
Revises: 013
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_understanding", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("user_understanding", sa.Column("learned_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "learning_observations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("signal", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "source_type", "source_id", "signal", name="uq_learning_observations_source_signal"),
    )
    op.create_index("ix_learning_observations_user_id", "learning_observations", ["user_id"])
    op.create_index("ix_learning_observations_source_type", "learning_observations", ["source_type"])
    op.create_index("ix_learning_observations_source_id", "learning_observations", ["source_id"])

    op.create_table(
        "learning_suggestions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'accepted', 'ignored', 'edited')", name="ck_learning_suggestions_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_suggestions_user_id", "learning_suggestions", ["user_id"])
    op.create_index("ix_learning_suggestions_status", "learning_suggestions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_learning_suggestions_status", table_name="learning_suggestions")
    op.drop_index("ix_learning_suggestions_user_id", table_name="learning_suggestions")
    op.drop_table("learning_suggestions")
    op.drop_index("ix_learning_observations_source_id", table_name="learning_observations")
    op.drop_index("ix_learning_observations_source_type", table_name="learning_observations")
    op.drop_index("ix_learning_observations_user_id", table_name="learning_observations")
    op.drop_table("learning_observations")
    op.drop_column("user_understanding", "learned_at")
    op.drop_column("user_understanding", "confidence")
