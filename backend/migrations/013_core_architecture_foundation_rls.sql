-- Shared Synzept V2 foundation for Supabase PostgreSQL.
-- Apply after 012_workspace_system_rls.sql.

ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS title TEXT;
UPDATE public.projects SET title = name WHERE title IS NULL;
ALTER TABLE public.goals ADD COLUMN IF NOT EXISTS target_date DATE;
ALTER TABLE public.memories
  ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'system';

CREATE INDEX IF NOT EXISTS ix_goals_target_date ON public.goals(target_date);
CREATE INDEX IF NOT EXISTS ix_memories_source ON public.memories(source);

CREATE TABLE IF NOT EXISTS public.timeline_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  importance DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (importance >= 0 AND importance <= 1),
  event_date DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS public.learning_signals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  signal_type TEXT NOT NULL,
  content TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'ignored')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS public.graph_nodes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  node_type TEXT NOT NULL,
  title TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE TABLE IF NOT EXISTS public.graph_edges (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  source_node_id UUID NOT NULL REFERENCES public.graph_nodes(id) ON DELETE CASCADE,
  target_node_id UUID NOT NULL REFERENCES public.graph_nodes(id) ON DELETE CASCADE,
  relationship_type TEXT NOT NULL,
  strength DOUBLE PRECISION NOT NULL DEFAULT 0.5 CHECK (strength >= 0 AND strength <= 1),
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
  CONSTRAINT uq_graph_edges_relation UNIQUE (user_id, source_node_id, target_node_id, relationship_type)
);

CREATE INDEX IF NOT EXISTS ix_timeline_events_user_id ON public.timeline_events(user_id);
CREATE INDEX IF NOT EXISTS ix_timeline_events_event_date ON public.timeline_events(event_date);
CREATE INDEX IF NOT EXISTS ix_learning_signals_user_id ON public.learning_signals(user_id);
CREATE INDEX IF NOT EXISTS ix_learning_signals_status ON public.learning_signals(status);
CREATE INDEX IF NOT EXISTS ix_graph_nodes_user_id ON public.graph_nodes(user_id);
CREATE INDEX IF NOT EXISTS ix_graph_edges_user_id ON public.graph_edges(user_id);
CREATE INDEX IF NOT EXISTS ix_graph_edges_source_node_id ON public.graph_edges(source_node_id);
CREATE INDEX IF NOT EXISTS ix_graph_edges_target_node_id ON public.graph_edges(target_node_id);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users FORCE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects FORCE ROW LEVEL SECURITY;
ALTER TABLE public.goals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.goals FORCE ROW LEVEL SECURITY;
ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.memories FORCE ROW LEVEL SECURITY;
ALTER TABLE public.timeline_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.timeline_events FORCE ROW LEVEL SECURITY;
ALTER TABLE public.learning_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_signals FORCE ROW LEVEL SECURITY;
ALTER TABLE public.graph_nodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.graph_nodes FORCE ROW LEVEL SECURITY;
ALTER TABLE public.graph_edges ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.graph_edges FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can access their own user row" ON public.users;
CREATE POLICY "Users can access their own user row" ON public.users FOR ALL USING (id = auth.uid()) WITH CHECK (id = auth.uid());
DROP POLICY IF EXISTS "Users can access their own projects" ON public.projects;
CREATE POLICY "Users can access their own projects" ON public.projects FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users can access their own goals" ON public.goals;
CREATE POLICY "Users can access their own goals" ON public.goals FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users can access their own memories" ON public.memories;
CREATE POLICY "Users can access their own memories" ON public.memories FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users can access their own timeline events" ON public.timeline_events;
CREATE POLICY "Users can access their own timeline events" ON public.timeline_events FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users can access their own learning signals" ON public.learning_signals;
CREATE POLICY "Users can access their own learning signals" ON public.learning_signals FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users can access their own graph nodes" ON public.graph_nodes;
CREATE POLICY "Users can access their own graph nodes" ON public.graph_nodes FOR ALL USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
DROP POLICY IF EXISTS "Users can access their own graph edges" ON public.graph_edges;
CREATE POLICY "Users can access their own graph edges" ON public.graph_edges FOR ALL
  USING (
    user_id = auth.uid()
    AND EXISTS (SELECT 1 FROM public.graph_nodes source WHERE source.id = source_node_id AND source.user_id = auth.uid())
    AND EXISTS (SELECT 1 FROM public.graph_nodes target WHERE target.id = target_node_id AND target.user_id = auth.uid())
  )
  WITH CHECK (
    user_id = auth.uid()
    AND EXISTS (SELECT 1 FROM public.graph_nodes source WHERE source.id = source_node_id AND source.user_id = auth.uid())
    AND EXISTS (SELECT 1 FROM public.graph_nodes target WHERE target.id = target_node_id AND target.user_id = auth.uid())
  );
