"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Archive,
  ArrowRight,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Circle,
  Clock3,
  Edit3,
  Folder,
  Link as LinkIcon,
  ListChecks,
  MoreHorizontal,
  NotebookText,
  Paperclip,
  Plus,
  Search,
  Sparkles,
  Trash2,
  Upload,
  Users,
  Video,
  X,
} from "lucide-react";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, type Conversation, type DailyBriefSnapshot, type Dashboard, type Note, type Project, type S1Home, type Task } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/stores/auth";
import { PageFrame } from "@frontend/components/layout/page-frame";

const CHAT_DRAFT_KEY = "synzept_chat_draft";
const CALENDAR_KEY = "synzept_dashboard_calendar_events";
const MEETINGS_KEY = "synzept_dashboard_meetings";
const DOCUMENTS_KEY = "synzept_dashboard_documents";

type CalendarView = "day" | "week" | "month" | "year";
type CalendarEvent = {
  id: string;
  title: string;
  description: string;
  date: string;
  time: string;
  location: string;
  participants: string;
  notes: string;
  attachments: string[];
  recurring: "none" | "daily" | "weekly" | "monthly";
  reminder: string;
};
type Meeting = {
  id: string;
  title: string;
  date: string;
  time: string;
  link: string;
  participants: string;
  agenda: string;
  notes: string;
  summary: string;
  followUp: string;
};
type WorkspaceDocument = {
  id: string;
  title: string;
  kind: "note" | "document" | "file";
  folder: string;
  content: string;
  tags: string;
  pinned: boolean;
  favorite: boolean;
  archived: boolean;
  attachments: string[];
  updatedAt: string;
};
type TimeGreeting = {
  greeting: string;
  brief: string;
  phase: "morning" | "afternoon" | "evening" | "night";
};
type BriefItem = { id?: string | null; title: string; detail?: string | null; href?: string | null; priority?: string | null };

const defaultEvents: CalendarEvent[] = [
  {
    id: "event-planning",
    title: "Plan today",
    description: "Review priorities and choose the next action.",
    date: todayInput(),
    time: "09:30",
    location: "Synzept",
    participants: "",
    notes: "Keep the plan small enough to finish.",
    attachments: [],
    recurring: "daily",
    reminder: "15 minutes before",
  },
];

const defaultMeetings: Meeting[] = [
  {
    id: "meeting-weekly",
    title: "Weekly review",
    date: todayInput(),
    time: "17:00",
    link: "",
    participants: "",
    agenda: "Review progress, blockers, and follow-ups.",
    notes: "",
    summary: "",
    followUp: "Capture action items after the meeting.",
  },
];

const defaultDocuments: WorkspaceDocument[] = [
  {
    id: "doc-dashboard",
    title: "Dashboard operating note",
    kind: "note",
    folder: "Workspace",
    content: "Use this workspace to collect notes, files, meetings, tasks, and continuation points.",
    tags: "dashboard, planning",
    pinned: true,
    favorite: false,
    archived: false,
    attachments: [],
    updatedAt: new Date().toISOString(),
  },
];

export function DashboardPage() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const timeGreeting = useTimeGreeting();
  const [s1Home, setS1Home] = useState<S1Home | null>(null);
  const [dailyBrief, setDailyBrief] = useState<DailyBriefSnapshot | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [events, setEvents] = useLocalState<CalendarEvent[]>(CALENDAR_KEY, defaultEvents);
  const [meetings, setMeetings] = useLocalState<Meeting[]>(MEETINGS_KEY, defaultMeetings);
  const [documents, setDocuments] = useLocalState<WorkspaceDocument[]>(DOCUMENTS_KEY, defaultDocuments);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState("brief");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s1, daily, dash, taskRows, projectRows, noteRows, conversationRows] = await Promise.all([
        api.getS1Home().catch(() => null),
        api.getDailyBriefV2().catch(() => null),
        api.getDashboard().catch(() => null),
        api.listTasks().catch(() => []),
        api.listProjects().catch(() => []),
        api.listNotes().catch(() => []),
        api.listConversations().catch(() => []),
      ]);
      setS1Home(s1);
      setDailyBrief(daily);
      setDashboard(dash);
      setTasks(taskRows);
      setProjects(projectRows);
      setNotes(noteRows);
      setConversations(conversationRows);
      void api.trackEvent("dashboard_workspace_loaded", "dashboard", {
        tasks: taskRows.length,
        projects: projectRows.length,
        notes: noteRows.length,
        events: events.length,
      });
    } catch {
      setError("Dashboard could not refresh. Your local workspace is still available.");
    } finally {
      setLoading(false);
    }
  }, [events.length]);

  useEffect(() => {
    void load();
  }, [load]);

  const brief = useMemo(() => buildBrief({ s1Home, dailyBrief, dashboard, timeGreeting, name: user?.display_name || null }), [dashboard, dailyBrief, s1Home, timeGreeting, user?.display_name]);

  const continueWithPrompt = (prompt: string) => {
    localStorage.setItem(CHAT_DRAFT_KEY, prompt);
    router.push("/chat");
  };

  return (
    <PageFrame eyebrow="Dashboard" title="Personal Workspace">
      <div className="min-h-full bg-[#f7f6f2] text-stone-950">
        <div className="mx-auto flex w-full max-w-[1500px] gap-5 px-3 py-4 sm:px-5 lg:px-7">
          <aside className="sticky top-4 hidden h-[calc(100dvh-2rem)] w-52 shrink-0 flex-col rounded-lg border border-stone-200 bg-white p-2 shadow-[0_12px_35px_rgba(28,25,23,0.04)] xl:flex">
            <p className="px-3 pb-2 pt-3 text-xs font-semibold uppercase tracking-[0.18em] text-stone-400">Workspace</p>
            {sections.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition",
                  activeSection === section.id ? "bg-stone-950 text-white" : "text-stone-600 hover:bg-stone-100 hover:text-stone-950",
                )}
              >
                <section.icon className="h-4 w-4" />
                {section.label}
              </a>
            ))}
          </aside>

          <main className="min-w-0 flex-1 space-y-5 pb-24">
            <RecoveryBanner message={error} onRetry={load} />
            {loading ? <DashboardSkeleton /> : null}
            <AIDailyBrief id="brief" brief={brief} timeGreeting={timeGreeting} onContinue={() => continueWithPrompt(buildBriefPrompt(brief))} />
            <CalendarModule id="calendar" events={events} setEvents={setEvents} />
            <TasksModule id="tasks" tasks={tasks} projects={projects} setTasks={setTasks} setError={setError} reload={load} />
            <ProjectsModule id="projects" projects={projects} tasks={tasks} notes={notes} conversations={conversations} setProjects={setProjects} setError={setError} reload={load} onContinue={continueWithPrompt} />
            <MeetingsModule id="meetings" meetings={meetings} setMeetings={setMeetings} />
            <DocumentsModule id="documents" documents={documents} setDocuments={setDocuments} notes={notes} setError={setError} reload={load} />
            <ContinueWorking id="continue" brief={brief} tasks={tasks} projects={projects} conversations={conversations} onContinue={continueWithPrompt} />
            <RecentActivity id="activity" dashboard={dashboard} tasks={tasks} projects={projects} notes={notes} meetings={meetings} documents={documents} />
            <AISuggestions id="suggestions" brief={brief} tasks={tasks} projects={projects} notes={notes} onContinue={continueWithPrompt} />
          </main>
        </div>
      </div>
    </PageFrame>
  );
}

