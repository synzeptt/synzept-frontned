"""Memory intelligence fields

Revision ID: 002
Revises: 001
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("memories", sa.Column("content_hash", sa.String(64), nullable=True))
    op.create_index("ix_memories_content_hash", "memories", ["content_hash"])
    op.add_column("conversations", sa.Column("active_intent", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("conversations", "active_intent")
    op.drop_index("ix_memories_content_hash", table_name="memories")
    op.drop_column("memories", "content_hash")
