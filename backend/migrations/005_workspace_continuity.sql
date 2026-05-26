-- Projects, notes, and task continuity updates.
-- Apply after 004_memory_retrieval_foundation.sql.

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

INSERT INTO schema_migrations (version)
VALUES ('005_workspace_continuity')
ON CONFLICT (version) DO NOTHING;

ALTER TABLE notes
  ADD COLUMN IF NOT EXISTS summary TEXT,
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;

UPDATE tasks
SET status = 'todo'
WHERE status = 'pending';

UPDATE tasks
SET status = 'completed'
WHERE status = 'done';

CREATE INDEX IF NOT EXISTS ix_notes_project_updated_at ON notes(project_id, updated_at);
CREATE INDEX IF NOT EXISTS ix_tasks_project_status ON tasks(project_id, status);
CREATE INDEX IF NOT EXISTS ix_conversations_project_updated_at ON conversations(project_id, updated_at);
CREATE INDEX IF NOT EXISTS ix_memories_project_updated_at ON memories(project_id, updated_at);
