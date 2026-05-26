"use client";

import { memo, useDeferredValue, useMemo, useState } from "react";
import { FolderKanban, MessageSquare, Search } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import type { Conversation, Project } from "@/lib/api";
import { cn } from "@/lib/cn";

function ConversationSidebarComponent({
  conversations,
  projects,
  activeConversationId,
  onSelect,
}: {
  conversations: Conversation[];
  projects: Project[];
  activeConversationId: string | null;
  onSelect: (conversation: Conversation) => void;
}) {
  const [query, setQuery] = useState("");
  const deferredQuery = useDeferredValue(query);
  const projectById = useMemo(() => new Map(projects.map((project) => [project.id, project])), [projects]);
  const filtered = useMemo(() => {
    const q = deferredQuery.toLowerCase().trim();
    if (!q) return conversations;
    return conversations.filter((conversation) => {
      const project = conversation.project_id ? projectById.get(conversation.project_id) : null;
      return [conversation.title, conversation.summary, project?.name].some((value) => value?.toLowerCase().includes(q));
    });
  }, [conversations, projectById, deferredQuery]);

  return (
    <aside className="hidden w-[292px] shrink-0 border-r border-border bg-white lg:flex lg:flex-col">
      <div className="border-b border-border p-4">
        <p className="mb-3 text-xs font-medium uppercase tracking-[0.12em] text-muted">Threads</p>
        <label className="flex h-9 items-center gap-2 rounded-md border border-border bg-stone-50 px-3 text-stone-500">
          <Search className="h-4 w-4" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search history"
            className="min-w-0 flex-1 bg-transparent text-sm text-stone-800 outline-none placeholder:text-stone-400"
          />
        </label>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {filtered.map((conversation) => {
          const active = conversation.id === activeConversationId;
          const project = conversation.project_id ? projectById.get(conversation.project_id) : null;
          return (
            <button
              key={conversation.id}
              type="button"
              onClick={() => onSelect(conversation)}
              className={cn(
                "mb-1 w-full rounded-md px-3 py-3 text-left transition duration-150",
                active ? "bg-stone-100 shadow-[inset_0_0_0_1px_rgba(32,31,28,0.04)]" : "hover:bg-stone-50",
              )}
            >
              <div className="flex items-start gap-2">
                <MessageSquare className="mt-0.5 h-4 w-4 shrink-0 text-stone-400" />
                <div className="min-w-0">
                  <p className="truncate text-sm text-stone-900">{conversation.title || "Untitled conversation"}</p>
                  {conversation.summary && <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{conversation.summary}</p>}
                  {project && (
                    <p className="mt-2 flex items-center gap-1.5 text-xs text-muted">
                      <FolderKanban className="h-3 w-3" />
                      {project.name}
                    </p>
                  )}
                </div>
              </div>
            </button>
          );
        })}
        {!filtered.length && (
          <EmptyState
            icon={<MessageSquare className="h-5 w-5" />}
            title={query ? "No matching threads" : "No conversations yet"}
            description={
              query
                ? "Try a different word from the project, decision, or topic you remember."
                : "Start with what you want to continue. Synzept will keep the thread ready for later."
            }
            steps={
              query
                ? ["Search project names, decisions, or words from the conversation."]
                : ["Ask about an active project.", "Paste rough notes to organize.", "Say what should not be lost before you stop."]
            }
            className="mx-2 mt-3 px-4 py-8"
          />
        )}
      </div>
    </aside>
  );
}

export const ConversationSidebar = memo(ConversationSidebarComponent);
