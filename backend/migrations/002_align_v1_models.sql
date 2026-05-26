-- Align the database schema with the Synzept V1 SQLAlchemy model surface.
-- Apply after 001_initial.sql. Statements are idempotent for local/prod upgrades.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

INSERT INTO schema_migrations (version)
VALUES ('002_align_v1_models')
ON CONFLICT (version) DO NOTHING;

UPDATE users
SET email = 'local-user@synzept.local'
WHERE id = '00000000-0000-0000-0000-000000000001'
  AND email IS NULL;

UPDATE users
SET email = concat('user-', id::text, '@synzept.local')
WHERE email IS NULL;

ALTER TABLE users
  ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255),
  ADD COLUMN IF NOT EXISTS google_id VARCHAR(255),
  ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(32) DEFAULT 'email',
  ADD COLUMN IF NOT EXISTS onboarding_state VARCHAR(50) DEFAULT 'new',
  ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) DEFAULT 'UTC',
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE users
  ALTER COLUMN email SET NOT NULL,
  ALTER COLUMN auth_provider SET DEFAULT 'email',
  ALTER COLUMN onboarding_state SET DEFAULT 'new',
  ALTER COLUMN timezone SET DEFAULT 'UTC',
  ALTER COLUMN is_active SET DEFAULT true;

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS ix_users_onboarding_state ON users(onboarding_state);
CREATE INDEX IF NOT EXISTS ix_users_deleted_at ON users(deleted_at);

ALTER TABLE conversations
  ADD COLUMN IF NOT EXISTS active_intent VARCHAR(500),
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_conversations_project_id ON conversations(project_id);
CREATE INDEX IF NOT EXISTS ix_conversations_deleted_at ON conversations(deleted_at);

ALTER TABLE messages
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  ADD COLUMN IF NOT EXISTS embedding_id UUID,
  ADD COLUMN IF NOT EXISTS token_count INTEGER,
  ADD COLUMN IF NOT EXISTS provider VARCHAR(50),
  ADD COLUMN IF NOT EXISTS model VARCHAR(120);

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_projects_status ON projects(status);
CREATE INDEX IF NOT EXISTS ix_projects_deleted_at ON projects(deleted_at);

ALTER TABLE notes
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_notes_project_id ON notes(project_id);
CREATE INDEX IF NOT EXISTS ix_notes_deleted_at ON notes(deleted_at);

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_tasks_project_id ON tasks(project_id);
CREATE INDEX IF NOT EXISTS ix_tasks_priority ON tasks(priority);
CREATE INDEX IF NOT EXISTS ix_tasks_deleted_at ON tasks(deleted_at);

ALTER TABLE memories
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64),
  ADD COLUMN IF NOT EXISTS recency_score REAL DEFAULT 1.0,
  ADD COLUMN IF NOT EXISTS embedding_id UUID;

CREATE INDEX IF NOT EXISTS ix_memories_project_id ON memories(project_id);
CREATE INDEX IF NOT EXISTS ix_memories_content_hash ON memories(content_hash);
CREATE INDEX IF NOT EXISTS ix_memories_deleted_at ON memories(deleted_at);

