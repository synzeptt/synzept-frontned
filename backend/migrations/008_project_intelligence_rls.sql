-- Supabase migration for V2 project intelligence.

CREATE TABLE IF NOT EXISTS public.project_intelligence (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL UNIQUE REFERENCES public.projects(id) ON DELETE CASCADE,
  current_focus TEXT NOT NULL DEFAULT '',
  summary TEXT NOT NULL DEFAULT '',
  recommended_next_step TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS public.project_decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  decision TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS public.project_open_loops (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
  loop TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS ix_project_intelligence_project_id ON public.project_intelligence(project_id);
CREATE INDEX IF NOT EXISTS ix_project_decisions_project_id ON public.project_decisions(project_id);
CREATE INDEX IF NOT EXISTS ix_project_open_loops_project_id ON public.project_open_loops(project_id);

CREATE OR REPLACE FUNCTION public.set_project_intelligence_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = timezone('utc', now());
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS set_project_intelligence_updated_at ON public.project_intelligence;
CREATE TRIGGER set_project_intelligence_updated_at
  BEFORE UPDATE ON public.project_intelligence
  FOR EACH ROW
  EXECUTE FUNCTION public.set_project_intelligence_updated_at();

ALTER TABLE public.project_intelligence ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_intelligence FORCE ROW LEVEL SECURITY;
ALTER TABLE public.project_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE public.project_open_loops ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_open_loops FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Owners can access project intelligence" ON public.project_intelligence;
CREATE POLICY "Owners can access project intelligence"
  ON public.project_intelligence FOR ALL
  USING (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_intelligence.project_id AND projects.user_id = auth.uid()))
  WITH CHECK (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_intelligence.project_id AND projects.user_id = auth.uid()));

DROP POLICY IF EXISTS "Owners can access project decisions" ON public.project_decisions;
CREATE POLICY "Owners can access project decisions"
  ON public.project_decisions FOR ALL
  USING (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_decisions.project_id AND projects.user_id = auth.uid()))
  WITH CHECK (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_decisions.project_id AND projects.user_id = auth.uid()));

DROP POLICY IF EXISTS "Owners can access project open loops" ON public.project_open_loops;
CREATE POLICY "Owners can access project open loops"
  ON public.project_open_loops FOR ALL
  USING (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_open_loops.project_id AND projects.user_id = auth.uid()))
  WITH CHECK (EXISTS (SELECT 1 FROM public.projects WHERE projects.id = project_open_loops.project_id AND projects.user_id = auth.uid()));
