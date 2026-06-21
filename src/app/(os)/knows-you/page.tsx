"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Brain, Check, Edit3, Loader2, Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type AgentMemoryTimeline, type Project, type UserUnderstandingCoverage, type UserUnderstandingItem, type UserUnderstandingProfile } from "@/lib/api";
import { cn } from "@/lib/cn";
import { PageFrame } from "@frontend/components/layout/page-frame";

const sections = [
  { id: "startup", title: "Professional: Startup", empty: "Add the venture, product, or startup context Synzept should keep in view." },
  { id: "about_me", title: "Personal · About me", empty: "Add the context you never want to explain twice." },
  { id: "interests", title: "Personal · Interests", empty: "Add recurring topics, industries, or themes." },
  { id: "habits", title: "Personal · Habits", empty: "Add routines and patterns that shape your days." },
  { id: "preferences", title: "Personal · Preferences", empty: "Add how you prefer to think, plan, decide, or communicate." },
  { id: "job", title: "Professional · Job", empty: "Add your role, team, and work context." },
  { id: "company", title: "Professional · Company", empty: "Add the company, startup, or organization you are building with." },
  { id: "projects", title: "Professional · Projects", empty: "Project knowledge appears from your workspace and manual notes." },
  { id: "responsibilities", title: "Professional · Responsibilities", empty: "Add the responsibilities Synzept should keep in view." },
  { id: "short_term_goals", title: "Goals · Short-term", empty: "Add outcomes for the coming days or weeks." },
  { id: "long_term_goals", title: "Goals · Long-term", empty: "Add outcomes that need sustained attention." },
  { id: "missions", title: "Goals · Missions", empty: "Add the larger mission behind your work and life." },
  { id: "important_people", title: "Relationships · Important people", empty: "Add the people and relationships that matter." },
  { id: "commitments", title: "Relationships · Commitments", empty: "Add promises and commitments Synzept should remember." },
  { id: "learning_topics", title: "Learning · Topics", empty: "Add subjects or questions you want to explore." },
  { id: "skills", title: "Learning · Skills", empty: "Add capabilities you are developing or want to develop." },
  { id: "current_focus", title: "Current situation · Focus", empty: "Add what matters this week or today." },
  { id: "current_struggles", title: "Current situation · Struggles", empty: "Add what is blocking or slowing you down." },
  { id: "open_loops", title: "Current situation · Open loops", empty: "Add unresolved work, decisions, or follow-ups." },
  { id: "learned_understanding", title: "Learned Understanding", empty: "Agent recall from goals, projects, decisions, conversations, and milestones appears here." },
  { id: "decision_memory", title: "Decision Memory", empty: "Important decisions, reasons, and outcomes appear here as Synzept learns them." },
  { id: "recent_priorities", title: "Recent Priorities", empty: "Recent priorities appear as Synzept sees what changed and what remains unfinished." },
  { id: "accepted_learnings", title: "Accepted Learnings", empty: "Accepted learnings appear here after you approve them." },
] as const;

type SectionId = (typeof sections)[number]["id"];

const categoryAliases: Record<string, SectionId> = {
  about_me: "about_me",
  personal: "about_me",
  goals: "short_term_goals",
  goal: "short_term_goals",
  short_term_goals: "short_term_goals",
  long_term_goals: "long_term_goals",
  missions: "missions",
  current_mission: "missions",
  mission: "missions",
  current_focus: "current_focus",
  focus: "current_focus",
  current_challenges: "current_struggles",
  current_struggles: "current_struggles",
  challenges: "current_struggles",
  blockers: "current_struggles",
  interests: "interests",
  interest: "interests",
  habits: "habits",
  projects: "projects",
  project: "projects",
  work_style: "preferences",
  preferences: "preferences",
  job: "job",
  company: "company",
  startup: "startup",
  responsibilities: "responsibilities",
  important_people: "important_people",
  relationships: "important_people",
  commitments: "commitments",
  open_loops: "open_loops",
  learned_insights: "accepted_learnings",
  learned_understanding: "learned_understanding",
  decision_memory: "decision_memory",
  decisions: "decision_memory",
  decision: "decision_memory",
  recent_priorities: "recent_priorities",
  learning: "learning_topics",
  learning_topics: "learning_topics",
  topics: "learning_topics",
  skills: "skills",
  accepted_learnings: "accepted_learnings",
};