const sections = [
  { id: "brief", label: "Daily Brief", icon: Sparkles },
  { id: "calendar", label: "Calendar", icon: CalendarDays },
  { id: "tasks", label: "Tasks", icon: ListChecks },
  { id: "projects", label: "Projects", icon: Folder },
  { id: "meetings", label: "Meetings", icon: Video },
  { id: "documents", label: "Documents", icon: NotebookText },
  { id: "continue", label: "Continue", icon: ArrowRight },
  { id: "activity", label: "Activity", icon: Clock3 },
  { id: "suggestions", label: "AI Suggestions", icon: Sparkles },
];

function AIDailyBrief({ id, brief, timeGreeting, onContinue }: { id: string; brief: BuiltBrief; timeGreeting: TimeGreeting; onContinue: () => void }) {
  return (
    <WorkspaceSection id={id} label="AI Daily Brief" title={brief.greeting} action={<PrimaryButton onClick={onContinue}>Continue <ArrowRight className="h-4 w-4" /></PrimaryButton>}>
      <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-lg bg-stone-950 p-5 text-white sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-stone-400">{timeGreeting.phase} brief</p>
          <h2 className="mt-3 max-w-3xl text-3xl font-semibold tracking-tight sm:text-4xl">{brief.subtitle}</h2>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-stone-300">{brief.summary}</p>
          <div className="mt-5 rounded-lg bg-white/8 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-400">Suggested next action</p>
            <p className="mt-2 text-lg font-semibold">{brief.nextAction.title}</p>
            {brief.nextAction.detail ? <p className="mt-1 text-sm leading-6 text-stone-300">{brief.nextAction.detail}</p> : null}
          </div>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          <BriefList title="Today's priorities" items={brief.priorities} empty="No priorities yet. Add tasks or projects and Synzept will rank them." />
          <BriefList title="Needs attention" items={brief.attention} empty="Nothing urgent is visible right now." />
        </div>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <BriefList title="Yesterday" items={brief.yesterday} empty="No recent summary yet." />
        <BriefList title="Open loops" items={brief.openLoops} empty="No open loops need attention." />
        <BriefList title="Important reminders" items={brief.reminders} empty="Reminders appear from tasks, events, and workspace context." />
      </div>
    </WorkspaceSection>
  );
}

function BriefList({ title, items, empty }: { title: string; items: BriefItem[]; empty: string }) {
  return (
    <div className="rounded-lg border border-stone-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-stone-950">{title}</h3>
      <div className="mt-3 space-y-2">
        {items.slice(0, 5).map((item) => (
          <div key={`${title}-${item.id || item.title}`} className="rounded-lg bg-stone-50 px-3 py-2.5">
            <p className="line-clamp-2 text-sm font-medium text-stone-900">{item.title}</p>
            {item.detail ? <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{item.detail}</p> : null}
          </div>
        ))}
        {!items.length ? <p className="rounded-lg bg-stone-50 px-3 py-3 text-sm leading-6 text-stone-500">{empty}</p> : null}
      </div>
    </div>
  );
}

function CalendarModule({ id, events, setEvents }: { id: string; events: CalendarEvent[]; setEvents: (events: CalendarEvent[]) => void }) {
  const [view, setView] = useState<CalendarView>("week");
  const [anchor, setAnchor] = useState(() => startOfDay(new Date()));
  const [editing, setEditing] = useState<CalendarEvent | null>(null);
  const [draft, setDraft] = useState(() => blankEvent(anchor));
  const visibleDays = useMemo(() => calendarDays(anchor, view), [anchor, view]);
  const upcoming = useMemo(() => events.slice().sort((a, b) => `${a.date}T${a.time}`.localeCompare(`${b.date}T${b.time}`)).slice(0, 6), [events]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const clean = { ...draft, title: draft.title.trim() || "Untitled event", id: editing?.id || idFor("event") };
    setEvents(editing ? events.map((item) => (item.id === editing.id ? clean : item)) : [clean, ...events]);
    setEditing(null);
    setDraft(blankEvent(anchor));
  };

  const edit = (event: CalendarEvent) => {
    setEditing(event);
    setDraft(event);
  };

  const remove = (eventId: string) => {
    setEvents(events.filter((event) => event.id !== eventId));
    if (editing?.id === eventId) setEditing(null);
  };

  const moveEvent = (eventId: string, date: string) => {
    setEvents(events.map((event) => (event.id === eventId ? { ...event, date } : event)));
  };

  return (
    <WorkspaceSection
      id={id}
      label="Calendar"
      title="Schedule and reminders"
      action={
        <div className="flex items-center gap-1 rounded-lg border border-stone-200 bg-white p-1">
          {(["day", "week", "month", "year"] as CalendarView[]).map((item) => (
            <button key={item} type="button" onClick={() => setView(item)} className={cn("h-8 rounded-md px-3 text-xs capitalize", view === item ? "bg-stone-950 text-white" : "text-stone-500 hover:bg-stone-100")}>{item}</button>
          ))}
        </div>
      }
    >
      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <div className="rounded-lg border border-stone-200 bg-white p-4">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <IconButton label="Previous" onClick={() => setAnchor(shiftAnchor(anchor, view, -1))}><ChevronLeft className="h-4 w-4" /></IconButton>
              <div>
                <p className="text-sm font-semibold text-stone-950">{formatCalendarTitle(anchor, view)}</p>
                <p className="text-xs text-stone-500">Drag events between days. Google Calendar can plug into this model later.</p>
              </div>
              <IconButton label="Next" onClick={() => setAnchor(shiftAnchor(anchor, view, 1))}><ChevronRight className="h-4 w-4" /></IconButton>
            </div>
            <button type="button" onClick={() => setAnchor(startOfDay(new Date()))} className="h-8 rounded-lg border border-stone-200 px-3 text-xs font-medium text-stone-700 hover:bg-stone-50">Today</button>
          </div>
          <div className={cn("grid gap-2", view === "day" ? "grid-cols-1" : view === "year" ? "grid-cols-2 md:grid-cols-4" : "grid-cols-2 md:grid-cols-7")}>
            {visibleDays.map((day) => (
              <CalendarCell key={day.toISOString()} day={day} view={view} events={events.filter((event) => event.date === inputDate(day))} onEdit={edit} onDelete={remove} onMove={moveEvent} />
            ))}
          </div>
        </div>
        <aside className="space-y-4">
          <form onSubmit={submit} className="rounded-lg border border-stone-200 bg-white p-4">
            <PanelTitle icon={<Plus className="h-4 w-4" />} title={editing ? "Edit event" : "Add event"} />
            <CalendarEventForm draft={draft} setDraft={setDraft} />
            <div className="mt-3 flex gap-2">
              <PrimaryButton type="submit">{editing ? "Save event" : "Add event"}</PrimaryButton>
              {editing ? <GhostButton onClick={() => { setEditing(null); setDraft(blankEvent(anchor)); }}>Cancel</GhostButton> : null}
            </div>
          </form>
          <div className="rounded-lg border border-stone-200 bg-white p-4">
            <PanelTitle icon={<Clock3 className="h-4 w-4" />} title="Upcoming schedule" />
            <div className="mt-3 space-y-2">
              {upcoming.map((event) => (
                <button key={event.id} type="button" onClick={() => edit(event)} className="w-full rounded-lg bg-stone-50 px-3 py-2 text-left hover:bg-stone-100">
                  <p className="text-sm font-medium text-stone-950">{event.title}</p>
                  <p className="text-xs text-stone-500">{formatShortDate(event.date)} at {event.time || "anytime"}</p>
                </button>
              ))}
              {!upcoming.length ? <p className="text-sm text-stone-500">No upcoming events.</p> : null}
            </div>
          </div>
        </aside>
      </div>
    </WorkspaceSection>
  );
}

