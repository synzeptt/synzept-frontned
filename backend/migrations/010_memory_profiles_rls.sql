-- Supabase migration for persistent V2 memory profiles and revision history.

ALTER TABLE public.memories
  ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

CREATE TABLE IF NOT EXISTS public.memory_revisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  memory_id UUID NOT NULL REFERENCES public.memories(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('created', 'updated', 'merged', 'deleted')),
  content TEXT NOT NULL,
  category TEXT NOT NULL,
  importance_score DOUBLE PRECISION NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS ix_memory_revisions_memory_id ON public.memory_revisions(memory_id);
CREATE INDEX IF NOT EXISTS ix_memory_revisions_user_id ON public.memory_revisions(user_id);

ALTER TABLE public.memory_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memory_revisions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can access their own memory revisions" ON public.memory_revisions;
CREATE POLICY "Users can access their own memory revisions"
  ON public.memory_revisions FOR ALL
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());
