"use client";

import { type ReactNode, useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import Link from "next/link";
import { ArrowRight, CheckSquare2, CircleHelp, ClipboardList, FileText, FolderKanban, Loader2, Play, Plus, Sparkles, Square, Target, WifiOff } from "lucide-react";
import { ChatInput } from "@/components/chat/chat-input";
import { MessageBubble } from "@/components/chat/message-bubble";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type AgentMemoryTimeline, type ChatMessage, type ContinuityAssistant, type DailyBriefSnapshot, type Dashboard, type Project, type Task } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useChatStore } from "@/stores/chat";
import { useWorkspaceStore } from "@/stores/workspace";
import { useAutoScroll } from "@frontend/hooks/use-auto-scroll";

const AGENT_DRAFT_KEY = "synzept_agent_draft";
const doneStatuses = new Set(["completed", "archived", "done"]);
const priorityRank: Record<string, number> = { high: 3, medium: 2, low: 1 };

const agentPrompts = [
  "What should I work on next?",
  "What is blocking progress?",
  "What changed recently?",
];

export function AgentPage() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const frameRef = useRef<number | null>(null);
  const pendingAssistantRef = useRef("");
  const user = useAuthStore((state) => state.user);
  const { dashboard, isLoading, hasFreshDashboard, setDashboard, setLoading } = useWorkspaceStore();
  const {
    conversations,
    activeConversationId,
    activeProjectId,
    messages,
    isStreaming,
    error: chatError,
    hasFreshConversations,
    setConversations,
    setActiveConversation,
    setActiveProject,
    setMessages,
    appendMessage,
    updateLastAssistant,
    removeLastMessage,
    setStreaming,
    setError: setChatError,
    reset,
  } = useChatStore();
  const [, startTransition] = useTransition();
  const [assistant, setAssistant] = useState<ContinuityAssistant | null>(null);
  const [dailyBrief, setDailyBrief] = useState<DailyBriefSnapshot | null>(null);
  const [memoryTimeline, setMemoryTimeline] = useState<AgentMemoryTimeline | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [input, setInput] = useState("");
  const [lastUserMessage, setLastUserMessage] = useState("");
  const [contextError, setContextError] = useState<string | null>(null);
  const [actionBusy, setActionBusy] = useState<string | null>(null);
  const [isOnline, setIsOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));

  useAutoScroll(scrollRef, [messages, isStreaming], true, !isStreaming);

  const loadContext = useCallback(() => {
    setLoading(true);
    setContextError(null);
    return Promise.all([
      api.getDashboard(),
      api.getContinuityAssistant().catch(() => null),
      api.getDailyBriefV2().catch(() => null),
      api.getAgentMemoryTimeline().catch(() => null),
      api.listProjects().catch(() => []),
    ])
      .then(([dashboardData, assistantData, briefData, memoryData, projectRows]) => {
        startTransition(() => {
          setDashboard(dashboardData);
          setAssistant(assistantData);
          setDailyBrief(briefData);
          setMemoryTimeline(memoryData);
          setProjects(projectRows);
        });
      })
      .catch(() => setContextError("Synzept Agent could not refresh its workspace context. Your data is still safe."))
      .finally(() => setLoading(false));
  }, [setDashboard, setLoading, startTransition]);

  const loadConversations = useCallback(async () => {
    if (conversations.length && hasFreshConversations()) return;
    try {
      const rows = await api.listConversations();
      startTransition(() => setConversations(rows));
    } catch {
      setChatError("Conversation history could not load. You can still ask Synzept a new question.");
    }
  }, [conversations.length, hasFreshConversations, setChatError, setConversations, startTransition]);

  useEffect(() => {
    if (dashboard && hasFreshDashboard()) {
      void Promise.all([
        api.getContinuityAssistant().then(setAssistant).catch(() => null),
        api.getDailyBriefV2().then(setDailyBrief).catch(() => null),
        api.getAgentMemoryTimeline().then(setMemoryTimeline).catch(() => null),
        api.listProjects().then(setProjects).catch(() => null),
      ]);
      return;
    }
    void loadContext();
  }, [dashboard, hasFreshDashboard, loadContext]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    const saved = localStorage.getItem(AGENT_DRAFT_KEY);
    if (saved) setInput(saved);
  }, []);

  useEffect(() => {
    if (input.trim()) localStorage.setItem(AGENT_DRAFT_KEY, input);
    else localStorage.removeItem(AGENT_DRAFT_KEY);
  }, [input]);

  useEffect(() => {
    const online = () => setIsOnline(true);
    const offline = () => setIsOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
      abortRef.current?.abort();
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, []);

  useEffect(() => {
    void api.trackEvent("agent_home_loaded", "agent", {
      active_projects: dashboard?.stats?.active_projects ?? projects.length,
      open_tasks: dashboard?.stats?.open_tasks ?? 0,
      returning: Boolean(dashboard?.returning_user?.is_returning),
    });
  }, [dashboard, projects.length]);

  const tasks = useMemo(() => dashboard?.unfinished_tasks || dashboard?.priorities || dashboard?.tasks || [], [dashboard]);
  const priorityTasks = useMemo(() => getPriorityTasks(tasks), [tasks]);
  const agentContext = useMemo(() => buildAgentContext({ dashboard, assistant, dailyBrief, memoryTimeline, projects, priorityTasks }), [assistant, dailyBrief, dashboard, memoryTimeline, priorityTasks, projects]);
  const welcomeMessage = useMemo<ChatMessage>(() => ({ id: "agent-welcome", role: "assistant", content: buildWelcomeMessage(agentContext, user?.display_name || user?.email || "there") }), [agentContext, user]);
  const visibleMessages = messages.length ? messages : [welcomeMessage];

  const flushAssistant = useCallback(() => {
    frameRef.current = null;
    updateLastAssistant(pendingAssistantRef.current);
  }, [updateLastAssistant]);

  const stop = () => abortRef.current?.abort();

  const newConversation = () => {
    abortRef.current?.abort();
    reset();
    setActiveProject(null);
    setChatError(null);
  };

  const runAgentAction = useCallback(
    async (action: AgentAction, announce = true) => {
      if (actionBusy) return;
      setChatError(null);
      setActionBusy(action.kind);
      try {
        const result = await executeAgentAction(action, { context: agentContext, projects, tasks });
        if (announce) appendMessage({ role: "assistant", content: result.message });
        void api.trackEvent("agent_action_completed", "agent", { kind: action.kind });
        await loadContext();
      } catch (err) {
        setChatError(err instanceof Error ? err.message : "Synzept Agent could not complete that action.");
      } finally {
        setActionBusy(null);
      }
    },
    [actionBusy, agentContext, appendMessage, loadContext, projects, setChatError, tasks],
  );

  const send = async (retry = false, prompt?: string) => {
    const text = retry ? lastUserMessage : (prompt || input).trim();
    if (!text || isStreaming) return;
    if (!isOnline) {
      setChatError("You appear to be offline. Reconnect and retry when ready.");
      return;
    }

    if (!retry) {
      setInput("");
      localStorage.removeItem(AGENT_DRAFT_KEY);
      setLastUserMessage(text);
      appendMessage({ role: "user", content: text });
      void api.trackEvent("agent_message_sent", "agent", {
        conversation_id: activeConversationId,
        project_id: activeProjectId,
        message_length: text.length,
      });

      const directAction = parseAgentAction(text, { context: agentContext, projects, tasks });
      if (directAction) {
        await runAgentAction(directAction);
        return;
      }
    }

    appendMessage({ role: "assistant", content: "" });
    pendingAssistantRef.current = "";
    setChatError(null);
    setStreaming(true);
    abortRef.current = new AbortController();

    try {
      let assistantText = "";
      let gotToken = false;
      const enrichedMessage = enrichAgentPrompt(text, agentContext);
      for await (const event of api.streamMessage(
        enrichedMessage,
        activeConversationId ?? undefined,
        activeProjectId ?? undefined,
        abortRef.current.signal,
      )) {
        if ((event.type === "meta" || event.type === "done") && event.conversation_id) setActiveConversation(event.conversation_id);
        if (event.type === "token" && event.content) {
          gotToken = true;
          assistantText += event.content;
          pendingAssistantRef.current = assistantText;
          if (!frameRef.current) frameRef.current = requestAnimationFrame(flushAssistant);
        }
      }
      if (!gotToken) {
        const result = await api.sendMessage(enrichedMessage, activeConversationId ?? undefined, activeProjectId ?? undefined);
        setActiveConversation(result.conversation_id);
        updateLastAssistant(result.reply);
      }
      const syncedConversationId = useChatStore.getState().activeConversationId;
      if (syncedConversationId) {
        const rows = await api.getMessages(syncedConversationId);
        startTransition(() => {
          setMessages(rows.map((row) => ({ id: row.id, role: row.role as "user" | "assistant" | "system", content: row.content, metadata: row.metadata })));
        });
      }
      void loadConversations();
      void loadContext();
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      setChatError(aborted ? "Response stopped. You can continue from here." : err instanceof Error ? err.message : "Synzept Agent could not respond.");
      removeLastMessage();
    } finally {
      if (pendingAssistantRef.current) updateLastAssistant(pendingAssistantRef.current);
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      abortRef.current = null;
      setStreaming(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col bg-surface">
      <header className="shrink-0 border-b border-border bg-white/90 px-4 py-3 backdrop-blur md:px-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-[0.14em] text-muted">
              <Sparkles className="h-3.5 w-3.5" />
              Synzept Agent
            </p>
            <h1 className="mt-1 truncate text-xl font-semibold text-stone-950">Welcome back, {firstName(user?.display_name || user?.email || "there")}.</h1>
          </div>
          <div className="flex items-center gap-2">
            {isLoading && <Loader2 className="h-4 w-4 animate-spin text-muted" />}
            {isStreaming ? (
              <Button variant="outline" size="sm" onClick={stop}>
                <Square className="h-4 w-4 md:mr-1.5" />
                <span className="hidden md:inline">Stop</span>
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={newConversation}>
                <Plus className="h-4 w-4 md:mr-1.5" />
                <span className="hidden md:inline">New</span>
              </Button>
            )}
          </div>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 xl:grid-cols-[minmax(0,1fr)_280px]">
        <section className="flex min-h-0 flex-col border-r border-border bg-white/35">
          <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-5 md:px-6">
              <RecoveryBanner message={contextError || chatError} onRetry={() => (chatError && lastUserMessage ? send(true) : loadContext())} />
              {isLoading && !dashboard ? <AgentSkeleton /> : <AgentBrief context={agentContext} actionBusy={actionBusy} onAction={runAgentAction} />}
              <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
                <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-3">
                  <div>
                    <p className="text-sm font-semibold text-stone-950">Talk to your Agent</p>
                    <p className="mt-1 text-xs text-muted-foreground">Ask what to do next, what changed, or what you are forgetting.</p>
                  </div>
                  <PromptRail onPrompt={(prompt) => send(false, prompt)} disabled={isStreaming} />
                </div>
                <div className="mt-4 space-y-4">
                  {visibleMessages.map((message, index) => (
                    <MessageBubble
                      key={message.id || index}
                      role={message.role as "user" | "assistant"}
                      content={message.content}
                      messageId={message.id}
                      isStreaming={isStreaming && index === visibleMessages.length - 1 && message.role === "assistant"}
                    />
                  ))}
                </div>
              </section>
              <MobileSupportPanel context={agentContext} projects={projects} />
            </div>
          </div>
          {!isOnline && !chatError && (
            <p className="flex items-center justify-center gap-2 px-4 pb-2 text-center text-sm text-amber-700">
              <WifiOff className="h-4 w-4" />
              Offline. Reconnect to send.
            </p>
          )}
          <ChatInput value={input} onChange={setInput} onSubmit={() => send()} disabled={isStreaming} placeholder="Ask Synzept anything about your work, goals, projects, or progress." />
        </section>

        <aside className="hidden min-h-0 overflow-y-auto bg-surface p-4 xl:block">
          <AgentSupportPanel context={agentContext} projects={projects} />
        </aside>
      </div>
    </div>
  );
}

function AgentBrief({ context, actionBusy, onAction }: { context: AgentContext; actionBusy: string | null; onAction: (action: AgentAction) => void }) {
  return (
    <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
      <div className="grid gap-3 lg:grid-cols-[1fr_1fr]">
        <EssentialsCard label="Current Goal" value={context.goal} icon={<Target className="h-4 w-4" />} href="/knows-you" />
        <EssentialsCard label="Current Focus" value={context.workingOn} icon={<FolderKanban className="h-4 w-4" />} href={context.workingHref} />
      </div>
      <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1.2fr]">
        <EssentialsCard label="Biggest Blocker" value={context.blocker} icon={<CircleHelp className="h-4 w-4" />} href="/knows-you" />
        <EssentialsCard label="Recommended Next Action" value={context.nextStep} icon={<ArrowRight className="h-4 w-4" />} href={context.nextHref} strong />
      </div>
      <div className="mt-4 border-t border-border pt-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-[0.12em] text-muted">Take action</p>
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <ActionButton
            icon={<Play className="h-4 w-4" />}
            label="Start Working"
            busy={actionBusy === "start_working"}
            onClick={() => onAction({ kind: "start_working" })}
          />
          <ActionButton
            icon={<ClipboardList className="h-4 w-4" />}
            label="Create Task"
            busy={actionBusy === "create_task"}
            onClick={() => onAction({ kind: "create_task", title: context.nextStep, projectId: context.projectId })}
          />
          <ActionButton
            icon={<FileText className="h-4 w-4" />}
            label="Add Note"
            busy={actionBusy === "add_note"}
            onClick={() => onAction({ kind: "add_note", title: "Agent recommendation", content: context.nextStep, projectId: context.projectId })}
          />
          <ActionButton
            icon={<CheckSquare2 className="h-4 w-4" />}
            label="Mark Complete"
            busy={actionBusy === "complete_task"}
            onClick={() => onAction({ kind: "complete_task", title: context.nextStep, taskId: context.taskId })}
          />
        </div>
      </div>
    </section>
  );
}

function EssentialsCard({ label, value, icon, href, strong = false }: { label: string; value: string; icon: ReactNode; href: string; strong?: boolean }) {
  return (
    <Link
      href={href}
      className={`group rounded-md border p-3 transition ${strong ? "border-stone-900 bg-stone-950 text-white hover:bg-stone-900" : "border-border bg-stone-50 hover:bg-stone-100"}`}
    >
      <div className="flex items-center justify-between gap-2">
        <span className={strong ? "text-stone-300" : "text-stone-500"}>{icon}</span>
        <ArrowRight className={`h-3.5 w-3.5 transition group-hover:translate-x-0.5 ${strong ? "text-stone-500 group-hover:text-white" : "text-stone-300 group-hover:text-stone-700"}`} />
      </div>
      <p className={`mt-3 text-[11px] font-medium uppercase tracking-[0.12em] ${strong ? "text-stone-400" : "text-muted"}`}>{label}</p>
      <p className="mt-1 line-clamp-2 min-h-10 text-sm font-semibold leading-5">{value}</p>
    </Link>
  );
}

function ActionButton({ icon, label, busy, onClick }: { icon: ReactNode; label: string; busy: boolean; onClick: () => void }) {
  return (
    <Button type="button" variant="outline" size="sm" onClick={onClick} disabled={busy} className="justify-start">
      {busy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <span className="mr-2 text-stone-500">{icon}</span>}
      {label}
    </Button>
  );
}

function PromptRail({ onPrompt, disabled }: { onPrompt: (prompt: string) => void; disabled: boolean }) {
  return (
    <div className="flex max-w-full gap-2 overflow-x-auto">
      {agentPrompts.map((prompt) => (
        <button
          key={prompt}
          type="button"
          disabled={disabled}
          onClick={() => onPrompt(prompt)}
          className="shrink-0 rounded-full border border-border bg-white px-3 py-2 text-xs font-medium text-stone-700 transition hover:border-stone-300 hover:bg-stone-50 disabled:opacity-50"
        >
          {prompt}
        </button>
      ))}
    </div>
  );
}

function AgentSupportPanel({ context, projects }: { context: AgentContext; projects: Project[] }) {
  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Recent Activity</p>
        <div className="mt-3 space-y-2">
          {(context.memoryHighlights.length ? context.memoryHighlights.slice(0, 3) : ["No recent activity yet."]).map((item) => (
            <p key={item} className="line-clamp-2 rounded-md bg-stone-50 px-3 py-2 text-sm leading-5 text-stone-700">{item}</p>
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-border bg-white p-4 shadow-soft">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Progress</p>
        <div className="mt-3 grid gap-2">
          <p className="rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-700">{projects.length} active project{projects.length === 1 ? "" : "s"}</p>
          <p className="rounded-md bg-stone-50 px-3 py-2 text-sm text-stone-700">{context.incompleteGoals.length} incomplete goal{context.incompleteGoals.length === 1 ? "" : "s"}</p>
        </div>
      </section>

      <Link href="/knows-you" className="flex items-center justify-between rounded-lg border border-border bg-white p-4 text-sm font-medium text-stone-950 shadow-soft hover:bg-stone-50">
        Review what Synzept knows
        <ArrowRight className="h-4 w-4" />
      </Link>
    </div>
  );
}

function MobileSupportPanel({ context, projects }: { context: AgentContext; projects: Project[] }) {
  return (
    <section className="grid gap-3 xl:hidden">
      <div className="rounded-lg border border-border bg-white p-3 shadow-soft">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Recent Activity</p>
        <p className="mt-2 line-clamp-2 text-sm text-stone-700">{context.memoryHighlights[0] || "No recent activity yet."}</p>
      </div>
      <div className="rounded-lg border border-border bg-white p-3 shadow-soft">
        <p className="text-xs font-medium uppercase tracking-[0.14em] text-muted">Progress</p>
        <p className="mt-2 text-sm text-stone-700">{projects.length} active project{projects.length === 1 ? "" : "s"} / {context.incompleteGoals.length} incomplete goal{context.incompleteGoals.length === 1 ? "" : "s"}</p>
      </div>
    </section>
  );
}

function AgentSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-28 rounded-lg" />
      <Skeleton className="h-10 rounded-full" />
    </div>
  );
}

type AgentAction =
  | { kind: "create_project"; title: string }
  | { kind: "create_goal"; title: string }
  | { kind: "create_task"; title: string; projectId?: string | null }
  | { kind: "update_project_status"; title: string; status: "active" | "paused" | "completed" }
  | { kind: "add_note"; title?: string; content: string; projectId?: string | null }
  | { kind: "create_timeline_event"; title: string; description?: string; projectId?: string | null }
  | { kind: "create_open_loop"; title: string; projectId?: string | null }
  | { kind: "complete_task"; title: string; taskId?: string | null }
  | { kind: "start_working" };

type AgentActionContext = {
  context: AgentContext;
  projects: Project[];
  tasks: Task[];
};

type AgentActionResult = {
  message: string;
};

async function executeAgentAction(action: AgentAction, { context, projects, tasks }: AgentActionContext): Promise<AgentActionResult> {
  if (action.kind === "create_project") {
    const project = await api.createProject({
      name: action.title,
      currentFocus: action.title,
      recommendedNextStep: "Ask Synzept Agent for the next concrete action.",
      status: "active",
    });
    return { message: `Done - created project "${project.name}".` };
  }

  if (action.kind === "create_goal") {
    const goal = await api.createGoal({ title: action.title, description: "Created by Synzept Agent." });
    return { message: `Done - added "${goal.title}" as a goal.` };
  }

  if (action.kind === "create_task") {
    const task = await api.createTask({
      title: action.title,
      priority: "medium",
      project_id: action.projectId || context.projectId || undefined,
    });
    return { message: `Done - created task "${task.title}".` };
  }

  if (action.kind === "update_project_status") {
    const project = findProject(projects, action.title);
    if (!project) throw new Error(`I could not find a project matching "${action.title}".`);
    const updated = await api.updateProject(project.id, { status: action.status });
    return { message: `Done - updated "${updated.name}" to ${action.status}.` };
  }

  if (action.kind === "add_note") {
    const note = await api.createNote({
      title: action.title || "Agent note",
      content: action.content,
      project_id: action.projectId || context.projectId || undefined,
      tags: ["agent"],
    });
    return { message: `Done - added note "${note.title || "Agent note"}".` };
  }

  if (action.kind === "create_timeline_event") {
    const event = await api.createTimelineEvent({
      eventType: "progress",
      title: action.title,
      description: action.description || "Created by Synzept Agent.",
      eventDate: new Date().toISOString().slice(0, 10),
      importance: 0.7,
      projectId: action.projectId || context.projectId || null,
    });
    return { message: `Done - added timeline event "${event.title}".` };
  }

  if (action.kind === "create_open_loop") {
    const projectId = action.projectId || context.projectId;
    if (!projectId) throw new Error("Choose or create a project first so I can attach that open loop.");
    const loop = await api.createOpenLoop(projectId, { title: action.title, status: "open" });
    return { message: `Done - created open loop "${loop.title}".` };
  }

  if (action.kind === "complete_task") {
    const task = action.taskId ? tasks.find((item) => item.id === action.taskId) : findTask(tasks, action.title);
    if (task) {
      const updated = await api.updateTask(task.id, { status: "completed" });
      return { message: `Done - marked task "${updated.title}" complete.` };
    }
    await api.createTimelineEvent({
      eventType: "achievement",
      title: action.title,
      description: "Marked complete from Synzept Agent.",
      eventDate: new Date().toISOString().slice(0, 10),
      importance: 0.75,
      projectId: context.projectId,
    });
    return { message: `Done - recorded "${action.title}" as complete on the timeline.` };
  }

  if (action.kind === "start_working") {
    if (context.taskId) {
      const task = await api.updateTask(context.taskId, { status: "in_progress" });
      return { message: `Done - moved "${task.title}" to in progress.` };
    }
    const task = await api.createTask({
      title: context.nextStep,
      priority: "high",
      project_id: context.projectId || undefined,
    });
    await api.updateTask(task.id, { status: "in_progress" });
    return { message: `Done - created "${task.title}" and started it.` };
  }

  return { message: "Done." };
}

function parseAgentAction(message: string, { context, projects, tasks }: AgentActionContext): AgentAction | null {
  const text = normalizeCommand(message);
  const projectMatch = text.match(/^create (?:a )?project (?:called |named )?(.+)$/i);
  if (projectMatch) return { kind: "create_project", title: cleanActionTitle(projectMatch[1]) };

  const goalMatch = text.match(/^(?:add|create) (.+?) as (?:a )?goal$/i) || text.match(/^create (?:a )?goal (?:called |named )?(.+)$/i);
  if (goalMatch) return { kind: "create_goal", title: cleanActionTitle(goalMatch[1]) };

  const taskMatch = text.match(/^(?:create|add) (?:a )?task (?:called |named )?(.+)$/i);
  if (taskMatch) return { kind: "create_task", title: cleanActionTitle(taskMatch[1]), projectId: context.projectId };

  const noteMatch = text.match(/^add (?:a )?note(?: to (.+?))?(?::| about)? (.+)$/i);
  if (noteMatch) {
    const project = noteMatch[1] ? findProject(projects, noteMatch[1]) : null;
    return { kind: "add_note", title: "Agent note", content: cleanActionTitle(noteMatch[2]), projectId: project?.id || context.projectId };
  }

  const loopMatch = text.match(/^(?:create|add) (?:an? )?open loop(?: called | named )?(.+)$/i);
  if (loopMatch) return { kind: "create_open_loop", title: cleanActionTitle(loopMatch[1]), projectId: context.projectId };

  const timelineMatch = text.match(/^(?:create|add) (?:a )?timeline event(?: called | named )?(.+)$/i);
  if (timelineMatch) return { kind: "create_timeline_event", title: cleanActionTitle(timelineMatch[1]), projectId: context.projectId };

  const statusMatch = text.match(/^set (.+?) status to (active|paused|completed)$/i);
  if (statusMatch) return { kind: "update_project_status", title: cleanActionTitle(statusMatch[1]), status: statusMatch[2].toLowerCase() as "active" | "paused" | "completed" };

  const projectCompleteMatch = text.match(/^mark project (.+?) complete$/i);
  if (projectCompleteMatch) return { kind: "update_project_status", title: cleanActionTitle(projectCompleteMatch[1]), status: "completed" };

  const completeMatch = text.match(/^mark (.+?) complete$/i);
  if (completeMatch) {
    const title = cleanActionTitle(completeMatch[1]);
    const task = findTask(tasks, title);
    const project = findProject(projects, title);
    if (task || !project) return { kind: "complete_task", title, taskId: task?.id };
    return { kind: "update_project_status", title, status: "completed" };
  }

  return null;
}

function normalizeCommand(value: string) {
  return value.trim().replace(/[.!?]+$/, "");
}

function cleanActionTitle(value: string) {
  return value.trim().replace(/^["']|["']$/g, "");
}

function findProject(projects: Project[], query: string) {
  const target = query.toLowerCase().trim();
  return projects.find((project) => project.name.toLowerCase() === target) || projects.find((project) => project.name.toLowerCase().includes(target));
}

function findTask(tasks: Task[], query: string) {
  const target = query.toLowerCase().trim();
  return tasks.find((task) => task.title.toLowerCase() === target) || tasks.find((task) => task.title.toLowerCase().includes(target));
}

type AgentContext = {
  workingOn: string;
  workingHref: string;
  projectId: string | null;
  taskId: string | null;
  blocker: string;
  goal: string;
  nextStep: string;
  nextHref: string;
  returnSummary: string;
  projectsNeedingAttention: string[];
  memoryHighlights: string[];
  incompleteGoals: string[];
  importantDecisions: string[];
  recallContext: string;
  why: string[];
};

function buildAgentContext({
  dashboard,
  assistant,
  dailyBrief,
  memoryTimeline,
  projects,
  priorityTasks,
}: {
  dashboard: Dashboard | null;
  assistant: ContinuityAssistant | null;
  dailyBrief: DailyBriefSnapshot | null;
  memoryTimeline: AgentMemoryTimeline | null;
  projects: Project[];
  priorityTasks: Task[];
}): AgentContext {
  const activeProjects = (projects.length ? projects : dashboard?.projects || []).filter((project) => !doneStatuses.has(project.status));
  const leadProject = activeProjects.find((project) => project.currentFocus || project.recommendedNextStep) || activeProjects[0];
  const recommendation = dashboard?.returning_user?.recommended_next_step;
  const briefNext = textFromRecord(dailyBrief?.recommendedNextStep, "title") || "Create your next project anchor.";
  const openLoops = assistant?.open_loops || dashboard?.daily?.carry_forward || [];
  const projectRisks = assistant?.project_risks?.map((risk) => risk.project_title) || [];
  const returning = dashboard?.returning_user;
  const counts = returning?.activity_counts;
  const changed = counts
    ? `${counts.projects_updated} projects changed\n${openLoops.length} open loops remain\n${counts.milestones_reached} milestones completed`
    : `${activeProjects.length} active projects\n${openLoops.length} open loops remain\n${assistant?.recent_progress?.length || 0} recent progress updates`;
  const nextStep = memoryTimeline?.recommended_next_step || recommendation?.title || leadProject?.recommendedNextStep || assistant?.recommendation?.title || priorityTasks[0]?.title || briefNext;
  const projectId = leadProject?.id && !leadProject.id.startsWith("sample-") ? leadProject.id : null;
  const taskId = priorityTasks[0]?.id || null;
  const memoryHighlights = memoryTimeline?.what_changed?.length ? memoryTimeline.what_changed : memoryTimeline?.items?.slice(0, 5).map((item) => item.title) || [];
  const unfinished = memoryTimeline?.unfinished?.length ? memoryTimeline.unfinished : openLoops;
  const recallContext = [
    "Agent memory timeline:",
    ...(memoryTimeline?.items || []).slice(0, 12).map((item) => `- ${item.happened_at}: ${item.type} - ${item.title}. Why it mattered: ${item.why_it_mattered}`),
    memoryTimeline?.incomplete_goals?.length ? `Incomplete goals: ${memoryTimeline.incomplete_goals.join("; ")}` : "",
    memoryTimeline?.important_decisions?.length ? `Important decisions: ${memoryTimeline.important_decisions.join("; ")}` : "",
    memoryTimeline?.unfinished?.length ? `Unfinished work: ${memoryTimeline.unfinished.join("; ")}` : "",
  ].filter(Boolean).join("\n");

  return {
    workingOn: leadProject?.currentFocus || leadProject?.name || "Set one project focus so Synzept can help you move.",
    workingHref: projectId ? `/projects/${projectId}` : "/projects",
    projectId,
    taskId,
    blocker: unfinished[0] || assistant?.recommendation?.reason || "No blocker is visible yet.",
    goal: memoryTimeline?.incomplete_goals?.[0] || assistant?.priorities?.[0] || dashboard?.focus_areas?.[0] || "Clarify your most important goal in Synzept Knows You.",
    nextStep,
    nextHref: recommendation?.href || (projectId ? `/projects/${projectId}` : "/projects"),
    returnSummary: `Since your last visit:\n${memoryHighlights.length ? memoryHighlights.slice(0, 4).join("\n") : changed}\n\nWhat remains unfinished:\n${unfinished.slice(0, 4).join("\n") || "No unfinished work is visible."}\n\nRecommended next step:\n${nextStep}`,
    projectsNeedingAttention: projectRisks,
    memoryHighlights,
    incompleteGoals: memoryTimeline?.incomplete_goals || [],
    importantDecisions: memoryTimeline?.important_decisions || [],
    recallContext,
    why: [
      `I can see ${activeProjects.length} active project${activeProjects.length === 1 ? "" : "s"}.`,
      `I can see ${unfinished.length} open loop${unfinished.length === 1 ? "" : "s"} or unfinished item${unfinished.length === 1 ? "" : "s"}.`,
      memoryTimeline?.items?.length ? `I can recall ${memoryTimeline.items.length} timeline event${memoryTimeline.items.length === 1 ? "" : "s"} with when and why they mattered.` : "I will build long-term recall as you create goals, projects, decisions, notes, and timeline events.",
      assistant?.learned_patterns?.[0]?.evidence?.[0]
        ? `I know one pattern because ${assistant.learned_patterns[0].evidence[0].count} ${assistant.learned_patterns[0].evidence[0].source} signal${assistant.learned_patterns[0].evidence[0].count === 1 ? "" : "s"} support it.`
        : "I use your profile, projects, tasks, timeline, daily brief, and accepted learnings as context.",
    ],
  };
}

function buildWelcomeMessage(context: AgentContext, name: string) {
  const changed = context.memoryHighlights.length ? context.memoryHighlights.slice(0, 4) : ["No major changes are visible yet."];
  const unfinished = context.blocker && context.blocker !== "No blocker is visible yet." ? [context.blocker, ...context.incompleteGoals.slice(0, 3)] : context.incompleteGoals.slice(0, 4);
  return `Welcome back, ${firstName(name)}.\n\nWhat changed:\n- ${changed.join("\n- ")}\n\nWhat remains unfinished:\n- ${(unfinished.length ? unfinished : ["No unfinished work is visible."]).join("\n- ")}\n\nRecommended next step:\n${context.nextStep}\n\nAsk me what you were working on last week, what changed this month, which goals are incomplete, or what decisions you made.`;
}

function enrichAgentPrompt(message: string, context: AgentContext) {
  return [
    message,
    "",
    "Use this Synzept Agent context when it is relevant. Be direct, recommend concrete actions, and explain why you know something when making a recommendation.",
    "When the user asks you to create or update workspace items, tell them Synzept can take that action directly from the Agent.",
    `Working on: ${context.workingOn}`,
    `Biggest blocker: ${context.blocker}`,
    `Most important goal: ${context.goal}`,
    `Recommended next step: ${context.nextStep}`,
    context.recallContext,
  ].join("\n");
}

function getPriorityTasks(tasks: Task[]) {
  return tasks
    .filter((task) => !doneStatuses.has(task.status))
    .slice()
    .sort((a, b) => {
      const aOverdue = a.due_at && new Date(a.due_at) < startOfToday() ? 1 : 0;
      const bOverdue = b.due_at && new Date(b.due_at) < startOfToday() ? 1 : 0;
      if (aOverdue !== bOverdue) return bOverdue - aOverdue;
      return (priorityRank[b.priority] || 0) - (priorityRank[a.priority] || 0);
    });
}

function textFromRecord(value: Record<string, unknown> | undefined, key: string) {
  const text = value?.[key];
  return typeof text === "string" ? text : "";
}

function startOfToday() {
  const date = new Date();
  date.setHours(0, 0, 0, 0);
  return date;
}

function firstName(value: string) {
  return value.split("@")[0].split(" ")[0] || "there";
}
