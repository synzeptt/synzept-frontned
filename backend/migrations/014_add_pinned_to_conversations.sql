-- Add pinned column to conversations for conversation pinning support.
-- Apply after 013_core_architecture_foundation_rls.sql. Statements are idempotent.

INSERT INTO schema_migrations (version)
VALUES ('014_add_pinned_to_conversations')
ON CONFLICT (version) DO NOTHING;

ALTER TABLE conversations
  ADD COLUMN IF NOT EXISTS pinned BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_conversations_pinned ON conversations(pinned);
