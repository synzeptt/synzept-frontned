"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { ArrowRight, ChevronRight, Loader2, PanelRightOpen, Plus, RotateCcw, Square, WifiOff, X } from "lucide-react";
import { ChatInput } from "@/components/chat/chat-input";
import { MessageBubble } from "@/components/chat/message-bubble";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { api, type ContinuityMode, type Conversation, type Dashboard, type Project } from "@/lib/api";
import { useChatStore } from "@/stores/chat";
import { useAutoScroll } from "@frontend/hooks/use-auto-scroll";

const CHAT_DRAFT_KEY = "synzept_chat_draft";

export function ChatWorkspace() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const frameRef = useRef<number | null>(null);
  const pendingAssistantRef = useRef("");
  const [input, setInput] = useState("");
  const [lastUserMessage, setLastUserMessage] = useState("");
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [selectingConversationId, setSelectingConversationId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [continuityMode, setContinuityMode] = useState<ContinuityMode | null>(null);
  const [continuityOpen, setContinuityOpen] = useState(false);
  const [isOnline, setIsOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));
  const [isPending, startTransition] = useTransition();
  const {
    conversations,
    activeConversationId,
    activeProjectId,
    messages,
    messagesByConversation,
    isStreaming,
    error,
    hasFreshConversations,
    setConversations,
    setActiveConversation,
    setActiveProject,
    setMessages,
    appendMessage,
    updateLastAssistant,
    removeLastMessage,
    setStreaming,
    setError,
    reset,
  } = useChatStore();

  useAutoScroll(scrollRef, [messages, isStreaming], true, !isStreaming);

  const loadConversations = useCallback(async (background = false) => {
    if (!background) setLoadingHistory(true);
    try {
      const [conversationRows, projectRows] = await Promise.all([api.listConversations(), api.listProjects().catch(() => [])]);
      startTransition(() => {
        setConversations(conversationRows);
        setProjects(projectRows);
      });
    } catch {
      setError("Thread history could not load. You can still start a new conversation; retry from the sidebar when ready.");
    } finally {
      if (!background) setLoadingHistory(false);
    }
  }, [setConversations, setError, startTransition]);

  useEffect(() => {
    if (conversations.length && hasFreshConversations()) {
      setLoadingHistory(false);
      return;
    }
    loadConversations();
  }, [conversations.length, hasFreshConversations, loadConversations]);

  useEffect(() => {
    api.getDashboard().then(setDashboard).catch(() => setDashboard(null));
    api.getContinuityMode().then(setContinuityMode).catch(() => setContinuityMode(null));
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem(CHAT_DRAFT_KEY);
    if (saved) setInput(saved);
  }, []);

  useEffect(() => {
    if (input.trim()) {
      localStorage.setItem(CHAT_DRAFT_KEY, input);
    } else {
      localStorage.removeItem(CHAT_DRAFT_KEY);
    }
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

  const flushAssistant = useCallback(() => {
    frameRef.current = null;
    updateLastAssistant(pendingAssistantRef.current);
  }, [updateLastAssistant]);

  const selectConversation = async (conversation: Conversation) => {
    abortRef.current?.abort();
    setActiveConversation(conversation.id);
    setActiveProject(conversation.project_id);
    setError(null);
    const cached = messagesByConversation[conversation.id];
    if (cached) {
      setMessages(cached);
      return;
    }
    setSelectingConversationId(conversation.id);
    try {
      const rows = await api.getMessages(conversation.id);
      startTransition(() => {
        setMessages(rows.map((row) => ({ id: row.id, role: row.role as "user" | "assistant" | "system", content: row.content })));
      });
    } catch {
      setError("This thread could not load. Your history is still saved; choose another thread or retry in a moment.");
    } finally {
      setSelectingConversationId(null);
    }
  };

  const newConversation = () => {
    abortRef.current?.abort();
    reset();
    setActiveProject(null);
  };

  const stop = () => {
    abortRef.current?.abort();
  };

  const send = async (retry = false, overrideText?: string, overrideProjectId?: string | null) => {
    const text = retry ? lastUserMessage : overrideText ?? input.trim();
    const outboundProjectId = overrideProjectId ?? activeProjectId;
    if (!text || isStreaming) return;
    if (!isOnline) {
      setError("You appear to be offline. Reconnect and retry when ready.");
      return;
    }

    if (!retry) {
      setInput("");
      localStorage.removeItem(CHAT_DRAFT_KEY);
      setLastUserMessage(text);
      appendMessage({ role: "user", content: text });
      void api.trackEvent("chat_message_sent", "chat", {
        conversation_id: activeConversationId,
        project_id: outboundProjectId,
        message_length: text.length,
        continuity_mode: Boolean(overrideText),
      });
    }
    appendMessage({ role: "assistant", content: "" });
    pendingAssistantRef.current = "";
    setError(null);
    setStreaming(true);
    abortRef.current = new AbortController();

    try {
      let assistant = "";
      let gotToken = false;
      for await (const event of api.streamMessage(
        text,
        activeConversationId ?? undefined,
        outboundProjectId ?? undefined,
        abortRef.current.signal,
      )) {
        if ((event.type === "meta" || event.type === "done") && event.conversation_id) {
          setActiveConversation(event.conversation_id);
        }
        if (event.type === "token" && event.content) {
          gotToken = true;
          assistant += event.content;
          pendingAssistantRef.current = assistant;
          if (!frameRef.current) frameRef.current = requestAnimationFrame(flushAssistant);
        }
      }
      if (!gotToken) {
        const result = await api.sendMessage(text, activeConversationId ?? undefined, outboundProjectId ?? undefined);
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
      void loadConversations(true);
      void api.trackEvent("chat_response_completed", "chat", {
        conversation_id: activeConversationId,
        project_id: outboundProjectId,
      });
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      setError(aborted ? "Response stopped. You can continue from here." : err instanceof Error ? err.message : "Could not reach Synzept.");
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

  const activeTitle = useMemo(
    () => conversations.find((item: Conversation) => item.id === activeConversationId)?.title || "Conversation",
    [activeConversationId, conversations],
  );

  const continuity = useMemo(() => getContinuityPanel(continuityMode, dashboard, projects), [continuityMode, dashboard, projects]);

  return (
    <div className="flex h-full min-h-0 bg-[#f7f7f4]">
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-16 items-center justify-between border-b border-border bg-white/80 px-4 backdrop-blur md:px-6">
          <div className="min-w-0">
            <p className="text-xs text-muted">Chat</p>
            <h1 className="truncate text-lg font-semibold text-stone-950">
              {activeConversationId ? activeTitle : "New conversation"}
            </h1>
          </div>
          <div className="flex items-center gap-2">
            {loadingHistory && <Loader2 className="h-4 w-4 animate-spin text-muted" />}
            {(selectingConversationId || isPending) && !loadingHistory && <Loader2 className="h-4 w-4 animate-spin text-muted" />}
            {error && (
              <Button variant="outline" size="sm" onClick={() => send(true)}>
                <RotateCcw className="h-4 w-4 md:mr-1.5" />
                <span className="hidden md:inline">Retry</span>
              </Button>
            )}
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
            <Button variant="outline" size="sm" onClick={() => setContinuityOpen((value) => !value)}>
              <PanelRightOpen className="h-4 w-4 md:mr-1.5" />
              <span className="hidden md:inline">Context</span>
            </Button>
          </div>
        </header>

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8 md:px-6">
            {selectingConversationId && !messagesByConversation[selectingConversationId] ? (
              <ConversationLoading />
            ) : messages.length ? (
              messages.map((message, index) => (
                <MessageBubble
                  key={message.id || index}
                  role={message.role as "user" | "assistant"}
                  content={message.content}
                  messageId={message.id}
                  isStreaming={isStreaming && index === messages.length - 1 && message.role === "assistant"}
                />
              ))
            ) : (
              <ContinuityModeStart snapshot={continuityMode} onContinue={(prompt, projectId) => send(false, prompt, projectId)} />
            )}
          </div>
        </div>

        <RecoveryBanner message={error} onRetry={() => (lastUserMessage ? send(true) : loadConversations())} className="mx-4 mb-2" />
        {!isOnline && !error && (
          <p className="flex items-center justify-center gap-2 px-4 pb-2 text-center text-sm text-amber-700">
            <WifiOff className="h-4 w-4" />
            Offline. Reconnect to send.
          </p>
        )}
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={() => send()}
          disabled={isStreaming}
          placeholder="What would you like to continue?"
        />
      </section>
      <ContinuityPanel open={continuityOpen} continuity={continuity} conversations={conversations} activeConversationId={activeConversationId} onClose={() => setContinuityOpen(false)} onSelect={selectConversation} />
    </div>
  );
}

function ConversationLoading() {
  return (
    <div className="space-y-4">
      <div className="h-20 max-w-[70%] rounded-xl border border-border bg-white shadow-soft" />
      <div className="ml-auto h-14 max-w-[62%] rounded-xl bg-stone-900" />
      <div className="h-28 max-w-[82%] rounded-xl border border-border bg-white shadow-soft" />
    </div>
  );
}

function ContinuityModeStart({
  snapshot,
  onContinue,
}: {
  snapshot: ContinuityMode | null;
  onContinue: (prompt: string, projectId?: string | null) => void;
}) {
  if (!snapshot) {
    return (
      <div className="rounded-xl border border-border bg-white p-5 shadow-soft">
        <p className="text-sm text-stone-500">Synzept is gathering your continuity context.</p>
        <h2 className="mt-2 text-2xl font-semibold text-stone-950">What would you like to continue?</h2>
        <p className="mt-3 text-sm leading-6 text-stone-600">Start with one sentence. Memory, projects, goals, and open loops will come in behind the scenes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-xl border border-border bg-white p-5 shadow-soft md:p-6">
        <p className="text-sm text-stone-500">{snapshot.headline}</p>
        <h2 className="mt-2 text-2xl font-semibold leading-tight text-stone-950">You were working on {snapshot.last_focus}</h2>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <ContinuityList title="Since then" items={snapshot.what_changed} />
          <ContinuityList title="Open loops" items={snapshot.open_loops} />
        </div>

        <div className="mt-5 rounded-lg border border-stone-200 bg-stone-50 p-4">
          <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">Suggested next action</p>
          <p className="mt-2 text-base font-medium text-stone-950">{snapshot.recommended_next_action}</p>
          {snapshot.recommended_reason && <p className="mt-1 text-sm leading-6 text-stone-600">{snapshot.recommended_reason}</p>}
        </div>
      </section>

      <section className="grid gap-2 sm:grid-cols-2">
        {snapshot.actions.map((action) => (
          <button
            key={action.mode}
            type="button"
            onClick={() => onContinue(action.prompt, action.project_id)}
            className="group flex min-h-14 items-center justify-between gap-3 rounded-lg border border-stone-200 bg-white px-4 py-3 text-left text-sm font-medium text-stone-900 shadow-sm transition hover:border-stone-300 hover:bg-stone-50"
          >
            <span>{action.label}</span>
            <ArrowRight className="h-4 w-4 shrink-0 text-stone-400 transition group-hover:translate-x-0.5 group-hover:text-stone-900" />
          </button>
        ))}
      </section>
    </div>
  );
}

function ContinuityList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{title}</p>
      <div className="mt-2 space-y-2">
        {items.slice(0, 5).map((item) => (
          <p key={item} className="rounded-md bg-stone-50 px-3 py-2 text-sm leading-5 text-stone-700">{item}</p>
        ))}
      </div>
    </div>
  );
}

function ContinuityPanel({
  open,
  continuity,
  conversations,
  activeConversationId,
  onClose,
  onSelect,
}: {
  open: boolean;
  continuity: ReturnType<typeof getContinuityPanel>;
  conversations: Conversation[];
  activeConversationId: string | null;
  onClose: () => void;
  onSelect: (conversation: Conversation) => void;
}) {
  if (!open) return null;

  return (
    <aside className="fixed inset-y-0 right-0 z-50 flex w-full max-w-sm flex-col border-l border-border bg-white shadow-xl md:relative md:z-auto md:w-[340px] md:max-w-none md:shadow-none">
      <div className="flex min-h-16 items-center justify-between border-b border-border px-4">
        <div>
          <p className="text-xs text-muted">Continuity</p>
          <h2 className="text-base font-semibold text-stone-950">What Synzept knows</h2>
        </div>
        <button type="button" onClick={onClose} className="grid h-9 w-9 place-items-center rounded-md text-stone-500 hover:bg-stone-100" aria-label="Close context">
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        <PanelSection title="Mission">
          <p className="text-sm leading-6 text-stone-700">{continuity.mission}</p>
        </PanelSection>
        <PanelSection title="Focus">
          <p className="text-sm leading-6 text-stone-700">{continuity.focus}</p>
        </PanelSection>
        <PanelSection title="Projects">
          <div className="space-y-2">
            {continuity.projects.map((project) => (
              <div key={project.id} className="rounded-md bg-stone-50 px-3 py-2">
                <p className="line-clamp-1 text-sm font-medium text-stone-950">{project.name}</p>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-600">{project.currentFocus || project.recommendedNextStep || project.description || "Active context"}</p>
              </div>
            ))}
          </div>
        </PanelSection>
        <PanelSection title="Open Loops">
          <div className="space-y-2">
            {continuity.openLoops.map((loop) => (
              <div key={loop.id || loop.title} className="rounded-md bg-stone-50 px-3 py-2">
                <p className="line-clamp-2 text-sm font-medium text-stone-950">{loop.title}</p>
                {loop.next_step || loop.description ? <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-600">{loop.next_step || loop.description}</p> : null}
              </div>
            ))}
          </div>
        </PanelSection>
        <PanelSection title="Recent Threads">
          <div className="space-y-1">
            {conversations.slice(0, 5).map((conversation) => {
              const active = conversation.id === activeConversationId;
              return (
                <button
                  key={conversation.id}
                  type="button"
                  onClick={() => onSelect(conversation)}
                  className={`flex w-full items-center justify-between gap-3 rounded-md px-3 py-2 text-left text-sm transition ${active ? "bg-stone-100 text-stone-950" : "text-stone-700 hover:bg-stone-50"}`}
                >
                  <span className="truncate">{conversation.title || "Untitled conversation"}</span>
                  <ChevronRight className="h-4 w-4 shrink-0 text-stone-400" />
                </button>
              );
            })}
          </div>
        </PanelSection>
      </div>
    </aside>
  );
}

function PanelSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-5">
      <p className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-stone-400">{title}</p>
      {children}
    </section>
  );
}

function getContinuityPanel(continuityMode: ContinuityMode | null, dashboard: Dashboard | null, projects: Project[]) {
  const os = dashboard?.personal_os;
  const activeProjects = (dashboard?.projects?.length ? dashboard.projects : projects).filter((project) => project.status !== "archived").slice(0, 4);
  const openLoops = (os?.open_loops || []).slice(0, 4);
  const modeOpenLoops = (continuityMode?.open_loops || []).slice(0, 4).map((title, index) => ({
    id: `continuity-${index}`,
    title,
    description: "",
    next_step: "",
  }));

  return {
    mission: os?.current_mission || activeProjects[0]?.description || activeProjects[0]?.name || continuityMode?.last_focus || "Start a thread and Synzept will keep the mission visible.",
    focus: os?.current_focus || activeProjects[0]?.currentFocus || activeProjects[0]?.recommendedNextStep || continuityMode?.recommended_next_action || "Ask what to continue next.",
    projects: activeProjects,
    openLoops: openLoops.length
      ? openLoops
      : modeOpenLoops.length
        ? modeOpenLoops
      : [
          {
            id: "continue",
            title: "Continue from the thread that matters most.",
            description: "",
            next_step: "Ask Synzept what to resume.",
          },
        ],
  };
}