function CalendarCell({ day, view, events, onEdit, onDelete, onMove }: { day: Date; view: CalendarView; events: CalendarEvent[]; onEdit: (event: CalendarEvent) => void; onDelete: (id: string) => void; onMove: (id: string, date: string) => void }) {
  const date = inputDate(day);
  return (
    <div
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        const id = event.dataTransfer.getData("text/event-id");
        if (id) onMove(id, date);
      }}
      className={cn("min-h-28 rounded-lg border border-stone-200 bg-[#fbfaf7] p-2", inputDate(new Date()) === date && "border-stone-950 bg-white")}
    >
      <p className="text-xs font-semibold text-stone-500">{view === "year" ? day.toLocaleDateString(undefined, { month: "short" }) : day.toLocaleDateString(undefined, { weekday: "short", day: "numeric" })}</p>
      <div className="mt-2 space-y-1.5">
        {events.slice(0, view === "year" ? 2 : 4).map((event) => (
          <div key={event.id} draggable onDragStart={(drag) => drag.dataTransfer.setData("text/event-id", event.id)} className="group rounded-md bg-white px-2 py-1.5 text-xs shadow-sm ring-1 ring-stone-200">
            <button type="button" onClick={() => onEdit(event)} className="block w-full text-left">
              <span className="block truncate font-medium text-stone-900">{event.title}</span>
              <span className="text-stone-500">{event.time || "Anytime"}</span>
            </button>
            <button type="button" onClick={() => onDelete(event.id)} className="mt-1 hidden text-[11px] text-rose-600 group-hover:block">Delete</button>
          </div>
        ))}
        {events.length > 4 ? <p className="text-[11px] text-stone-500">+{events.length - 4} more</p> : null}
      </div>
    </div>
  );
}

function CalendarEventForm({ draft, setDraft }: { draft: CalendarEvent; setDraft: (draft: CalendarEvent) => void }) {
  return (
    <div className="mt-3 space-y-2">
      <InputLike value={draft.title} onChange={(value) => setDraft({ ...draft, title: value })} placeholder="Title" />
      <Textarea value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} rows={2} placeholder="Description" />
      <div className="grid gap-2 sm:grid-cols-2">
        <InputLike type="date" value={draft.date} onChange={(value) => setDraft({ ...draft, date: value })} />
        <InputLike type="time" value={draft.time} onChange={(value) => setDraft({ ...draft, time: value })} />
      </div>
      <InputLike value={draft.location} onChange={(value) => setDraft({ ...draft, location: value })} placeholder="Location" />
      <InputLike value={draft.participants} onChange={(value) => setDraft({ ...draft, participants: value })} placeholder="Participants" />
      <Textarea value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} rows={2} placeholder="Notes" />
      <div className="grid gap-2 sm:grid-cols-2">
        <SelectLike value={draft.recurring} onChange={(value) => setDraft({ ...draft, recurring: value as CalendarEvent["recurring"] })} options={["none", "daily", "weekly", "monthly"]} />
        <SelectLike value={draft.reminder} onChange={(value) => setDraft({ ...draft, reminder: value })} options={["none", "5 minutes before", "15 minutes before", "1 hour before", "1 day before"]} />
      </div>
      <InputLike value={draft.attachments.join(", ")} onChange={(value) => setDraft({ ...draft, attachments: splitList(value) })} placeholder="Attachments" />
    </div>
  );
}

function TasksModule({ id, tasks, projects, setTasks, setError }: { id: string; tasks: Task[]; projects: Project[]; setTasks: (tasks: Task[]) => void; setError: (error: string | null) => void; reload: () => Promise<void> }) {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<"today" | "upcoming" | "completed" | "overdue">("today");
  const [draft, setDraft] = useState({ title: "", priority: "medium", due_at: todayInput(), tags: "", project_id: "", recurring: "none" });
  const [editing, setEditing] = useState<Task | null>(null);
  const filtered = useMemo(() => filterTasks(tasks, filter, query), [filter, query, tasks]);
  const recommended = useMemo(() => tasks.filter((task) => !isDone(task) && (task.priority === "high" || isToday(task.due_at))).slice(0, 3), [tasks]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.title.trim()) return;
    setError(null);
    try {
      const task = await api.createTask({ title: draft.title.trim(), priority: draft.priority, project_id: draft.project_id || undefined });
      const updated = await api.updateTask(task.id, { due_at: draft.due_at || null, description: tagsDescription(draft.tags, draft.recurring) }).catch(() => task);
      setTasks([updated, ...tasks]);
      setDraft({ title: "", priority: "medium", due_at: todayInput(), tags: "", project_id: "", recurring: "none" });
    } catch {
      setError("Task could not be saved.");
    }
  };

  const update = async (task: Task, patch: Partial<Task>) => {
    const previous = tasks;
    setTasks(tasks.map((item) => (item.id === task.id ? { ...item, ...patch } : item)));
    try {
      const updated = await api.updateTask(task.id, patch);
      setTasks(previous.map((item) => (item.id === task.id ? updated : item)));
    } catch {
      setTasks(previous);
      setError("Task update failed.");
    }
  };

  const saveEdit = async () => {
    if (!editing) return;
    await update(editing, editing);
    setEditing(null);
  };

  return (
    <WorkspaceSection id={id} label="Tasks" title="To-do and priorities">
      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <aside className="space-y-4">
          <form onSubmit={create} className="rounded-lg border border-stone-200 bg-white p-4">
            <PanelTitle icon={<Plus className="h-4 w-4" />} title="Create task" />
            <div className="mt-3 space-y-2">
              <InputLike value={draft.title} onChange={(value) => setDraft({ ...draft, title: value })} placeholder="Task title" />
              <div className="grid gap-2 sm:grid-cols-2">
                <SelectLike value={draft.priority} onChange={(value) => setDraft({ ...draft, priority: value })} options={["low", "medium", "high"]} />
                <InputLike type="date" value={draft.due_at} onChange={(value) => setDraft({ ...draft, due_at: value })} />
              </div>
              <SelectLike value={draft.project_id} onChange={(value) => setDraft({ ...draft, project_id: value })} options={["", ...projects.map((project) => project.id)]} labels={{ "": "No project", ...Object.fromEntries(projects.map((project) => [project.id, project.name])) }} />
              <div className="grid gap-2 sm:grid-cols-2">
                <InputLike value={draft.tags} onChange={(value) => setDraft({ ...draft, tags: value })} placeholder="Tags" />
                <SelectLike value={draft.recurring} onChange={(value) => setDraft({ ...draft, recurring: value })} options={["none", "daily", "weekly", "monthly"]} />
              </div>
              <PrimaryButton type="submit">Add task</PrimaryButton>
            </div>
          </form>
          <div className="rounded-lg border border-stone-200 bg-white p-4">
            <PanelTitle icon={<Sparkles className="h-4 w-4" />} title="AI recommended priorities" />
            <div className="mt-3 space-y-2">
              {recommended.map((task) => <TaskRow key={task.id} task={task} onToggle={() => update(task, { status: isDone(task) ? "todo" : "completed" })} onEdit={() => setEditing(task)} onDelete={() => update(task, { status: "archived" })} />)}
              {!recommended.length ? <p className="text-sm text-stone-500">High priority and due-today tasks appear here automatically.</p> : null}
            </div>
          </div>
        </aside>
        <div className="rounded-lg border border-stone-200 bg-white p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap gap-1 rounded-lg border border-stone-200 bg-white p-1">
              {(["today", "upcoming", "completed", "overdue"] as const).map((item) => <button key={item} type="button" onClick={() => setFilter(item)} className={cn("h-8 rounded-md px-3 text-xs capitalize", filter === item ? "bg-stone-950 text-white" : "text-stone-500 hover:bg-stone-100")}>{item}</button>)}
            </div>
            <label className="flex h-9 min-w-0 items-center gap-2 rounded-lg border border-stone-200 px-3 text-sm text-stone-500 lg:w-72">
              <Search className="h-4 w-4" />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tasks" className="min-w-0 flex-1 bg-transparent outline-none" />
            </label>
          </div>
          <div className="mt-4 grid gap-2">
            {filtered.map((task) => <TaskRow key={task.id} task={task} onToggle={() => update(task, { status: isDone(task) ? "todo" : "completed" })} onEdit={() => setEditing(task)} onDelete={() => update(task, { status: "archived" })} />)}
            {!filtered.length ? <EmptyLine text="No tasks match this view." /> : null}
          </div>
        </div>
      </div>
      {editing ? <TaskEditDialog task={editing} projects={projects} onChange={setEditing} onClose={() => setEditing(null)} onSave={saveEdit} /> : null}
    </WorkspaceSection>
  );
}

