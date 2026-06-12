-- Supabase migration for the approval-first V2 Learning Engine.

ALTER TABLE public.user_understanding
  ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS learned_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS public.learning_observations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL,
  source_id UUID NOT NULL,
  signal TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  CONSTRAINT uq_learning_observations_source_signal UNIQUE (user_id, source_type, source_id, signal)
);

CREATE TABLE IF NOT EXISTS public.learning_suggestions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'ignored', 'edited')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS ix_learning_observations_user_id ON public.learning_observations(user_id);
CREATE INDEX IF NOT EXISTS ix_learning_suggestions_user_id ON public.learning_suggestions(user_id);

ALTER TABLE public.learning_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_observations FORCE ROW LEVEL SECURITY;
ALTER TABLE public.learning_suggestions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_suggestions FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can access their own learning observations" ON public.learning_observations;
CREATE POLICY "Users can access their own learning observations"
  ON public.learning_observations FOR ALL
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

DROP POLICY IF EXISTS "Users can access their own learning suggestions" ON public.learning_suggestions;
CREATE POLICY "Users can access their own learning suggestions"
  ON public.learning_suggestions FOR ALL
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());
