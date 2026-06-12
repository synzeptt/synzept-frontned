-- Supabase migration for persisted V2 daily brief snapshots.

CREATE TABLE IF NOT EXISTS public.daily_briefs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  brief_date DATE NOT NULL,
  summary TEXT NOT NULL,
  open_loops JSONB NOT NULL DEFAULT '[]'::jsonb,
  next_step TEXT NOT NULL,
  context JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  CONSTRAINT uq_daily_briefs_user_date UNIQUE (user_id, brief_date)
);

CREATE INDEX IF NOT EXISTS ix_daily_briefs_user_id ON public.daily_briefs(user_id);
CREATE INDEX IF NOT EXISTS ix_daily_briefs_brief_date ON public.daily_briefs(brief_date);

ALTER TABLE public.daily_briefs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.daily_briefs FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own daily briefs" ON public.daily_briefs;
CREATE POLICY "Users can view their own daily briefs"
  ON public.daily_briefs FOR SELECT
  USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can add their own daily briefs" ON public.daily_briefs;
CREATE POLICY "Users can add their own daily briefs"
  ON public.daily_briefs FOR INSERT
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can update their own daily briefs" ON public.daily_briefs;
CREATE POLICY "Users can update their own daily briefs"
  ON public.daily_briefs FOR UPDATE
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can delete their own daily briefs" ON public.daily_briefs;
CREATE POLICY "Users can delete their own daily briefs"
  ON public.daily_briefs FOR DELETE
  USING (user_id = auth.uid());
