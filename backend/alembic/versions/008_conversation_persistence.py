"""Conversation persistence contract.

Revision ID: 008
Revises: 007
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("conversation_type", sa.String(50), server_default="general", nullable=False),
    )
    op.add_column("conversations", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    op.create_index("ix_conversations_archived_at", "conversations", ["archived_at"])
    op.create_index("ix_conversations_conversation_type", "conversations", ["conversation_type"])

    op.add_column("messages", sa.Column("provider_name", sa.String(50), nullable=True))
    op.add_column("messages", sa.Column("model_name", sa.String(120), nullable=True))
    op.execute("UPDATE messages SET provider_name = provider WHERE provider_name IS NULL AND provider IS NOT NULL")
    op.execute("UPDATE messages SET model_name = model WHERE model_name IS NULL AND model IS NOT NULL")
    op.create_index("ix_messages_created_at", "messages", ["created_at"])
    op.create_index("ix_messages_conversation_created_at", "messages", ["conversation_id", "created_at"])
    op.create_check_constraint("ck_messages_role", "messages", "role IN ('user', 'assistant', 'system')")


def downgrade() -> None:
    op.drop_constraint("ck_messages_role", "messages", type_="check")
    op.drop_index("ix_messages_conversation_created_at", table_name="messages")
    op.drop_index("ix_messages_created_at", table_name="messages")
    op.drop_column("messages", "model_name")
    op.drop_column("messages", "provider_name")

    op.drop_index("ix_conversations_conversation_type", table_name="conversations")
    op.drop_index("ix_conversations_archived_at", table_name="conversations")
    op.drop_index("ix_conversations_updated_at", table_name="conversations")
    op.drop_column("conversations", "archived_at")
    op.drop_column("conversations", "conversation_type")
