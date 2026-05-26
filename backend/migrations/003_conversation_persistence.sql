-- Conversation and chat persistence contract.
-- Apply after 002_align_v1_models.sql. Statements are idempotent for local/prod upgrades.

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

INSERT INTO schema_migrations (version)
VALUES ('003_conversation_persistence')
ON CONFLICT (version) DO NOTHING;

ALTER TABLE conversations
  ADD COLUMN IF NOT EXISTS conversation_type VARCHAR(50) NOT NULL DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS ix_conversations_project_id ON conversations(project_id);
CREATE INDEX IF NOT EXISTS ix_conversations_updated_at ON conversations(updated_at);
CREATE INDEX IF NOT EXISTS ix_conversations_archived_at ON conversations(archived_at);
CREATE INDEX IF NOT EXISTS ix_conversations_conversation_type ON conversations(conversation_type);

ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS token_count INTEGER,
  ADD COLUMN IF NOT EXISTS provider_name VARCHAR(50),
  ADD COLUMN IF NOT EXISTS model_name VARCHAR(120),
  ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE messages
  ALTER COLUMN metadata TYPE JSONB USING metadata::jsonb,
  ALTER COLUMN metadata SET DEFAULT '{}'::jsonb;

UPDATE messages
SET metadata = '{}'::jsonb
WHERE metadata IS NULL;

ALTER TABLE messages
  ALTER COLUMN metadata SET NOT NULL;

UPDATE messages
SET provider_name = provider
WHERE provider_name IS NULL
  AND provider IS NOT NULL;

UPDATE messages
SET model_name = model
WHERE model_name IS NULL
  AND model IS NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_messages_role') THEN
    ALTER TABLE messages
      ADD CONSTRAINT ck_messages_role CHECK (role IN ('user', 'assistant', 'system'));
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS ix_messages_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS ix_messages_conversation_created_at ON messages(conversation_id, created_at);
