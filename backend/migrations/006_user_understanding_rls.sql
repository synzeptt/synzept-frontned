-- Supabase migration for the visible V2 user-understanding store.
-- Every policy scopes rows to the authenticated Supabase user.

CREATE TABLE IF NOT EXISTS public.user_understanding (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  title TEXT NOT NULL,
  value TEXT NOT NULL,
  source TEXT NOT NULL CHECK (source IN ('user', 'learned')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS ix_user_understanding_user_id ON public.user_understanding(user_id);
CREATE INDEX IF NOT EXISTS ix_user_understanding_category ON public.user_understanding(category);

CREATE OR REPLACE FUNCTION public.set_user_understanding_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = timezone('utc', now());
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS set_user_understanding_updated_at ON public.user_understanding;
CREATE TRIGGER set_user_understanding_updated_at
  BEFORE UPDATE ON public.user_understanding
  FOR EACH ROW
  EXECUTE FUNCTION public.set_user_understanding_updated_at();

ALTER TABLE public.user_understanding ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_understanding FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view their own understanding" ON public.user_understanding;
CREATE POLICY "Users can view their own understanding"
  ON public.user_understanding FOR SELECT
  USING (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can add their own understanding" ON public.user_understanding;
CREATE POLICY "Users can add their own understanding"
  ON public.user_understanding FOR INSERT
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can edit their own understanding" ON public.user_understanding;
CREATE POLICY "Users can edit their own understanding"
  ON public.user_understanding FOR UPDATE
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can delete their own understanding" ON public.user_understanding;
CREATE POLICY "Users can delete their own understanding"
  ON public.user_understanding FOR DELETE
  USING (user_id = auth.uid());
