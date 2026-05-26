"""Infrastructure foundation — profiles, context, summaries, AI audit, indexes.

Revision ID: 003
Revises: 002
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- User onboarding ---
    op.add_column("users", sa.Column("onboarding_state", sa.String(50), server_default="new"))
    op.add_column("users", sa.Column("timezone", sa.String(64), server_default="UTC"))
    op.create_index("ix_users_onboarding_state", "users", ["onboarding_state"])

    # Align preferences column type
    op.alter_column(
        "users",
        "preferences",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(),
        postgresql_using="preferences::jsonb",
    )

    # --- User profiles ---
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("goals", postgresql.JSONB(), server_default="[]"),
        sa.Column("work_preferences", postgresql.JSONB(), server_default="{}"),
        sa.Column("communication_preferences", postgresql.JSONB(), server_default="{}"),
        sa.Column("routines", postgresql.JSONB(), server_default="{}"),
        sa.Column("personality_metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("productivity_style", sa.String(80)),
        sa.Column("summary", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_user_profiles_user_id", "user_profiles", ["user_id"], unique=True)

    # --- Project context ---
    op.create_table(
        "project_context",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("project_id", sa.UUID(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("context_type", sa.String(50), server_default="summary"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("is_current", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_project_context_project_id", "project_context", ["project_id"])
    op.create_index("ix_project_context_type", "project_context", ["context_type"])
    op.create_index("ix_project_context_is_current", "project_context", ["is_current"])

    # --- Daily summaries ---
    op.create_table(
        "daily_summaries",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("summary_date", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("completed_work", postgresql.JSONB(), server_default="[]"),
        sa.Column("unfinished_priorities", postgresql.JSONB(), server_default="[]"),
        sa.Column("insights", postgresql.JSONB(), server_default="[]"),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "summary_date", name="uq_daily_summaries_user_date"),
    )
    op.create_index("ix_daily_summaries_user_id", "daily_summaries", ["user_id"])
    op.create_index("ix_daily_summaries_date", "daily_summaries", ["summary_date"])

    # --- AI interactions ---
    op.create_table(
        "ai_interactions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("conversations.id", ondelete="SET NULL")),
        sa.Column("message_id", sa.UUID()),
        sa.Column("interaction_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50)),
        sa.Column("model", sa.String(120)),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("status", sa.String(20), server_default="success"),
        sa.Column("error_message", sa.Text()),
        sa.Column("request_id", sa.String(64)),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_ai_interactions_user_id", "ai_interactions", ["user_id"])
    op.create_index("ix_ai_interactions_conversation_id", "ai_interactions", ["conversation_id"])
    op.create_index("ix_ai_interactions_type", "ai_interactions", ["interaction_type"])
    op.create_index("ix_ai_interactions_status", "ai_interactions", ["status"])
    op.create_index("ix_ai_interactions_request_id", "ai_interactions", ["request_id"])

    # --- Embeddings metadata ---
    op.add_column("embeddings", sa.Column("metadata", postgresql.JSONB(), server_default="{}"))

    # --- Memories enrichment ---
    op.add_column("memories", sa.Column("recency_score", sa.Float(), server_default="1.0"))
    op.add_column("memories", sa.Column("embedding_id", sa.UUID(), sa.ForeignKey("embeddings.id", ondelete="SET NULL")))

    # --- Messages enrichment ---
    op.alter_column(
        "messages",
        "metadata",
        existing_type=sa.JSON(),
        type_=postgresql.JSONB(),
        postgresql_using="metadata::jsonb",
    )
    op.add_column("messages", sa.Column("embedding_id", sa.UUID(), sa.ForeignKey("embeddings.id", ondelete="SET NULL")))
    op.add_column("messages", sa.Column("token_count", sa.Integer()))
    op.add_column("messages", sa.Column("provider", sa.String(50)))
    op.add_column("messages", sa.Column("model", sa.String(120)))

    # FK message_id on ai_interactions after messages exist
    op.create_foreign_key(
        "fk_ai_interactions_message_id",
        "ai_interactions",
        "messages",
        ["message_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- Performance indexes ---
    op.create_index("ix_conversations_project_id", "conversations", ["project_id"])
    op.create_index("ix_conversations_deleted_at", "conversations", ["deleted_at"])
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_tasks_user_id", "tasks", ["user_id"])
    op.create_index("ix_tasks_project_id", "tasks", ["project_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_priority", "tasks", ["priority"])
    op.create_index("ix_notes_user_id", "notes", ["user_id"])
    op.create_index("ix_notes_project_id", "notes", ["project_id"])
    op.create_index("ix_memories_category", "memories", ["category"])
    op.create_index("ix_memories_memory_type", "memories", ["memory_type"])
    op.create_index("ix_memories_deleted_at", "memories", ["deleted_at"])
    op.create_index("ix_embeddings_user_id", "embeddings", ["user_id"])
    op.create_index("ix_embeddings_source_type", "embeddings", ["source_type"])
    op.create_index("ix_embeddings_source_id", "embeddings", ["source_id"])
    op.create_index(
        "ix_embeddings_source_lookup",
        "embeddings",
        ["user_id", "source_type", "source_id"],
    )

    # pgvector HNSW index for semantic search (cosine distance)
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_embeddings_embedding_hnsw
        ON embeddings USING hnsw (embedding vector_cosine_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_embeddings_embedding_hnsw")

    op.drop_index("ix_conversations_project_id", table_name="conversations")
    op.drop_index("ix_conversations_deleted_at", table_name="conversations")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_tasks_user_id", table_name="tasks")
    op.drop_index("ix_tasks_project_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_notes_user_id", table_name="notes")
    op.drop_index("ix_notes_project_id", table_name="notes")
    op.drop_index("ix_memories_category", table_name="memories")
    op.drop_index("ix_memories_memory_type", table_name="memories")
    op.drop_index("ix_memories_deleted_at", table_name="memories")
    op.drop_index("ix_embeddings_user_id", table_name="embeddings")
    op.drop_index("ix_embeddings_source_type", table_name="embeddings")
    op.drop_index("ix_embeddings_source_id", table_name="embeddings")
    op.drop_index("ix_embeddings_source_lookup", table_name="embeddings")

    op.drop_constraint("fk_ai_interactions_message_id", "ai_interactions", type_="foreignkey")
    op.drop_column("messages", "model")
    op.drop_column("messages", "provider")
    op.drop_column("messages", "token_count")
    op.drop_column("messages", "embedding_id")
    op.drop_column("memories", "embedding_id")
    op.drop_column("memories", "recency_score")
    op.drop_column("embeddings", "metadata")

    op.drop_table("ai_interactions")
    op.drop_table("daily_summaries")
    op.drop_table("project_context")
    op.drop_table("user_profiles")

    op.drop_index("ix_users_onboarding_state", table_name="users")
    op.drop_column("users", "timezone")
    op.drop_column("users", "onboarding_state")