function TaskRow({ task, onToggle, onEdit, onDelete }: { task: Task; onToggle: () => void; onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="flex items-center gap-3 rounded-lg bg-stone-50 px-3 py-2.5">
      <button type="button" onClick={onToggle} className="text-stone-500">{isDone(task) ? <Check className="h-4 w-4" /> : <Circle className="h-4 w-4" />}</button>
      <div className="min-w-0 flex-1">
        <p className={cn("truncate text-sm font-medium", isDone(task) ? "text-stone-400 line-through" : "text-stone-900")}>{task.title}</p>
        <p className="text-xs text-stone-500">{task.priority} priority {task.due_at ? `- due ${formatShortDate(task.due_at)}` : ""}</p>
      </div>
      <IconButton label="Edit task" onClick={onEdit}><Edit3 className="h-4 w-4" /></IconButton>
      <IconButton label="Delete task" onClick={onDelete}><Trash2 className="h-4 w-4" /></IconButton>
    </div>
  );
}

function TaskEditDialog({ task, projects, onChange, onClose, onSave }: { task: Task; projects: Project[]; onChange: (task: Task) => void; onClose: () => void; onSave: () => void }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-stone-950/25 px-4">
      <div className="w-full max-w-lg rounded-lg bg-white p-5 shadow-2xl">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-stone-950">Edit task</h3>
          <IconButton label="Close" onClick={onClose}><X className="h-4 w-4" /></IconButton>
        </div>
        <div className="mt-4 space-y-2">
          <InputLike value={task.title} onChange={(value) => onChange({ ...task, title: value })} />
          <Textarea value={task.description || ""} onChange={(event) => onChange({ ...task, description: event.target.value })} rows={3} />
          <div className="grid gap-2 sm:grid-cols-3">
            <SelectLike value={task.priority} onChange={(value) => onChange({ ...task, priority: value })} options={["low", "medium", "high"]} />
            <InputLike type="date" value={task.due_at?.slice(0, 10) || ""} onChange={(value) => onChange({ ...task, due_at: value })} />
            <SelectLike value={task.project_id || ""} onChange={(value) => onChange({ ...task, project_id: value || null })} options={["", ...projects.map((project) => project.id)]} labels={{ "": "No project", ...Object.fromEntries(projects.map((project) => [project.id, project.name])) }} />
          </div>
          <PrimaryButton onClick={onSave}>Save changes</PrimaryButton>
        </div>
      </div>
    </div>
  );
}

function ProjectsModule({ id, projects, tasks, notes, conversations, setProjects, setError, reload, onContinue }: { id: string; projects: Project[]; tasks: Task[]; notes: Note[]; conversations: Conversation[]; setProjects: (projects: Project[]) => void; setError: (error: string | null) => void; reload: () => Promise<void>; onContinue: (prompt: string) => void }) {
  const [draft, setDraft] = useState({ name: "", description: "", currentFocus: "", recommendedNextStep: "" });
  const [editingId, setEditingId] = useState<string | null>(null);
  const active = projects.filter((project) => project.status !== "archived");

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!draft.name.trim()) return;
    try {
      const project = await api.createProject(draft);
      setProjects([project, ...projects]);
      setDraft({ name: "", description: "", currentFocus: "", recommendedNextStep: "" });
    } catch {
      setError("Project could not be created.");
    }
  };

  const updateProject = async (project: Project, patch: Partial<Project>) => {
    const previous = projects;
    setProjects(projects.map((item) => (item.id === project.id ? { ...item, ...patch } : item)));
    try {
      await api.updateProject(project.id, patch);
      await reload();
    } catch {
      setProjects(previous);
      setError("Project update failed.");
    }
  };

  const archive = (project: Project) => updateProject(project, { status: "archived" });
  const remove = async (project: Project) => {
    if (!window.confirm(`Delete ${project.name}?`)) return;
    try {
      await api.deleteProject(project.id);
      setProjects(projects.filter((item) => item.id !== project.id));
    } catch {
      setError("Project could not be deleted.");
    }
  };

  return (
    <WorkspaceSection id={id} label="Projects" title="Project intelligence">
      <div className="grid gap-4 xl:grid-cols-[340px_1fr]">
        <form onSubmit={create} className="rounded-lg border border-stone-200 bg-white p-4">
          <PanelTitle icon={<Plus className="h-4 w-4" />} title="Create project" />
          <div className="mt-3 space-y-2">
            <InputLike value={draft.name} onChange={(value) => setDraft({ ...draft, name: value })} placeholder="Project name" />
            <Textarea value={draft.description} onChange={(event) => setDraft({ ...draft, description: event.target.value })} rows={2} placeholder="Description" />
            <InputLike value={draft.currentFocus} onChange={(value) => setDraft({ ...draft, currentFocus: value })} placeholder="Current focus" />
            <InputLike value={draft.recommendedNextStep} onChange={(value) => setDraft({ ...draft, recommendedNextStep: value })} placeholder="Recommended next step" />
            <PrimaryButton type="submit">Create project</PrimaryButton>
          </div>
        </form>
        <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
          {active.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              tasks={tasks.filter((task) => task.project_id === project.id)}
              notes={notes.filter((note) => note.project_id === project.id)}
              conversations={conversations.filter((conversation) => conversation.project_id === project.id)}
              editing={editingId === project.id}
              setEditing={(value) => setEditingId(value ? project.id : null)}
              onUpdate={(patch) => updateProject(project, patch)}
              onArchive={() => archive(project)}
              onDelete={() => remove(project)}
              onContinue={() => onContinue(`Continue project: ${project.name}\n\nCurrent focus: ${project.currentFocus || "None"}\nRecommended next step: ${project.recommendedNextStep || "None"}\nDo not ask me to re-explain. Restore the project context.`)}
            />
          ))}
          {!active.length ? <EmptyLine text="Create a project to anchor ongoing work." /> : null}
        </div>
      </div>
    </WorkspaceSection>
  );
}

