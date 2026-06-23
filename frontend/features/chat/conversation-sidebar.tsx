"use client";

import { memo, useDeferredValue, useMemo, useState } from "react";
import { FolderKanban, MessageSquare, Pin, Search } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import type { Conversation, Project } from "@/lib/api";
import { cn } from "@/lib/cn";

function formatUpdatedAt(value?: string | null) {
  if (!value) return "Updated recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Updated recently";
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function bucketForConversation(dateString?: string | null) {
  if (!dateString) return "Older";
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return "Older";
  const now = new Date();
  const delta = now.getTime() - date.getTime();
  const oneDay = 24 * 60 * 60 * 1000;
  if (date.toDateString() === now.toDateString()) return "Today";
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  if (delta <= 7 * oneDay) return "Last 7 days";
  return "Older";
}

function ConversationSidebarComponent({
  conversations,
  projects,
  activeConversationId,
  onSelect,
  onRename,
  onArchive,
  onDelete,
  onPin,
  onCreate,
  open,
  onClose,
}: {
  conversations: Conversation[];
  projects: Project[];
  activeConversationId: string | null;
  onSelect: (conversation: Conversation) => void;
  onRename: (conversation: Conversation) => void;
  onArchive: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onPin: (conversation: Conversation, pinned: boolean) => void;
  onCreate: () => void;
  open?: boolean;
  onClose?: () => void;
}) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const projectById = useMemo(() => new Map(projects.map((project) => [project.id, project])), [projects]);

  const featuredConversation = useMemo(() => {
    const active = conversations.find((conversation) => conversation.id === activeConversationId);
    return active ?? conversations[0] ?? null;
  }, [activeConversationId, conversations]);

  const filtered = useMemo(() => {
    const q = deferredQuery.toLowerCase().trim();
    if (!q) return conversations;
    return conversations.filter((conversation) => {
      const project = conversation.project_id ? projectById.get(conversation.project_id) : null;
      return [conversation.title, conversation.summary, project?.name].some((value) => value?.toLowerCase().includes(q));
    });
  }, [conversations, projectById, deferredQuery]);

  const pinnedConversations = useMemo(
    () => filtered.filter((conversation) => conversation.pinned),
    [filtered],
  );

  const groupedConversations = useMemo(() => {
    const bucketOrder = ["Today", "Yesterday", "Last 7 days", "Older"] as const;
    const buckets = new Map<string, Conversation[]>(bucketOrder.map((label) => [label, []]));
    const items = filtered.filter((conversation) => conversation !== featuredConversation && !conversation.pinned);
    for (const conversation of items) {
      const bucket = bucketForConversation(conversation.updated_at);
      buckets.get(bucket)?.push(conversation);
    }
    return bucketOrder
      .map((label) => ({ label, items: buckets.get(label) ?? [] }))
      .filter((bucket) => bucket.items.length > 0);
  }, [filtered, featuredConversation]);

  return (
    <aside
      className={cn(
        "shrink-0 border-r border-border bg-white lg:flex lg:flex-col",
        open ? "fixed inset-y-0 left-0 z-50 w-[320px] shadow-xl lg:static lg:shadow-none block" : "hidden lg:block",
      )}
    >
      {open ? (
        <div className="flex items-center justify-between border-b border-border px-4 py-3 lg:hidden">
          <div>
            <p className="text-xs uppercase tracking-[0.12em] text-muted">Threads</p>
            <p className="mt-1 text-sm font-semibold text-stone-950">Conversation history</p>
          </div>
          <button type="button" onClick={onClose} className="text-sm font-medium text-stone-500 hover:text-stone-900">
            Close
          </button>
        </div>
      ) : null}
      <div className="border-b border-border p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="mb-3 text-xs font-medium uppercase tracking-[0.12em] text-muted">Threads</p>
            <p className="text-sm text-stone-700">Continue where you left off</p>
          </div>
          <button
            type="button"
            onClick={onCreate}
            className="rounded-md bg-stone-950 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-stone-800"
          >
            New Chat
          </button>
        </div>
        <label className="mt-3 flex h-9 items-center gap-2 rounded-md border border-border bg-stone-50 px-3 text-stone-500">
          <Search className="h-4 w-4" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search chats..."
            className="min-w-0 flex-1 bg-transparent text-sm text-stone-800 outline-none placeholder:text-stone-400"
          />
        </label>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {!deferredQuery && featuredConversation ? (
          <div className="mb-4 rounded-3xl border border-stone-200 bg-stone-50 p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-stone-500">Continue where you left off</p>
                <p className="mt-3 truncate text-sm font-semibold text-stone-950">{featuredConversation.title || "Untitled conversation"}</p>
                <p className="mt-2 line-clamp-2 text-sm leading-6 text-stone-600">
                  {featuredConversation.summary || "Resume a recent conversation or open a new thread to keep momentum going."}
                </p>
              </div>
              <button
                type="button"
                onClick={() => onSelect(featuredConversation)}
                className="rounded-full bg-stone-950 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-white transition hover:bg-stone-800"
              >
                Continue
              </button>
            </div>
          </div>
        ) : null}

        {pinnedConversations.length > 0 ? (
          <div className="mb-5">
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">Pinned</p>
            <div className="space-y-2">
              {pinnedConversations.map((conversation) => {
                const active = conversation.id === activeConversationId;
                const project = conversation.project_id ? projectById.get(conversation.project_id) : null;
                return (
                  <div
                    key={conversation.id}
                    className={cn(
                      "rounded-3xl border px-3 py-3 transition",
                      active ? "border-stone-200 bg-stone-100 shadow-sm" : "border-transparent bg-white hover:border-border hover:bg-stone-50",
                    )}
                  >
                    <button type="button" onClick={() => onSelect(conversation)} className="w-full text-left">
                      <div className="flex items-center gap-2">
                        <Pin className="mt-0.5 h-4 w-4 shrink-0 text-stone-500" />
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-stone-950">{conversation.title || "Untitled conversation"}</p>
                          <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-600">
                            {conversation.summary || "Continue the thread with a fresh message."}
                          </p>
                        </div>
                      </div>
                    </button>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
                      {project ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-1 text-[11px] text-stone-700">
                          <FolderKanban className="h-3 w-3" />
                          {project.name}
                        </span>
                      ) : null}
                      <span>{formatUpdatedAt(conversation.updated_at)}</span>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => onPin(conversation, !conversation.pinned)}
                        className="rounded-md border border-border bg-white px-2.5 py-1.5 text-[11px] font-semibold text-stone-700 transition hover:border-stone-300 hover:bg-stone-50"
                      >
                        {conversation.pinned ? "Unpin" : "Pin"}
                      </button>
                      <button
                        type="button"
                        onClick={() => onRename(conversation)}
                        className="rounded-md border border-border bg-white px-2.5 py-1.5 text-[11px] font-semibold text-stone-700 transition hover:border-stone-300 hover:bg-stone-50"
                      >
                        Rename
                      </button>
                      <button
                        type="button"
                        onClick={() => onArchive(conversation)}
                        className="rounded-md border border-border bg-white px-2.5 py-1.5 text-[11px] font-semibold text-stone-700 transition hover:border-stone-300 hover:bg-stone-50"
                      >
                        Archive
                      </button>
                      <button
                        type="button"
                        onClick={() => onDelete(conversation)}
                        className="rounded-md border border-border bg-white px-2.5 py-1.5 text-[11px] font-semibold text-rose-600 transition hover:border-rose-300 hover:bg-rose-50"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        {groupedConversations.length > 0 ? (
          groupedConversations.map((bucket) => (
            <div key={bucket.label} className="mb-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">{bucket.label}</p>
              <div className="space-y-2">
                {bucket.items.map((conversation) => {
                  const active = conversation.id === activeConversationId;
                  const project = conversation.project_id ? projectById.get(conversation.project_id) : null;
                  return (
                    <div
                      key={conversation.id}
                      className={cn(
                        "rounded-3xl border px-3 py-3 transition",
                        active ? "border-stone-200 bg-stone-100 shadow-sm" : "border-transparent bg-white hover:border-border hover:bg-stone-50",
                      )}
                    >
                      <button type="button" onClick={() => onSelect(conversation)} className="w-full text-left">
                        <div className="flex items-center gap-2">
                          <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-stone-500" />
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-stone-950">{conversation.title || "Untitled conversation"}</p>
                            <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-600">
                              {conversation.summary || "Continue the thread with a fresh message."}
                            </p>
                          </div>
                        </div>
                      </button>
                      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
                        {project ? (
                          <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-1 text-[11px] text-stone-700">
                            <FolderKanban className="h-3 w-3" />
                            {project.name}
                          </span>
                        ) : null}
                        <span>{formatUpdatedAt(conversation.updated_at)}</span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => onRename(conversation)}
                          className="rounded-md border border-border bg-white px-2.5 py-1.5 text-[11px] font-semibold text-stone-700 transition hover:border-stone-300 hover:bg-stone-50"
                        >
                          Rename
                        </button>
                        <button
                          type="button"
                          onClick={() => onArchive(conversation)}
                          className="rounded-md border border-border bg-white px-2.5 py-1.5 text-[11px] font-semibold text-stone-700 transition hover:border-stone-300 hover:bg-stone-50"
                        >
                          Archive
                        </button>
                        <button
                          type="button"
                          onClick={() => onDelete(conversation)}
                          className="rounded-md border border-border bg-white px-2.5 py-1.5 text-[11px] font-semibold text-rose-600 transition hover:border-rose-300 hover:bg-rose-50"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        ) : (
          <EmptyState
            icon={<MessageSquare className="h-5 w-5" />}
            title={query ? "No matching chats" : "Start your first conversation with Synzept."}
            description={
              query
                ? "Try a different word from the project, decision, or topic you remember."
                : "Ask anything to begin your first conversation with Synzept."
            }
            steps={
              query
                ? ["Search project names, decisions, or words from the conversation."]
                : ["Click New Chat to begin.", "Type a question or project update.", "Synzept will keep the thread ready for later."]
            }
            className="mx-2 mt-3 px-4 py-8"
          />
        )}
      </div>
    </aside>
  );
}

export const ConversationSidebar = memo(ConversationSidebarComponent);
