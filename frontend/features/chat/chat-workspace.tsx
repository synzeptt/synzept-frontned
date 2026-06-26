"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import { Loader2, Menu, RotateCcw, Square, WifiOff } from "lucide-react";
import { ChatInput } from "@/components/chat/chat-input";
import { MessageBubble } from "@/components/chat/message-bubble";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { api, type AttachmentMetadata, type ContinuityMode, type Conversation, type Project } from "@/lib/api";
import { useChatStore } from "@/stores/chat";
import { ConversationSidebar } from "@frontend/features/chat/conversation-sidebar";
import { useAutoScroll } from "@frontend/hooks/use-auto-scroll";

const CHAT_DRAFT_KEY = "synzept_chat_draft";
const CONTINUE_PROJECT_KEY = "synzept_continue_project_id";

export function ChatWorkspace() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const frameRef = useRef<number | null>(null);
  const pendingAssistantRef = useRef("");
  const [input, setInput] = useState("");
  const [lastUserMessage, setLastUserMessage] = useState("");
  const [attachments, setAttachments] = useState<AttachmentMetadata[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [uploadFileName, setUploadFileName] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [selectingConversationId, setSelectingConversationId] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [continuityMode, setContinuityMode] = useState<ContinuityMode | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [isOnline, setIsOnline] = useState(() => (typeof navigator === "undefined" ? true : navigator.onLine));
  const [, startTransition] = useTransition();
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
      setError("Thread history could not load. You can still start a new conversation.");
    } finally {
      if (!background) setLoadingHistory(false);
    }
  }, [setConversations, setError, startTransition]);

  const updateConversation = useCallback(
    (updated: Conversation) => {
      setConversations(conversations.map((conversation) => (conversation.id === updated.id ? updated : conversation)));
    },
    [conversations, setConversations],
  );

  useEffect(() => {
    if (conversations.length && hasFreshConversations()) {
      setLoadingHistory(false);
      return;
    }
    loadConversations();
  }, [conversations.length, hasFreshConversations, loadConversations]);

  useEffect(() => {
    api.getContinuityMode().then(setContinuityMode).catch(() => setContinuityMode(null));
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem(CHAT_DRAFT_KEY);
    if (saved) setInput(saved);
    const projectId = localStorage.getItem(CONTINUE_PROJECT_KEY);
    if (projectId) {
      setActiveProject(projectId);
      localStorage.removeItem(CONTINUE_PROJECT_KEY);
    }
  }, [setActiveProject]);

  useEffect(() => {
    if (input.trim()) localStorage.setItem(CHAT_DRAFT_KEY, input);
    else localStorage.removeItem(CHAT_DRAFT_KEY);
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
        setMessages(rows.map((row) => ({ id: row.id, role: row.role as "user" | "assistant" | "system", content: row.content, metadata: row.metadata })));
      });
    } catch {
      setError("This thread could not load. Choose another thread or retry in a moment.");
    } finally {
      setSelectingConversationId(null);
    }
  };

  const newConversation = useCallback(async () => {
    abortRef.current?.abort();
    reset();
    setActiveProject(null);
    setAttachments([]);
    setInput("");
    setError(null);
    try {
      const conversation = await api.createConversation({ title: "New conversation" });
      setConversations([conversation, ...conversations]);
      setActiveConversation(conversation.id);
      setMessages([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start a new conversation.");
    }
  }, [conversations, reset, setActiveConversation, setActiveProject, setConversations, setError, setMessages]);

  const archiveConversation = useCallback(
    async (conversation: Conversation) => {
      if (!window.confirm("Archive this conversation?")) return;
      try {
        const updated = await api.archiveConversation(conversation.id);
        setConversations(conversations.filter((item) => item.id !== updated.id));
        if (activeConversationId === updated.id) await newConversation();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not archive that thread.");
      }
    },
    [activeConversationId, conversations, newConversation, setConversations, setError],
  );

  const deleteConversation = useCallback(
    async (conversation: Conversation) => {
      if (!window.confirm("Delete this conversation? This action cannot be undone.")) return;
      try {
        await api.deleteConversation(conversation.id);
        setConversations(conversations.filter((item) => item.id !== conversation.id));
        if (activeConversationId === conversation.id) newConversation();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not delete that thread.");
      }
    },
    [activeConversationId, conversations, newConversation, setConversations, setError],
  );

  const pinConversation = useCallback(
    async (conversation: Conversation, pinned: boolean) => {
      try {
        updateConversation(await api.pinConversation(conversation.id, pinned));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not update pin state.");
      }
    },
    [setError, updateConversation],
  );

  const renameConversation = useCallback(
    async (conversation: Conversation) => {
      const title = window.prompt("Rename conversation", conversation.title || "");
      if (!title?.trim() || title.trim() === conversation.title) return;
      try {
        updateConversation(await api.renameConversation(conversation.id, title.trim()));
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not rename that thread.");
      }
    },
    [setError, updateConversation],
  );

  const moveConversationToProject = useCallback(
    async (conversation: Conversation, projectId: string | null) => {
      try {
        const updated = await api.moveConversationToProject(conversation.id, projectId);
        updateConversation(updated);
        if (activeConversationId === updated.id) setActiveProject(updated.project_id);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not move that conversation.");
      }
    },
    [activeConversationId, setActiveProject, setError, updateConversation],
  );

  const stop = () => abortRef.current?.abort();

  const send = async (retry = false, overrideText?: string, overrideProjectId?: string | null) => {
    const requestAttachments = attachments.length ? attachments : undefined;
    const text = retry ? lastUserMessage : (overrideText ?? input.trim()) || (attachments.length > 0 ? "Attached files" : "");
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
      appendMessage({ role: "user", content: text, metadata: requestAttachments ? { attachments: requestAttachments } : undefined });
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
      for await (const event of api.streamMessage(text, activeConversationId ?? undefined, outboundProjectId ?? undefined, requestAttachments, abortRef.current.signal)) {
        if ((event.type === "meta" || event.type === "done") && event.conversation_id) setActiveConversation(event.conversation_id);
        if (event.type === "token" && event.content) {
          gotToken = true;
          assistant += event.content;
          pendingAssistantRef.current = assistant;
          if (!frameRef.current) frameRef.current = requestAnimationFrame(flushAssistant);
        }
      }
      if (!gotToken) {
        const result = await api.sendMessage(text, activeConversationId ?? undefined, outboundProjectId ?? undefined, requestAttachments);
        setActiveConversation(result.conversation_id);
        updateLastAssistant(result.reply);
      }
      if (!retry) setAttachments([]);
      const syncedConversationId = useChatStore.getState().activeConversationId;
      if (syncedConversationId) {
        const rows = await api.getMessages(syncedConversationId);
        startTransition(() => {
          setMessages(rows.map((row) => ({ id: row.id, role: row.role as "user" | "assistant" | "system", content: row.content, metadata: row.metadata })));
        });
      }
      void loadConversations(true);
      void api.trackEvent("chat_response_completed", "chat", { conversation_id: activeConversationId, project_id: outboundProjectId });
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

  const attachFiles = async (files: FileList) => {
    const batch = Array.from(files);
    if (!batch.length) return;
    setUploading(true);
    try {
      for (const file of batch) {
        setUploadProgress(0);
        setUploadFileName(file.name);
        const attachment = await api.uploadAttachment(file, (progress) => setUploadProgress(Math.round(progress)));
        setAttachments((current) => [...current, attachment]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not upload attachment. Please try again.");
    } finally {
      setUploading(false);
      setUploadProgress(null);
      setUploadFileName(null);
    }
  };

  const activeProject = useMemo(() => projects.find((project) => project.id === activeProjectId) ?? null, [activeProjectId, projects]);

  return (
    <div className="relative flex h-full min-h-0 bg-[#f8f7f3]">
      <ConversationSidebar
        conversations={conversations}
        projects={projects}
        activeConversationId={activeConversationId}
        onSelect={(conversation) => {
          selectConversation(conversation);
          setSidebarOpen(false);
        }}
        onRename={renameConversation}
        onArchive={archiveConversation}
        onDelete={deleteConversation}
        onPin={pinConversation}
        onMoveToProject={moveConversationToProject}
        onCreate={newConversation}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {sidebarOpen ? <button type="button" className="fixed inset-0 z-40 bg-black/25 md:hidden" aria-label="Close chats" onClick={() => setSidebarOpen(false)} /> : null}

      <main className="relative min-w-0 flex-1">
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className="fixed left-3 top-3 z-30 grid h-10 w-10 place-items-center rounded-lg border border-stone-200 bg-white text-stone-700 shadow-sm md:hidden"
          aria-label="Open chats"
        >
          <Menu className="h-5 w-5" />
        </button>

        {(loadingHistory || selectingConversationId) && (
          <div className="fixed right-4 top-4 z-20 flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs text-stone-500 shadow-sm">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            Syncing
          </div>
        )}

        {isStreaming ? (
          <button type="button" onClick={stop} className="fixed right-4 top-4 z-30 flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 shadow-sm hover:bg-stone-50">
            <Square className="h-3.5 w-3.5" />
            Stop
          </button>
        ) : error ? (
          <button type="button" onClick={() => send(true)} className="fixed right-4 top-4 z-30 flex items-center gap-2 rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs font-medium text-stone-700 shadow-sm hover:bg-stone-50">
            <RotateCcw className="h-3.5 w-3.5" />
            Retry
          </button>
        ) : null}

        <div ref={scrollRef} className="h-full overflow-y-auto pb-44 pt-8 md:pb-48 md:pt-10">
          <div className="mx-auto flex min-h-full max-w-3xl flex-col gap-7 px-4 md:px-6">
            {selectingConversationId && !messagesByConversation[selectingConversationId] ? (
              <ConversationLoading />
            ) : messages.length ? (
              messages.map((message, index) => (
                <MessageBubble
                  key={message.id || index}
                  role={message.role as "user" | "assistant"}
                  content={message.content}
                  metadata={message.metadata}
                  messageId={message.id}
                  isStreaming={isStreaming && index === messages.length - 1 && message.role === "assistant"}
                />
              ))
            ) : (
              <EmptyConversation snapshot={continuityMode} projectName={activeProject?.name} onContinue={(prompt, projectId) => send(false, prompt, projectId)} />
            )}
          </div>
        </div>

        <div className="fixed bottom-[132px] left-0 right-0 z-20 px-3 md:left-[320px] md:px-6">
          <div className="mx-auto max-w-3xl">
            <RecoveryBanner message={error} onRetry={() => (lastUserMessage ? send(true) : loadConversations())} />
            {!isOnline && !error ? (
              <p className="mt-2 flex items-center justify-center gap-2 text-center text-sm text-amber-700">
                <WifiOff className="h-4 w-4" />
                Offline. Reconnect to send.
              </p>
            ) : null}
          </div>
        </div>

        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={() => send()}
          disabled={isStreaming || uploading}
          placeholder="Message Synzept..."
          attachments={attachments}
          onAttachFiles={attachFiles}
          onRemoveAttachment={(attachmentId) => setAttachments((current) => current.filter((item) => item.id !== attachmentId))}
          uploading={uploading}
          uploadProgress={uploadProgress}
          uploadFileName={uploadFileName}
        />
      </main>
    </div>
  );
}

function ConversationLoading() {
  return (
    <div className="space-y-5 pt-8">
      <div className="h-16 max-w-[68%] animate-pulse rounded-xl bg-white" />
      <div className="ml-auto h-12 max-w-[58%] animate-pulse rounded-xl bg-stone-200" />
      <div className="h-24 max-w-[78%] animate-pulse rounded-xl bg-white" />
    </div>
  );
}

function EmptyConversation({
  snapshot,
  projectName,
  onContinue,
}: {
  snapshot: ContinuityMode | null;
  projectName?: string;
  onContinue: (prompt: string, projectId?: string | null) => void;
}) {
  const actions = snapshot?.actions?.slice(0, 3) ?? [];
  return (
    <div className="flex flex-1 items-center justify-center py-20">
      <div className="w-full max-w-2xl text-center">
        <p className="text-sm text-stone-500">{projectName ? `Working in ${projectName}` : "AI workspace"}</p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-stone-950 md:text-4xl">What would you like to work through?</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-stone-600">
          Start a new thought, continue a project, or drop in files for Synzept to read.
        </p>
        {actions.length ? (
          <div className="mt-7 grid gap-2 text-left sm:grid-cols-3">
            {actions.map((action) => (
              <button
                key={action.mode}
                type="button"
                onClick={() => onContinue(action.prompt, action.project_id)}
                className="rounded-lg border border-stone-200 bg-white px-3 py-3 text-sm font-medium text-stone-800 shadow-sm transition hover:border-stone-300 hover:bg-stone-50"
              >
                {action.label}
              </button>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