function ProjectCard({ project, tasks, notes, conversations, editing, setEditing, onUpdate, onArchive, onDelete, onContinue }: { project: Project; tasks: Task[]; notes: Note[]; conversations: Conversation[]; editing: boolean; setEditing: (value: boolean) => void; onUpdate: (patch: Partial<Project>) => void; onArchive: () => void; onDelete: () => void; onContinue: () => void }) {
  const progress = projectProgress(project, tasks);
  const [draft, setDraft] = useState(project);
  useEffect(() => setDraft(project), [project]);
  return (
    <article className="rounded-lg border border-stone-200 bg-white p-4">
      {editing ? (
        <div className="space-y-2">
          <InputLike value={draft.name} onChange={(value) => setDraft({ ...draft, name: value })} />
          <Textarea value={draft.description || ""} onChange={(event) => setDraft({ ...draft, description: event.target.value })} rows={2} />
          <InputLike value={draft.currentFocus || ""} onChange={(value) => setDraft({ ...draft, currentFocus: value })} placeholder="Current focus" />
          <InputLike value={draft.recommendedNextStep || ""} onChange={(value) => setDraft({ ...draft, recommendedNextStep: value })} placeholder="Next step" />
          <div className="flex gap-2">
            <PrimaryButton onClick={() => { onUpdate(draft); setEditing(false); }}>Save</PrimaryButton>
            <GhostButton onClick={() => setEditing(false)}>Cancel</GhostButton>
          </div>
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="truncate font-semibold text-stone-950">{project.name}</h3>
              <p className="mt-1 line-clamp-2 text-sm leading-6 text-stone-500">{project.description || "No description yet."}</p>
            </div>
            <IconButton label="Edit project" onClick={() => setEditing(true)}><MoreHorizontal className="h-4 w-4" /></IconButton>
          </div>
          <div className="mt-4">
            <div className="h-2 overflow-hidden rounded-full bg-stone-100"><div className="h-full bg-[#3f5f4a]" style={{ width: `${progress}%` }} /></div>
            <p className="mt-1 text-xs text-stone-500">{progress}% progress from completed tasks</p>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
            <MiniStat label="Tasks" value={tasks.length} />
            <MiniStat label="Chats" value={conversations.length} />
            <MiniStat label="Notes" value={notes.length} />
          </div>
          <p className="mt-4 text-sm font-medium text-stone-950">{project.currentFocus || "No current focus"}</p>
          <p className="mt-1 text-sm leading-6 text-stone-500">{project.recommendedNextStep || "Add a next step to keep momentum."}</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <PrimaryButton onClick={onContinue}>Continue</PrimaryButton>
            <GhostButton onClick={onArchive}><Archive className="h-4 w-4" />Archive</GhostButton>
            <GhostButton onClick={onDelete}><Trash2 className="h-4 w-4" />Delete</GhostButton>
          </div>
        </>
      )}
    </article>
  );
}

function MeetingsModule({ id, meetings, setMeetings }: { id: string; meetings: Meeting[]; setMeetings: (meetings: Meeting[]) => void }) {
  const [draft, setDraft] = useState<Meeting>(() => blankMeeting());
  const [editingId, setEditingId] = useState<string | null>(null);
  const editing = meetings.find((meeting) => meeting.id === editingId) || null;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const clean = { ...draft, title: draft.title.trim() || "Untitled meeting", id: editingId || idFor("meeting") };
    setMeetings(editingId ? meetings.map((meeting) => (meeting.id === editingId ? clean : meeting)) : [clean, ...meetings]);
    setDraft(blankMeeting());
    setEditingId(null);
  };

  const edit = (meeting: Meeting) => {
    setEditingId(meeting.id);
    setDraft(meeting);
  };

  return (
    <WorkspaceSection id={id} label="Meetings" title="Meetings and follow-up">
      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <form onSubmit={submit} className="rounded-lg border border-stone-200 bg-white p-4">
          <PanelTitle icon={<Users className="h-4 w-4" />} title={editing ? "Edit meeting" : "Schedule meeting"} />
          <div className="mt-3 space-y-2">
            <InputLike value={draft.title} onChange={(value) => setDraft({ ...draft, title: value })} placeholder="Meeting title" />
            <div className="grid gap-2 sm:grid-cols-2"><InputLike type="date" value={draft.date} onChange={(value) => setDraft({ ...draft, date: value })} /><InputLike type="time" value={draft.time} onChange={(value) => setDraft({ ...draft, time: value })} /></div>
            <InputLike value={draft.link} onChange={(value) => setDraft({ ...draft, link: value })} placeholder="Online meeting link" />
            <InputLike value={draft.participants} onChange={(value) => setDraft({ ...draft, participants: value })} placeholder="Participants" />
            <Textarea value={draft.agenda} onChange={(event) => setDraft({ ...draft, agenda: event.target.value })} rows={2} placeholder="Agenda" />
            <Textarea value={draft.notes} onChange={(event) => setDraft({ ...draft, notes: event.target.value })} rows={2} placeholder="Meeting notes" />
            <Textarea value={draft.summary} onChange={(event) => setDraft({ ...draft, summary: event.target.value })} rows={2} placeholder="Meeting summary" />
            <Textarea value={draft.followUp} onChange={(event) => setDraft({ ...draft, followUp: event.target.value })} rows={2} placeholder="AI follow-up" />
            <PrimaryButton type="submit">{editing ? "Save meeting" : "Schedule meeting"}</PrimaryButton>
          </div>
        </form>
        <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-3">
          {meetings.map((meeting) => (
            <article key={meeting.id} className="rounded-lg border border-stone-200 bg-white p-4">
              <p className="font-semibold text-stone-950">{meeting.title}</p>
              <p className="mt-1 text-sm text-stone-500">{formatShortDate(meeting.date)} at {meeting.time || "anytime"}</p>
              {meeting.link ? <a href={meeting.link} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 rounded-lg bg-stone-950 px-3 py-2 text-sm font-medium text-white"><LinkIcon className="h-4 w-4" />Join</a> : null}
              <InfoBlock title="Agenda" value={meeting.agenda} />
              <InfoBlock title="Notes" value={meeting.notes} />
              <InfoBlock title="AI follow-up" value={meeting.followUp} />
              <div className="mt-3 flex gap-2">
                <GhostButton onClick={() => edit(meeting)}><Edit3 className="h-4 w-4" />Edit</GhostButton>
                <GhostButton onClick={() => setMeetings(meetings.filter((item) => item.id !== meeting.id))}><Trash2 className="h-4 w-4" />Delete</GhostButton>
              </div>
            </article>
          ))}
          {!meetings.length ? <EmptyLine text="Schedule meetings and keep notes, summaries, and follow-ups here." /> : null}
        </div>
      </div>
    </WorkspaceSection>
  );
}