export default function KnowsYouPage() {
  const [items, setItems] = useState<UserUnderstandingItem[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [memoryTimeline, setMemoryTimeline] = useState<AgentMemoryTimeline | null>(null);
  const [profile, setProfile] = useState<UserUnderstandingProfile | null>(null);
  const [coverage, setCoverage] = useState<UserUnderstandingCoverage | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [draft, setDraft] = useState({ category: "about_me" as SectionId, title: "", value: "" });

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([
      api.listUserUnderstanding(),
      api.getUserUnderstandingProfile().catch(() => null),
      api.getUserUnderstandingCoverage().catch(() => null),
      api.listProjects().catch(() => []),
      api.getAgentMemoryTimeline().catch(() => null),
    ])
      .then(([understanding, profileData, coverageData, projectRows, timeline]) => {
        setItems(understanding);
        setProfile(profileData);
        setCoverage(coverageData);
        setProjects(projectRows);
        setMemoryTimeline(timeline);
      })
      .catch(() => setError("Synzept Knows You could not load. Your workspace is still safe."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const grouped = useMemo(() => groupItems(items), [items]);

  const create = async () => {
    if (!draft.title.trim() || !draft.value.trim()) return;
    const created = await api.createUserUnderstanding({
      category: draft.category,
      title: draft.title.trim(),
      value: draft.value.trim(),
    });
    setItems((current) => [created, ...current]);
    setDraft({ category: draft.category, title: "", value: "" });
  };

  const syncUnderstanding = async () => {
    setSyncing(true);
    setError(null);
    try {
      const result = await api.syncUserUnderstanding();
      setCoverage(result.coverage);
      await load();
    } catch {
      setError("Synzept could not refresh learned context right now. Existing understanding is unchanged.");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <PageFrame eyebrow="Transparent memory" title="Synzept Knows You">
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="grid gap-4 md:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Personal operating context</p>
              <h2 className="mt-2 text-2xl font-semibold text-stone-950">Current mission and focus, in one place.</h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-600">
                Synzept surfaces the mission, current focus, active projects, open loops, recent progress, decisions, and next suggested actions it is using.
              </p>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <SummaryPill label="Mission" value={firstItem(profile?.current_mission) || "Add a mission"} />
              <SummaryPill label="Focus" value={firstItem(profile?.current_focus) || "Add a current focus"} />
              <SummaryPill label="Projects" value={countLabel(profile?.active_projects?.length)} />
              <SummaryPill label="Open loops" value={countLabel(profile?.open_loops?.length)} />
              <SummaryPill label="Recent progress" value={countLabel(profile?.recent_progress?.length)} />
              <SummaryPill label="Next actions" value={countLabel(profile?.next_suggested_actions?.length)} />
            </div>
          </div>
          <div className="mt-4 grid gap-2 md:grid-cols-3">
            <SummaryList title="Active projects" items={profile?.active_projects || []} empty="No active projects yet." />
            <SummaryList title="Open loops" items={profile?.open_loops || []} empty="No open loops yet." />
            <SummaryList title="Recent decisions" items={profile?.recent_decisions || []} empty="No recent decisions yet." />
          </div>
        </section>
        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="grid gap-5 lg:grid-cols-[minmax(0,0.9fr)_minmax(320px,1.1fr)]">
            <div>
              <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted">
                <Brain className="h-3.5 w-3.5" />
                Agent Memory
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-stone-950">Everything Synzept uses should be visible.</h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">
                Add, edit, or remove the facts and preferences that shape Agent recommendations. Learned items stay separate from user-entered items.
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <div className="rounded-md bg-stone-100 px-3 py-2 text-sm text-stone-700">
                  {coverage ? `${coverage.completion_percent}% understood · ${coverage.learned_items} learned automatically` : "Understanding coverage is loading"}
                </div>
                <Button variant="outline" size="sm" onClick={syncUnderstanding} disabled={syncing}>
                  {syncing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Brain className="mr-2 h-4 w-4" />}
                  Refresh learned context
                </Button>
              </div>
            </div>
            <div className="grid gap-3 rounded-lg border border-border bg-stone-50 p-4">
              <div className="grid gap-2 sm:grid-cols-[160px_1fr]">
                <select
                  value={draft.category}
                  onChange={(event) => setDraft((current) => ({ ...current, category: event.target.value as SectionId }))}
                  className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
                >
                  {sections.map((section) => (
                    <option key={section.id} value={section.id}>{section.title}</option>
                  ))}
                </select>
                <input
                  value={draft.title}
                  onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
                  placeholder="Short label"
                  className="h-10 rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
                />
              </div>
              <textarea
                value={draft.value}
                onChange={(event) => setDraft((current) => ({ ...current, value: event.target.value }))}
                placeholder="What should Synzept know?"
                rows={3}
                className="resize-none rounded-md border border-border bg-white px-3 py-2 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
              />
              <Button onClick={create} disabled={!draft.title.trim() || !draft.value.trim()} className="w-fit">
                <Plus className="mr-2 h-4 w-4" />
                Add Memory
              </Button>
            </div>
          </div>
        </section>

        {loading ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-48 rounded-lg" />)}
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            {sections.map((section) => (
              <KnowledgeSection
                key={section.id}
                title={section.title}
                empty={section.empty}
                items={section.id === "projects" ? withProjectItems(grouped[section.id] || [], projects) : withMemoryItems(section.id, grouped[section.id] || [], memoryTimeline)}
                onUpdate={(updated) => setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)))}
                onDelete={(id) => setItems((current) => current.filter((item) => item.id !== id))}
              />
            ))}
          </div>
        )}
      </div>
    </PageFrame>
  );
}

function SummaryPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-stone-50 px-3 py-3">
      <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted">{label}</p>
      <p className="mt-1 line-clamp-2 text-sm leading-6 text-stone-900">{value}</p>
    </div>
  );
}

function SummaryList({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-stone-50 p-3">
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">{title}</p>
      <div className="mt-2 space-y-1.5">
        {items.length ? items.slice(0, 4).map((item) => <p key={item} className="rounded-md bg-white px-2.5 py-1.5 text-sm text-stone-700">{item}</p>) : <p className="text-sm text-muted">{empty}</p>}
      </div>
    </div>
  );
}

function firstItem(items?: string[]) {
  return items?.find((item) => item.trim()) || "";
}

function countLabel(count?: number) {
  return typeof count === "number" && count > 0 ? `${count} item${count === 1 ? "" : "s"}` : "None";
}

function KnowledgeSection({
  title,
  empty,
  items,
  onUpdate,
  onDelete,
}: {
  title: string;
  empty: string;
  items: UserUnderstandingItem[];
  onUpdate: (item: UserUnderstandingItem) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-stone-950">{title}</h2>
        <span className="rounded-full bg-stone-100 px-2.5 py-1 text-xs text-muted">{items.length}</span>
      </div>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <KnowledgeItem key={item.id} item={item} onUpdate={onUpdate} onDelete={onDelete} />
        ))}
        {!items.length && <p className="rounded-md bg-stone-50 px-3 py-3 text-sm leading-6 text-muted-foreground">{empty}</p>}
      </div>
    </section>
  );
}

