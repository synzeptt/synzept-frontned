"""repair model/schema drift

Revision ID: 037_conversation_schema_repair
Revises: 036_personal_os, 036_user_understanding_personal_os
Create Date: 2026-07-02
"""

from collections.abc import Sequence

from alembic import op


revision: str = "037_conversation_schema_repair"
down_revision: tuple[str, str] = ("036_personal_os", "036_user_understanding_personal_os")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Conversation columns used by the current chat persistence model.
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS pinned BOOLEAN DEFAULT false")
    op.execute("UPDATE conversations SET pinned = false WHERE pinned IS NULL")
    op.execute("ALTER TABLE conversations ALTER COLUMN pinned SET DEFAULT false")
    op.execute("ALTER TABLE conversations ALTER COLUMN pinned SET NOT NULL")

    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ")
    op.execute("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ")

    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_pinned ON conversations (pinned)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_archived_at ON conversations (archived_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_deleted_at ON conversations (deleted_at)")

    # Memory columns that existed in the legacy SQL migration set but were
    # missing from Alembic.
    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS retrieval_count INTEGER DEFAULT 0")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'memories'
                  AND column_name = 'access_count'
            ) THEN
                EXECUTE 'UPDATE memories SET retrieval_count = access_count WHERE retrieval_count IS NULL';
            END IF;
        END
        $$;
        """
    )
    op.execute("UPDATE memories SET retrieval_count = 0 WHERE retrieval_count IS NULL")
    op.execute("ALTER TABLE memories ALTER COLUMN retrieval_count SET DEFAULT 0")
    op.execute("ALTER TABLE memories ALTER COLUMN retrieval_count SET NOT NULL")

    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS pinned BOOLEAN DEFAULT false")
    op.execute("UPDATE memories SET pinned = false WHERE pinned IS NULL")
    op.execute("ALTER TABLE memories ALTER COLUMN pinned SET DEFAULT false")
    op.execute("ALTER TABLE memories ALTER COLUMN pinned SET NOT NULL")
    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ")

    op.execute("CREATE INDEX IF NOT EXISTS ix_memories_pinned ON memories (pinned)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memories_archived_at ON memories (archived_at)")

    # Additional model/schema drift found while auditing SQLAlchemy metadata
    # against the Alembic chain.
    op.execute("ALTER TABLE embeddings ADD COLUMN IF NOT EXISTS provider_name VARCHAR(50) DEFAULT 'openai'")
    op.execute("UPDATE embeddings SET provider_name = 'openai' WHERE provider_name IS NULL")
    op.execute("ALTER TABLE embeddings ALTER COLUMN provider_name SET DEFAULT 'openai'")
    op.execute("ALTER TABLE embeddings ALTER COLUMN provider_name SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_provider_name ON embeddings (provider_name)")

    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS summary TEXT")
    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS importance_score DOUBLE PRECISION DEFAULT 0.5")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'memories'
                  AND column_name = 'importance'
            ) THEN
                EXECUTE 'UPDATE memories SET importance_score = importance WHERE importance_score IS NULL';
            END IF;
        END
        $$;
        """
    )
    op.execute("UPDATE memories SET importance_score = 0.5 WHERE importance_score IS NULL")
    op.execute("ALTER TABLE memories ALTER COLUMN importance_score SET DEFAULT 0.5")
    op.execute("ALTER TABLE memories ALTER COLUMN importance_score SET NOT NULL")
    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb")
    op.execute("UPDATE memories SET metadata = '{}'::jsonb WHERE metadata IS NULL")
    op.execute("ALTER TABLE memories ALTER COLUMN metadata SET DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE memories ALTER COLUMN metadata SET NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS ix_memories_importance_score ON memories (importance_score)")

    op.execute("ALTER TABLE notes ADD COLUMN IF NOT EXISTS summary TEXT")

    # Remove legacy columns after data has been copied into the current model
    # columns. These are not mapped by SQLAlchemy anymore.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'messages' AND column_name = 'provider'
            ) THEN
                EXECUTE 'UPDATE messages SET provider_name = provider WHERE provider_name IS NULL AND provider IS NOT NULL';
            END IF;
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'messages' AND column_name = 'model'
            ) THEN
                EXECUTE 'UPDATE messages SET model_name = model WHERE model_name IS NULL AND model IS NOT NULL';
            END IF;
        END
        $$;
        """
    )
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS provider")
    op.execute("ALTER TABLE messages DROP COLUMN IF EXISTS model")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS importance")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS access_count")
    op.execute("ALTER TABLE learning_observations DROP CONSTRAINT IF EXISTS uq_learning_observations_source_signal")
    op.execute("DROP INDEX IF EXISTS ix_learning_observations_source_type")
    op.execute("DROP INDEX IF EXISTS ix_learning_observations_source_id")
    op.execute("ALTER TABLE learning_observations DROP COLUMN IF EXISTS source_type")
    op.execute("ALTER TABLE learning_observations DROP COLUMN IF EXISTS source_id")
    op.execute("ALTER TABLE learning_observations DROP COLUMN IF EXISTS signal")

    # Imported model with no Alembic table in the current chain.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS open_loop_actions (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            source VARCHAR(40) NOT NULL,
            source_id VARCHAR(80) NOT NULL,
            status VARCHAR(20) NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_open_loop_actions_source'
            ) THEN
                ALTER TABLE open_loop_actions
                ADD CONSTRAINT uq_open_loop_actions_source
                UNIQUE (user_id, source, source_id);
            END IF;
        END
        $$;
        """
    )
    for column in ("user_id", "source", "source_id", "status"):
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_open_loop_actions_{column} ON open_loop_actions ({column})")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS open_loop_actions")
    op.execute("ALTER TABLE notes DROP COLUMN IF EXISTS summary")
    op.execute("DROP INDEX IF EXISTS ix_memories_importance_score")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS importance_score")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS summary")
    op.execute("DROP INDEX IF EXISTS ix_embeddings_provider_name")
    op.execute("ALTER TABLE embeddings DROP COLUMN IF EXISTS provider_name")
    op.execute("DROP INDEX IF EXISTS ix_memories_archived_at")
    op.execute("DROP INDEX IF EXISTS ix_memories_pinned")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS archived_at")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS pinned")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS retrieval_count")
    op.execute("DROP INDEX IF EXISTS ix_conversations_pinned")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS pinned")