function DocumentsModule({ id, documents, setDocuments, notes, setError, reload }: { id: string; documents: WorkspaceDocument[]; setDocuments: (documents: WorkspaceDocument[]) => void; notes: Note[]; setError: (error: string | null) => void; reload: () => Promise<void> }) {
  const [query, setQuery] = useState("");
  const [draft, setDraft] = useState<WorkspaceDocument>(() => blankDocument());
  const [selectedId, setSelectedId] = useState<string | null>(documents[0]?.id || null);
  const selected = documents.find((document) => document.id === selectedId) || documents[0] || null;
  const visible = documents.filter((document) => !document.archived && [document.title, document.content, document.folder, document.tags].join(" ").toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    if (!selectedId && documents[0]) setSelectedId(documents[0].id);
  }, [documents, selectedId]);

  const saveDocument = (document: WorkspaceDocument) => setDocuments(documents.map((item) => (item.id === document.id ? { ...document, updatedAt: new Date().toISOString() } : item)));
  const createLocal = () => {
    const clean = { ...draft, id: idFor("doc"), title: draft.title.trim() || "Untitled", updatedAt: new Date().toISOString() };
    setDocuments([clean, ...documents]);
    setSelectedId(clean.id);
    setDraft(blankDocument());
  };
  const createNote = async () => {
    if (!draft.content.trim()) return;
    try {
      const note = await api.createNote({ title: draft.title || undefined, content: draft.content, tags: splitList(draft.tags) });
      setDraft(blankDocument());
      await reload();
      setSelectedId(note.id);
    } catch {
      setError("Note could not be saved.");
    }
  };
  const attachFiles = (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []).map((file) => `${file.name} (${Math.round(file.size / 1024)} KB)`);
    setDraft({ ...draft, kind: "file", attachments: [...draft.attachments, ...files], title: draft.title || files[0] || "" });
    event.target.value = "";
  };
  const importedNotes = notes.map(noteToDocument);
  const combinedVisible = [...visible, ...importedNotes.filter((note) => [note.title, note.content].join(" ").toLowerCase().includes(query.toLowerCase()))];

  return (
    <WorkspaceSection id={id} label="Documents and Notes" title="Secure notes and documents">
      <div className="grid gap-4 xl:grid-cols-[320px_1fr_360px]">
        <aside className="rounded-lg border border-stone-200 bg-white p-4">
          <label className="flex h-9 items-center gap-2 rounded-lg border border-stone-200 px-3 text-sm text-stone-500">
            <Search className="h-4 w-4" /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search" className="min-w-0 flex-1 bg-transparent outline-none" />
          </label>
          <div className="mt-3 space-y-1">
            {combinedVisible.slice(0, 12).map((document) => (
              <button key={document.id} type="button" onClick={() => setSelectedId(document.id)} className={cn("w-full rounded-lg px-3 py-2 text-left hover:bg-stone-100", selected?.id === document.id && "bg-stone-100")}>
                <p className="truncate text-sm font-medium text-stone-900">{document.title}</p>
                <p className="truncate text-xs text-stone-500">{document.folder} - {document.kind}</p>
              </button>
            ))}
            {!combinedVisible.length ? <EmptyLine text="No documents found." /> : null}
          </div>
        </aside>
        <article className="rounded-lg border border-stone-200 bg-white p-4">
          {selected ? (
            <DocumentEditor document={selected} onChange={saveDocument} onArchive={() => saveDocument({ ...selected, archived: true })} onDelete={() => { setDocuments(documents.filter((item) => item.id !== selected.id)); setSelectedId(null); }} />
          ) : <EmptyLine text="Select or create a document." />}
        </article>
        <aside className="rounded-lg border border-stone-200 bg-white p-4">
          <PanelTitle icon={<Plus className="h-4 w-4" />} title="Create or upload" />
          <div className="mt-3 space-y-2">
            <InputLike value={draft.title} onChange={(value) => setDraft({ ...draft, title: value })} placeholder="Title" />
            <div className="grid gap-2 sm:grid-cols-2">
              <SelectLike value={draft.kind} onChange={(value) => setDraft({ ...draft, kind: value as WorkspaceDocument["kind"] })} options={["note", "document", "file"]} />
              <InputLike value={draft.folder} onChange={(value) => setDraft({ ...draft, folder: value })} placeholder="Folder" />
            </div>
            <InputLike value={draft.tags} onChange={(value) => setDraft({ ...draft, tags: value })} placeholder="Tags" />
            <Textarea value={draft.content} onChange={(event) => setDraft({ ...draft, content: event.target.value })} rows={6} placeholder="Markdown, checklists, tables, code blocks..." />
            <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-stone-300 px-3 py-4 text-sm text-stone-600 hover:bg-stone-50">
              <Upload className="h-4 w-4" />
              Upload PDFs, images, videos, audio, Word files
              <input type="file" multiple className="hidden" onChange={attachFiles} />
            </label>
            {draft.attachments.length ? <p className="text-xs text-stone-500">{draft.attachments.join(", ")}</p> : null}
            <div className="flex flex-wrap gap-2">
              <PrimaryButton onClick={createLocal}>Create document</PrimaryButton>
              <GhostButton onClick={createNote}>Create note</GhostButton>
            </div>
          </div>
        </aside>
      </div>
    </WorkspaceSection>
  );
}

function DocumentEditor({ document, onChange, onArchive, onDelete }: { document: WorkspaceDocument; onChange: (document: WorkspaceDocument) => void; onArchive: () => void; onDelete: () => void }) {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <InputLike value={document.title} onChange={(value) => onChange({ ...document, title: value })} />
        <div className="flex gap-1">
          <IconButton label="Pin" onClick={() => onChange({ ...document, pinned: !document.pinned })}><Paperclip className={cn("h-4 w-4", document.pinned && "text-stone-950")} /></IconButton>
          <IconButton label="Favorite" onClick={() => onChange({ ...document, favorite: !document.favorite })}><Sparkles className={cn("h-4 w-4", document.favorite && "text-stone-950")} /></IconButton>
          <IconButton label="Archive" onClick={onArchive}><Archive className="h-4 w-4" /></IconButton>
          <IconButton label="Delete" onClick={onDelete}><Trash2 className="h-4 w-4" /></IconButton>
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2">
        <InputLike value={document.folder} onChange={(value) => onChange({ ...document, folder: value })} />
        <InputLike value={document.tags} onChange={(value) => onChange({ ...document, tags: value })} />
      </div>
      <Textarea value={document.content} onChange={(event) => onChange({ ...document, content: event.target.value })} rows={16} />
      <p className="text-xs text-stone-500">Auto-saved locally. Secure storage and encryption-ready metadata are preserved in this document model.</p>
    </div>
  );
}

function ContinueWorking({ id, brief, tasks, projects, conversations, onContinue }: { id: string; brief: BuiltBrief; tasks: Task[]; projects: Project[]; conversations: Conversation[]; onContinue: (prompt: string) => void }) {
  const cards = [
    { title: "Continue yesterday", detail: brief.yesterday[0]?.title || "Resume from yesterday's summary.", prompt: buildBriefPrompt(brief) },
    { title: "Continue current project", detail: projects[0]?.name || "Choose a project anchor.", prompt: `Continue project: ${projects[0]?.name || "current project"}` },
    { title: "Continue last chat", detail: conversations[0]?.title || "Open the latest conversation.", prompt: `Continue the last chat: ${conversations[0]?.title || "latest conversation"}` },
    { title: "Continue unfinished task", detail: tasks.find((task) => !isDone(task))?.title || "No unfinished task selected.", prompt: `Help me finish this task: ${tasks.find((task) => !isDone(task))?.title || "next task"}` },
  ];
  return (
    <WorkspaceSection id={id} label="Continue Working" title="Restore context in one click">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <button key={card.title} type="button" onClick={() => onContinue(card.prompt)} className="rounded-lg border border-stone-200 bg-white p-4 text-left transition hover:-translate-y-0.5 hover:shadow-[0_14px_36px_rgba(28,25,23,0.08)]">
            <p className="font-semibold text-stone-950">{card.title}</p>
            <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-500">{card.detail}</p>
            <span className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-stone-950">Continue <ArrowRight className="h-4 w-4" /></span>
          </button>
        ))}
      </div>
    </WorkspaceSection>
  );
}

