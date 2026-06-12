"""User-controlled V2 understanding rows.

Revision ID: 011
Revises: 010
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_understanding",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("source IN ('user', 'learned')", name="ck_user_understanding_source"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_understanding_user_id", "user_understanding", ["user_id"])
    op.create_index("ix_user_understanding_category", "user_understanding", ["category"])
    op.create_index("ix_user_understanding_source", "user_understanding", ["source"])


def downgrade() -> None:
    op.drop_index("ix_user_understanding_source", table_name="user_understanding")
    op.drop_index("ix_user_understanding_category", table_name="user_understanding")
    op.drop_index("ix_user_understanding_user_id", table_name="user_understanding")
    op.drop_table("user_understanding")
