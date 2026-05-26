-- Memory extraction and semantic retrieval foundation.
-- Apply after 003_conversation_persistence.sql.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

INSERT INTO schema_migrations (version)
VALUES ('004_memory_retrieval_foundation')
ON CONFLICT (version) DO NOTHING;

ALTER TABLE memories
  ADD COLUMN IF NOT EXISTS summary TEXT,
  ADD COLUMN IF NOT EXISTS importance_score REAL NOT NULL DEFAULT 0.5,
  ADD COLUMN IF NOT EXISTS recency_score REAL NOT NULL DEFAULT 1.0,
  ADD COLUMN IF NOT EXISTS retrieval_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64),
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE memories
  ALTER COLUMN memory_type TYPE VARCHAR(50),
  ALTER COLUMN metadata TYPE JSONB USING metadata::jsonb,
  ALTER COLUMN metadata SET DEFAULT '{}'::jsonb;

UPDATE memories
SET importance_score = importance
WHERE EXISTS (
  SELECT 1
  FROM information_schema.columns
  WHERE table_name = 'memories'
    AND column_name = 'importance'
)
AND importance_score = 0.5;

UPDATE memories
SET retrieval_count = access_count
WHERE EXISTS (
  SELECT 1
  FROM information_schema.columns
  WHERE table_name = 'memories'
    AND column_name = 'access_count'
)
AND retrieval_count = 0;

UPDATE memories
SET memory_type = category
WHERE category IN ('identity', 'goals', 'preferences', 'projects', 'routines', 'work', 'decisions', 'priorities')
  AND memory_type IN ('short_term', 'long_term', 'project');

ALTER TABLE embeddings
  ADD COLUMN IF NOT EXISTS provider_name VARCHAR(50) NOT NULL DEFAULT 'openai',
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE embeddings
  ALTER COLUMN metadata TYPE JSONB USING metadata::jsonb,
  ALTER COLUMN metadata SET DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS ix_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS ix_memories_memory_type ON memories(memory_type);
CREATE INDEX IF NOT EXISTS ix_memories_project_id ON memories(project_id);
CREATE INDEX IF NOT EXISTS ix_memories_importance_score ON memories(importance_score);
CREATE INDEX IF NOT EXISTS ix_memories_user_type_project ON memories(user_id, memory_type, project_id);
CREATE INDEX IF NOT EXISTS ix_memories_content_hash ON memories(user_id, content_hash);

CREATE INDEX IF NOT EXISTS ix_embeddings_source ON embeddings(source_type, source_id);
CREATE INDEX IF NOT EXISTS ix_embeddings_provider_name ON embeddings(provider_name);

CREATE INDEX IF NOT EXISTS ix_embeddings_vector_cosine
  ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