function KnowledgeItem({ item, onUpdate, onDelete }: { item: UserUnderstandingItem; onUpdate: (item: UserUnderstandingItem) => void; onDelete: (id: string) => void }) {
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState(item.title);
  const [value, setValue] = useState(item.value);
  const learned = item.source === "learned";
  const readonly = learned || item.id.startsWith("project:");

  const save = async () => {
    if (readonly || !title.trim() || !value.trim()) return;
    setBusy(true);
    try {
      const updated = await api.updateUserUnderstanding(item.id, { title: title.trim(), value: value.trim() });
      onUpdate(updated);
      setEditing(false);
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (readonly) return;
    setBusy(true);
    try {
      await api.deleteUserUnderstanding(item.id);
      onDelete(item.id);
    } finally {
      setBusy(false);
    }
  };

  return (
    <article className={cn("rounded-md border border-border bg-stone-50 p-3", learned && "border-emerald-100 bg-emerald-50/50")}>
      {editing ? (
        <div className="space-y-2">
          <input value={title} onChange={(event) => setTitle(event.target.value)} className="h-9 w-full rounded-md border border-border bg-white px-3 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10" />
          <textarea value={value} onChange={(event) => setValue(event.target.value)} rows={4} className="w-full resize-none rounded-md border border-border bg-white px-3 py-2 text-sm outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10" />
          <div className="flex gap-2">
            <Button size="sm" onClick={save} disabled={busy}>
              {busy ? <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" /> : <Check className="mr-2 h-3.5 w-3.5" />}
              Save
            </Button>
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
              <X className="mr-2 h-3.5 w-3.5" />
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-sm font-medium text-stone-950">{item.title}</p>
              <p className="mt-1 whitespace-pre-line text-sm leading-6 text-stone-700">{item.value}</p>
              <p className="mt-2 text-xs text-muted">
                {learned ? "Accepted learning" : item.id.startsWith("project:") ? "Project context" : "Added by you"}
                {typeof item.confidence === "number" ? ` - ${Math.round(item.confidence * 100)}% confidence` : ""}
              </p>
            </div>
            {!readonly && (
              <div className="flex shrink-0 gap-1">
                <button type="button" onClick={() => setEditing(true)} className="grid h-8 w-8 place-items-center rounded-md text-stone-500 hover:bg-white hover:text-stone-950" aria-label="Edit memory">
                  <Edit3 className="h-4 w-4" />
                </button>
                <button type="button" onClick={remove} disabled={busy} className="grid h-8 w-8 place-items-center rounded-md text-stone-500 hover:bg-white hover:text-red-600 disabled:opacity-50" aria-label="Remove memory">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </article>
  );
}

function groupItems(items: UserUnderstandingItem[]) {
  const grouped = {} as Record<SectionId, UserUnderstandingItem[]>;
  for (const section of sections) grouped[section.id] = [];
  for (const item of items) {
    const key = categoryAliases[item.category] || (item.source === "learned" ? "accepted_learnings" : "about_me");
    grouped[key].push(item);
  }
  return grouped;
}

function withProjectItems(items: UserUnderstandingItem[], projects: Project[]) {
  const projectItems: UserUnderstandingItem[] = projects.slice(0, 8).map((project) => ({
    id: `project:${project.id}`,
    user_id: "",
    category: "projects",
    title: project.name,
    value: [project.currentFocus, project.recommendedNextStep, project.description].filter(Boolean).join("\n") || "No project context added yet.",
    source: "user",
    confidence: null,
    learned_at: null,
    created_at: project.created_at,
    updated_at: project.updatedAt || project.createdAt || project.created_at,
  }));
  return [...items, ...projectItems];
}

function withMemoryItems(section: SectionId, items: UserUnderstandingItem[], memoryTimeline: AgentMemoryTimeline | null) {
  if (!memoryTimeline) return items;
  if (section === "learned_understanding") {
    const memoryItems = memoryTimeline.items.slice(0, 10).map((item) => syntheticItem({
      id: `memory:${item.id}`,
      category: "learned_understanding",
      title: item.title,
      value: `${item.why_it_mattered}\n\nWhen: ${new Date(item.happened_at).toLocaleString()}`,
      created_at: item.happened_at,
      updated_at: item.happened_at,
    }));
    return [...items, ...memoryItems];
  }
  if (section === "recent_priorities") {
    const priorities = [
      memoryTimeline.recommended_next_step,
      ...memoryTimeline.unfinished.slice(0, 5),
      ...memoryTimeline.what_changed.slice(0, 4),
    ].filter(Boolean);
    const priorityItems = Array.from(new Set(priorities)).slice(0, 10).map((priority, index) => syntheticItem({
      id: `priority:${index}:${priority}`,
      category: "recent_priorities",
      title: index === 0 ? "Recommended next action" : priority,
      value: priority,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));
    return [...items, ...priorityItems];
  }
  if (section === "decision_memory") {
    const decisionItems = memoryTimeline.important_decisions.slice(0, 10).map((decision, index) => syntheticItem({
      id: `decision:${index}:${decision}`,
      category: "decision_memory",
      title: "Decision",
      value: decision,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));
    return [...items, ...decisionItems];
  }
  return items;
}

function syntheticItem({
  id,
  category,
  title,
  value,
  created_at,
  updated_at,
}: {
  id: string;
  category: string;
  title: string;
  value: string;
  created_at: string;
  updated_at: string;
}): UserUnderstandingItem {
  return {
    id,
    user_id: "",
    category,
    title,
    value,
    source: "learned",
    confidence: null,
    learned_at: created_at,
    created_at,
    updated_at,
  };
}