function RecentActivity({ id, dashboard, tasks, projects, notes, meetings, documents }: { id: string; dashboard: Dashboard | null; tasks: Task[]; projects: Project[]; notes: Note[]; meetings: Meeting[]; documents: WorkspaceDocument[] }) {
  const activity = [
    ...(dashboard?.recent_activity || []).map((item) => ({ title: item.title, detail: item.description || item.type, time: item.occurred_at, href: item.project_id ? `/projects/${item.project_id}` : null })),
    ...tasks.slice(0, 4).map((task) => ({ title: task.title, detail: `Task - ${task.status}`, time: task.created_at, href: "/tasks" })),
    ...projects.slice(0, 4).map((project) => ({ title: project.name, detail: "Project", time: project.updatedAt || project.created_at, href: `/projects/${project.id}` })),
    ...notes.slice(0, 4).map((note) => ({ title: note.title || "Untitled note", detail: "Note", time: note.created_at, href: "/notes" })),
    ...meetings.slice(0, 3).map((meeting) => ({ title: meeting.title, detail: "Meeting", time: `${meeting.date}T${meeting.time}`, href: null })),
    ...documents.slice(0, 3).map((document) => ({ title: document.title, detail: "Document", time: document.updatedAt, href: null })),
  ].sort((a, b) => (b.time || "").localeCompare(a.time || "")).slice(0, 12);
  return (
    <WorkspaceSection id={id} label="Recent Activity" title="Timeline">
      <div className="rounded-lg border border-stone-200 bg-white p-4">
        <div className="space-y-3">
          {activity.map((item, index) => (
            <a key={`${item.title}-${index}`} href={item.href || "#activity"} className="flex gap-3 rounded-lg px-2 py-2 hover:bg-stone-50">
              <span className="mt-1 h-2 w-2 rounded-full bg-stone-950" />
              <span className="min-w-0">
                <span className="block truncate text-sm font-medium text-stone-950">{item.title}</span>
                <span className="block text-xs text-stone-500">{item.detail} - {formatRelative(item.time)}</span>
              </span>
            </a>
          ))}
          {!activity.length ? <EmptyLine text="Activity appears as you use chat, projects, tasks, notes, meetings, documents, and memory." /> : null}
        </div>
      </div>
    </WorkspaceSection>
  );
}

function AISuggestions({ id, brief, tasks, projects, notes, onContinue }: { id: string; brief: BuiltBrief; tasks: Task[]; projects: Project[]; notes: Note[]; onContinue: (prompt: string) => void }) {
  const suggestions = [
    { title: "Continue your work", detail: brief.nextAction.title, action: () => onContinue(buildBriefPrompt(brief)) },
    { title: "Schedule this task", detail: tasks.find((task) => !task.due_at && !isDone(task))?.title || "Choose an unscheduled task.", action: () => document.getElementById("calendar")?.scrollIntoView({ behavior: "smooth" }) },
    { title: "Create a reminder", detail: "Turn an open loop into a reminder.", action: () => document.getElementById("calendar")?.scrollIntoView({ behavior: "smooth" }) },
    { title: "Convert chat into a project", detail: "Use the latest conversation as a project seed.", action: () => document.getElementById("projects")?.scrollIntoView({ behavior: "smooth" }) },
    { title: "Save this memory", detail: "Keep important preference or context in Synzept Knows You.", action: () => onContinue("Help me decide what memory from today's work should be saved.") },
    { title: "Finish unfinished work", detail: projects[0]?.recommendedNextStep || notes[0]?.title || "Pick one unfinished loop.", action: () => onContinue("Help me finish unfinished work from my dashboard.") },
  ];
  return (
    <WorkspaceSection id={id} label="AI Suggestions" title="Proactive next moves">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {suggestions.map((suggestion) => (
          <button key={suggestion.title} type="button" onClick={suggestion.action} className="rounded-lg border border-stone-200 bg-white p-4 text-left hover:bg-stone-50">
            <Sparkles className="h-4 w-4 text-[#3f5f4a]" />
            <p className="mt-3 font-semibold text-stone-950">{suggestion.title}</p>
            <p className="mt-1 line-clamp-2 text-sm leading-6 text-stone-500">{suggestion.detail}</p>
          </button>
        ))}
      </div>
    </WorkspaceSection>
  );
}

function WorkspaceSection({ id, label, title, action, children }: { id: string; label: string; title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-4">
      <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">{label}</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-stone-950">{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

function DashboardSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-3">
      <Skeleton className="h-28 rounded-lg" />
      <Skeleton className="h-28 rounded-lg" />
      <Skeleton className="h-28 rounded-lg" />
    </div>
  );
}

function PanelTitle({ icon, title }: { icon: React.ReactNode; title: string }) {
  return <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">{icon}{title}</p>;
}

function PrimaryButton({ children, className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} className={cn("inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-stone-950 px-4 text-sm font-semibold text-white hover:bg-stone-800 disabled:opacity-50", className)}>{children}</button>;
}

function GhostButton({ children, className, ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button type="button" {...props} className={cn("inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-stone-200 bg-white px-3 text-sm font-medium text-stone-700 hover:bg-stone-50", className)}>{children}</button>;
}

function IconButton({ label, children, onClick }: { label: string; children: React.ReactNode; onClick: () => void }) {
  return <button type="button" aria-label={label} title={label} onClick={onClick} className="grid h-8 w-8 place-items-center rounded-lg text-stone-500 hover:bg-stone-100 hover:text-stone-950">{children}</button>;
}

function InputLike({ value, onChange, placeholder, type = "text" }: { value: string; onChange: (value: string) => void; placeholder?: string; type?: string }) {
  return <input type={type} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="h-10 w-full rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-900 outline-none placeholder:text-stone-400 focus:border-stone-400" />;
}

function SelectLike({ value, onChange, options, labels }: { value: string; onChange: (value: string) => void; options: string[]; labels?: Record<string, string> }) {
  return (
    <select value={value} onChange={(event) => onChange(event.target.value)} className="h-10 w-full rounded-lg border border-stone-200 bg-white px-3 text-sm text-stone-900 outline-none focus:border-stone-400">
      {options.map((option) => <option key={option || "empty"} value={option}>{labels?.[option] || option || "None"}</option>)}
    </select>
  );
}

function EmptyLine({ text }: { text: string }) {
  return <p className="rounded-lg border border-dashed border-stone-300 bg-white px-4 py-6 text-sm leading-6 text-stone-500">{text}</p>;
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return <div className="rounded-lg bg-stone-50 px-2 py-2"><p className="font-semibold text-stone-950">{value}</p><p className="text-stone-500">{label}</p></div>;
}

function InfoBlock({ title, value }: { title: string; value: string }) {
  if (!value) return null;
  return <div className="mt-3 rounded-lg bg-stone-50 px-3 py-2"><p className="text-xs font-medium uppercase tracking-[0.12em] text-stone-500">{title}</p><p className="mt-1 text-sm leading-6 text-stone-700">{value}</p></div>;
}

type BuiltBrief = {
  greeting: string;
  subtitle: string;
  summary: string;
  nextAction: BriefItem;
  priorities: BriefItem[];
  attention: BriefItem[];
  yesterday: BriefItem[];
  openLoops: BriefItem[];
  reminders: BriefItem[];
};

function buildBrief({ s1Home, dailyBrief, dashboard, timeGreeting, name }: { s1Home: S1Home | null; dailyBrief: DailyBriefSnapshot | null; dashboard: Dashboard | null; timeGreeting: TimeGreeting; name: string | null }): BuiltBrief {
  const daily = dailyBrief ? toDaily(dailyBrief) : null;
  const s1 = s1Home?.home;
  const priorities = toBriefItems(daily?.whatMattersToday).concat(taskItems(dashboard?.priorities || dashboard?.tasks || [])).slice(0, 5);
  const openLoops = toBriefItems(daily?.openLoops).concat((s1?.open_loops || []).map((item) => ({ id: item.id, title: item.title, detail: item.detail }))).slice(0, 5);
  const yesterday = toBriefItems(daily?.whatChanged).concat((s1?.last_time || []).map((item) => ({ id: item.id, title: item.title, detail: item.detail }))).slice(0, 5);
  const nextAction = toBriefItem(daily?.recommendedNextStep) || (s1?.suggested_next_action ? { title: s1.suggested_next_action.title, detail: s1.suggested_next_action.reason } : null) || { title: "Choose one meaningful next action.", detail: "A clear next action makes the workspace easier to return to." };
  return {
    greeting: `${timeGreeting.greeting}, ${name || "there"}`,
    subtitle: timeGreeting.brief,
    summary: s1?.mission || dashboard?.briefing || "Synzept is ready to help you plan, continue work, and preserve context.",
    nextAction,
    priorities,
    attention: openLoops.concat(taskItems((dashboard?.unfinished_tasks || []).filter((task) => task.priority === "high"))).slice(0, 5),
    yesterday,
    openLoops,
    reminders: toBriefItems(daily?.upcomingPriorities).concat(priorities.slice(0, 2)).slice(0, 5),
  };
}

function useTimeGreeting(): TimeGreeting {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const interval = window.setInterval(() => setNow(new Date()), 30_000);
    return () => window.clearInterval(interval);
  }, []);
  return useMemo(() => {
    const hour = now.getHours();
    if (hour >= 5 && hour < 12) return { phase: "morning", greeting: "Good Morning", brief: "Here is what deserves your attention today." };
    if (hour >= 12 && hour < 17) return { phase: "afternoon", greeting: "Good Afternoon", brief: "Here is what still deserves your attention today." };
    if (hour >= 17 && hour < 21) return { phase: "evening", greeting: "Good Evening", brief: "Here is what changed today and what is still open." };
    return { phase: "night", greeting: "Good Night", brief: "Here is what happened today and what you should continue tomorrow." };
  }, [now]);
}