ALTER TABLE embeddings
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  goals JSONB DEFAULT '[]'::jsonb,
  work_preferences JSONB DEFAULT '{}'::jsonb,
  communication_preferences JSONB DEFAULT '{}'::jsonb,
  routines JSONB DEFAULT '{}'::jsonb,
  personality_metadata JSONB DEFAULT '{}'::jsonb,
  productivity_style VARCHAR(80),
  summary TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash VARCHAR(64) NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS feedback_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  feedback_type VARCHAR(40) NOT NULL,
  message TEXT,
  rating INTEGER,
  status VARCHAR(32) DEFAULT 'open',
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
  memory_id UUID REFERENCES memories(id) ON DELETE SET NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS usage_events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  event_type VARCHAR(80) NOT NULL,
  surface VARCHAR(80),
  value INTEGER,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS memory_feedback (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  memory_id UUID REFERENCES memories(id) ON DELETE SET NULL,
  signal VARCHAR(50) NOT NULL,
  rating INTEGER,
  corrected_context TEXT,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS waitlist_entries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email VARCHAR(320) NOT NULL UNIQUE,
  name VARCHAR(120),
  role VARCHAR(120),
  intended_use TEXT,
  status VARCHAR(32) DEFAULT 'waiting',
  source VARCHAR(120),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS invite_codes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  code VARCHAR(64) NOT NULL UNIQUE,
  email VARCHAR(320),
  created_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  max_uses INTEGER DEFAULT 1,
  use_count INTEGER DEFAULT 0,
  is_active BOOLEAN DEFAULT true,
  expires_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS project_context (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  context_type VARCHAR(50) DEFAULT 'summary',
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}'::jsonb,
  version INTEGER DEFAULT 1,
  is_current BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  deleted_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS daily_summaries (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  summary_date DATE NOT NULL,
  summary_kind VARCHAR(20) DEFAULT 'morning',
  summary TEXT NOT NULL,
  completed_work JSONB DEFAULT '[]'::jsonb,
  unfinished_priorities JSONB DEFAULT '[]'::jsonb,
  insights JSONB DEFAULT '[]'::jsonb,
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  CONSTRAINT uq_daily_summaries_user_date_kind UNIQUE (user_id, summary_date, summary_kind)
);

CREATE TABLE IF NOT EXISTS ai_interactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
  message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
  interaction_type VARCHAR(50) NOT NULL,
  provider VARCHAR(50),
  model VARCHAR(120),
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  latency_ms INTEGER,
  status VARCHAR(20) DEFAULT 'success',
  error_message TEXT,
  request_id VARCHAR(64),
  metadata JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_messages_embedding') THEN
    ALTER TABLE messages
      ADD CONSTRAINT fk_messages_embedding FOREIGN KEY (embedding_id) REFERENCES embeddings(id) ON DELETE SET NULL;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_memories_embedding') THEN
    ALTER TABLE memories
      ADD CONSTRAINT fk_memories_embedding FOREIGN KEY (embedding_id) REFERENCES embeddings(id) ON DELETE SET NULL;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS ix_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS ix_feedback_items_user_id ON feedback_items(user_id);
CREATE INDEX IF NOT EXISTS ix_feedback_items_feedback_type ON feedback_items(feedback_type);
CREATE INDEX IF NOT EXISTS ix_feedback_items_status ON feedback_items(status);
CREATE INDEX IF NOT EXISTS ix_feedback_items_conversation_id ON feedback_items(conversation_id);
CREATE INDEX IF NOT EXISTS ix_feedback_items_memory_id ON feedback_items(memory_id);
CREATE INDEX IF NOT EXISTS ix_usage_events_user_id ON usage_events(user_id);
CREATE INDEX IF NOT EXISTS ix_usage_events_event_type ON usage_events(event_type);
CREATE INDEX IF NOT EXISTS ix_usage_events_surface ON usage_events(surface);
CREATE INDEX IF NOT EXISTS ix_memory_feedback_user_id ON memory_feedback(user_id);
CREATE INDEX IF NOT EXISTS ix_memory_feedback_memory_id ON memory_feedback(memory_id);
CREATE INDEX IF NOT EXISTS ix_memory_feedback_signal ON memory_feedback(signal);
CREATE INDEX IF NOT EXISTS ix_waitlist_entries_email ON waitlist_entries(email);
CREATE INDEX IF NOT EXISTS ix_waitlist_entries_status ON waitlist_entries(status);
CREATE INDEX IF NOT EXISTS ix_invite_codes_code ON invite_codes(code);
CREATE INDEX IF NOT EXISTS ix_invite_codes_email ON invite_codes(email);
CREATE INDEX IF NOT EXISTS ix_invite_codes_is_active ON invite_codes(is_active);
CREATE INDEX IF NOT EXISTS ix_project_context_project_id ON project_context(project_id);
CREATE INDEX IF NOT EXISTS ix_project_context_context_type ON project_context(context_type);
CREATE INDEX IF NOT EXISTS ix_project_context_is_current ON project_context(is_current);
CREATE INDEX IF NOT EXISTS ix_project_context_deleted_at ON project_context(deleted_at);
CREATE INDEX IF NOT EXISTS ix_daily_summaries_user_id ON daily_summaries(user_id);
CREATE INDEX IF NOT EXISTS ix_daily_summaries_summary_date ON daily_summaries(summary_date);
CREATE INDEX IF NOT EXISTS ix_daily_summaries_summary_kind ON daily_summaries(summary_kind);
CREATE INDEX IF NOT EXISTS ix_ai_interactions_user_id ON ai_interactions(user_id);
CREATE INDEX IF NOT EXISTS ix_ai_interactions_conversation_id ON ai_interactions(conversation_id);
CREATE INDEX IF NOT EXISTS ix_ai_interactions_interaction_type ON ai_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS ix_ai_interactions_status ON ai_interactions(status);
CREATE INDEX IF NOT EXISTS ix_ai_interactions_request_id ON ai_interactions(request_id);
