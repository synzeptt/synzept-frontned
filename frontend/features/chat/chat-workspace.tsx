"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { Loader2, Plus, RotateCcw, Square, WifiOff } from "lucide-react";
import { ChatInput } from "@/components/chat/chat-input";
import { MessageBubble } from "@/components/chat/message-bubble";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { api, type ChatMessage, type Conversation, type Project } from "@/lib/api";
import { useChatStore } from "@/stores/chat";
import { useAutoScroll } from "@frontend/hooks/use-auto-scroll";
import { ConversationSidebar } from "./conversation-sidebar";

const welcome: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Tell me what you want to continue, organize, or think through. Start with what matters, what feels unfinished, or what should not be lost.",
};
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

  const send = async (retry = false) => {
    const text = retry ? lastUserMessage : input.trim();
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
        activeProjectId ?? undefined,
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
        const result = await api.sendMessage(text, activeConversationId ?? undefined, activeProjectId ?? undefined);
        setActiveConversation(result.conversation_id);
        updateLastAssistant(result.reply);
      }
      void loadConversations(true);
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

  const visibleMessages = useMemo<ChatMessage[]>(() => (messages.length ? messages : [welcome]), [messages]);
  const activeTitle = useMemo(
    () => conversations.find((item: Conversation) => item.id === activeConversationId)?.title || "Conversation",
    [activeConversationId, conversations],
  );

  return (
    <div className="flex h-full min-h-0">
      <ConversationSidebar
        conversations={conversations}
        projects={projects}
        activeConversationId={activeConversationId}
        onSelect={selectConversation}
      />
      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-16 items-center justify-between border-b border-border bg-white/80 px-4 backdrop-blur md:px-6">
          <div className="min-w-0">
            <p className="text-xs text-muted">Continuity thread</p>
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
          </div>
        </header>

        <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-8 md:px-6">
            {selectingConversationId && !messagesByConversation[selectingConversationId] ? (
              <ConversationLoading />
            ) : visibleMessages.map((message, index) => (
              <MessageBubble
                key={message.id || index}
                role={message.role as "user" | "assistant"}
                content={message.content}
                isStreaming={isStreaming && index === visibleMessages.length - 1 && message.role === "assistant"}
              />
            ))}
          </div>
        </div>

        <RecoveryBanner message={error} onRetry={() => (lastUserMessage ? send(true) : loadConversations())} className="mx-4 mb-2" />
        {!isOnline && !error && (
          <p className="flex items-center justify-center gap-2 px-4 pb-2 text-center text-sm text-amber-700">
            <WifiOff className="h-4 w-4" />
            Offline. Reconnect to send.
          </p>
        )}
        <ChatInput value={input} onChange={setInput} onSubmit={() => send()} disabled={isStreaming} />
      </section>
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