function toDaily(brief: DailyBriefSnapshot) {
  return {
    whatMattersToday: brief.whatMattersToday || [],
    openLoops: brief.openLoops || [],
    whatChanged: brief.whatChanged || brief.recentProgress || [],
    upcomingPriorities: brief.upcomingPriorities || [],
    recommendedNextStep: brief.recommendedNextStep || {},
  };
}

function toBriefItems(values?: Array<Record<string, unknown>>): BriefItem[] {
  return (values || []).map(toBriefItem).filter((item): item is BriefItem => Boolean(item?.title));
}

function toBriefItem(value?: Record<string, unknown>): BriefItem | null {
  if (!value) return null;
  const title = stringValue(value.title);
  if (!title) return null;
  return { title, detail: stringValue(value.detail) || stringValue(value.description) || stringValue(value.reason), priority: stringValue(value.priority), href: stringValue(value.href) };
}

function taskItems(tasks: Task[]): BriefItem[] {
  return tasks.filter((task) => !isDone(task)).map((task) => ({ id: task.id, title: task.title, detail: task.description || `${task.priority} priority`, priority: task.priority }));
}

function buildBriefPrompt(brief: BuiltBrief) {
  return [
    "Continue from my Synzept Dashboard.",
    `Summary: ${brief.summary}`,
    `Next action: ${brief.nextAction.title}`,
    `Priorities: ${brief.priorities.map((item) => item.title).join("; ") || "None visible"}`,
    `Open loops: ${brief.openLoops.map((item) => item.title).join("; ") || "None visible"}`,
    "Help me continue without asking me to re-explain.",
  ].join("\n");
}

function useLocalState<T>(key: string, fallback: T) {
  const [value, setValue] = useState<T>(fallback);
  useEffect(() => {
    try {
      const stored = localStorage.getItem(key);
      if (stored) setValue(JSON.parse(stored));
    } catch {
      /* ignore unavailable storage */
    }
  }, [key]);
  const update = (next: T) => {
    setValue(next);
    try {
      localStorage.setItem(key, JSON.stringify(next));
    } catch {
      /* ignore unavailable storage */
    }
  };
  return [value, update] as const;
}

function calendarDays(anchor: Date, view: CalendarView) {
  if (view === "day") return [anchor];
  if (view === "week") return Array.from({ length: 7 }, (_, i) => addDays(startOfWeek(anchor), i));
  if (view === "year") return Array.from({ length: 12 }, (_, i) => new Date(anchor.getFullYear(), i, 1));
  const first = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
  const start = startOfWeek(first);
  return Array.from({ length: 42 }, (_, i) => addDays(start, i));
}

function shiftAnchor(anchor: Date, view: CalendarView, direction: number) {
  if (view === "day") return addDays(anchor, direction);
  if (view === "week") return addDays(anchor, direction * 7);
  if (view === "year") return new Date(anchor.getFullYear() + direction, anchor.getMonth(), 1);
  return new Date(anchor.getFullYear(), anchor.getMonth() + direction, 1);
}

function formatCalendarTitle(anchor: Date, view: CalendarView) {
  if (view === "year") return String(anchor.getFullYear());
  if (view === "day") return anchor.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });
  if (view === "week") return `Week of ${startOfWeek(anchor).toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
  return anchor.toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

function filterTasks(tasks: Task[], filter: "today" | "upcoming" | "completed" | "overdue", query: string) {
  const q = query.toLowerCase().trim();
  return tasks.filter((task) => {
    if (task.status === "archived") return false;
    if (q && ![task.title, task.description, task.priority].some((value) => value?.toLowerCase().includes(q))) return false;
    if (filter === "completed") return isDone(task);
    if (filter === "overdue") return !isDone(task) && Boolean(task.due_at) && task.due_at!.slice(0, 10) < todayInput();
    if (filter === "today") return !isDone(task) && (!task.due_at || isToday(task.due_at));
    return !isDone(task);
  });
}

function projectProgress(project: Project, tasks: Task[]) {
  if (tasks.length) return Math.round((tasks.filter(isDone).length / tasks.length) * 100);
  return project.currentFocus && project.recommendedNextStep ? 35 : project.currentFocus || project.recommendedNextStep ? 18 : 0;
}

function noteToDocument(note: Note): WorkspaceDocument {
  return { id: note.id, title: note.title || "Untitled note", kind: "note", folder: "Synzept Notes", content: note.content, tags: (note.tags || []).join(", "), pinned: false, favorite: false, archived: false, attachments: [], updatedAt: note.created_at };
}

function blankEvent(date: Date): CalendarEvent {
  return { id: "", title: "", description: "", date: inputDate(date), time: "10:00", location: "", participants: "", notes: "", attachments: [], recurring: "none", reminder: "15 minutes before" };
}

function blankMeeting(): Meeting {
  return { id: "", title: "", date: todayInput(), time: "11:00", link: "", participants: "", agenda: "", notes: "", summary: "", followUp: "" };
}

function blankDocument(): WorkspaceDocument {
  return { id: "", title: "", kind: "note", folder: "Workspace", content: "", tags: "", pinned: false, favorite: false, archived: false, attachments: [], updatedAt: new Date().toISOString() };
}

function tagsDescription(tags: string, recurring: string) {
  return [tags ? `Tags: ${tags}` : "", recurring !== "none" ? `Recurring: ${recurring}` : ""].filter(Boolean).join("\n") || undefined;
}

function isDone(task: Task) {
  return ["completed", "done"].includes(task.status);
}

function isToday(value?: string | null) {
  return Boolean(value && value.slice(0, 10) === todayInput());
}

function todayInput() {
  return inputDate(new Date());
}

function inputDate(date: Date) {
  return date.toISOString().slice(0, 10);
}

function startOfDay(date: Date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate());
}

function startOfWeek(date: Date) {
  const copy = startOfDay(date);
  copy.setDate(copy.getDate() - copy.getDay());
  return copy;
}

function addDays(date: Date, days: number) {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

function splitList(value: string) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function idFor(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function stringValue(value: unknown) {
  return typeof value === "string" ? value : "";
}

function formatShortDate(value?: string | null) {
  if (!value) return "not scheduled";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "not scheduled";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatRelative(value?: string | null) {
  if (!value) return "recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
