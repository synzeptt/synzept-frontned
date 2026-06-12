-- Supabase migration for the unified V2 workspace.

ALTER TABLE public.notes
  ADD COLUMN IF NOT EXISTS goal_id UUID REFERENCES public.goals(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS ix_notes_goal_id ON public.notes(goal_id);

CREATE TABLE IF NOT EXISTS public.workspace_activities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
  goal_id UUID REFERENCES public.goals(id) ON DELETE SET NULL,
  task_id UUID REFERENCES public.tasks(id) ON DELETE SET NULL,
  note_id UUID REFERENCES public.notes(id) ON DELETE SET NULL,
  action TEXT NOT NULL,
  title TEXT NOT NULL,
  detail TEXT NOT NULL DEFAULT '',
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS ix_workspace_activities_user_id ON public.workspace_activities(user_id);
CREATE INDEX IF NOT EXISTS ix_workspace_activities_project_id ON public.workspace_activities(project_id);
CREATE INDEX IF NOT EXISTS ix_workspace_activities_goal_id ON public.workspace_activities(goal_id);
CREATE INDEX IF NOT EXISTS ix_workspace_activities_created_at ON public.workspace_activities(created_at);

ALTER TABLE public.workspace_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workspace_activities FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can access their own workspace activity" ON public.workspace_activities;
CREATE POLICY "Users can access their own workspace activity"
  ON public.workspace_activities FOR ALL
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());
