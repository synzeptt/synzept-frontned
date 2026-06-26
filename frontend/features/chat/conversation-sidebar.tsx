"use client";

import { memo, useDeferredValue, useEffect, useMemo, useState } from "react";
import { Archive, ChevronDown, FileText, Folder, MoreHorizontal, Pencil, Pin, Plus, Search, Trash2, X } from "lucide-react";
import type { Conversation, Project } from "@/lib/api";
import { cn } from "@/lib/cn";

const BUCKETS = ["Today", "Yesterday", "Last 7 Days", "Older"] as const;

function formatUpdatedAt(value?: string | null) {
  if (!value) return "Recently";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Recently";
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
}

function bucketForConversation(value?: string | null) {
  if (!value) return "Older";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Older";
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  const oneDay = 24 * 60 * 60 * 1000;

  if (date.toDateString() === now.toDateString()) return "Today";
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  if (now.getTime() - date.getTime() <= 7 * oneDay) return "Last 7 Days";
  return "Older";
}

type Props = {
  conversations: Conversation[];
  projects: Project[];
  activeConversationId: string | null;
  onSelect: (conversation: Conversation) => void;
  onRename: (conversation: Conversation) => void;
  onArchive: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onPin: (conversation: Conversation, pinned: boolean) => void;
  onMoveToProject: (conversation: Conversation, projectId: string | null) => void;
  onCreate: () => void;
  open?: boolean;
  onClose?: () => void;
};

function ConversationSidebarComponent({
  conversations,
  projects,
  activeConversationId,
  onSelect,
  onRename,
  onArchive,
  onDelete,
  onPin,
  onMoveToProject,
  onCreate,
  open,
  onClose,
}: Props) {
  const [query, setQuery] = useState("");
  const [projectsOpen, setProjectsOpen] = useState(true);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [moveMenuId, setMoveMenuId] = useState<string | null>(null);
  const deferredQuery = useDeferredValue(query);
  const projectById = useMemo(() => new Map(projects.map((project) => [project.id, project])), [projects]);

  useEffect(() => {
    const close = () => {
      setMenuId(null);
      setMoveMenuId(null);
    };
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, []);

  const filtered = useMemo(() => {
    const q = deferredQuery.trim().toLowerCase();
    if (!q) return conversations;
    return conversations.filter((conversation) => {
      const project = conversation.project_id ? projectById.get(conversation.project_id) : null;
      return [conversation.title, conversation.summary, project?.name].some((value) => value?.toLowerCase().includes(q));
    });
  }, [conversations, deferredQuery, projectById]);

  const pinned = useMemo(() => filtered.filter((conversation) => conversation.pinned), [filtered]);
  const grouped = useMemo(() => {
    const unpinned = filtered.filter((conversation) => !conversation.pinned);
    return BUCKETS.map((label) => ({
      label,
      items: unpinned.filter((conversation) => bucketForConversation(conversation.updated_at) === label),
    })).filter((group) => group.items.length > 0);
  }, [filtered]);

  return (
    <aside
      className={cn(
        "z-50 flex h-full w-[320px] shrink-0 flex-col border-r border-stone-200/70 bg-[#fbfaf7]",
        open ? "fixed inset-y-0 left-0 shadow-2xl md:static md:shadow-none" : "hidden md:flex",
      )}
    >
      <div className="px-4 pb-3 pt-4">
        <div className="mb-4 flex items-center justify-between">
          <h1 className="text-lg font-semibold tracking-tight text-stone-950">Synzept</h1>
          <button type="button" onClick={onClose} className="grid h-8 w-8 place-items-center rounded-md text-stone-500 hover:bg-stone-100 md:hidden" aria-label="Close chats">
            <X className="h-4 w-4" />
          </button>
        </div>
        <button
          type="button"
          onClick={onCreate}
          className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-stone-950 px-3 text-sm font-medium text-white transition hover:bg-stone-800"
        >
          <Plus className="h-4 w-4" />
          New Chat
        </button>
        <label className="mt-3 flex h-10 items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 text-stone-500 shadow-sm">
          <Search className="h-4 w-4" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search Chats..."
            className="min-w-0 flex-1 bg-transparent text-sm text-stone-900 outline-none placeholder:text-stone-400"
          />
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        <section className="border-t border-stone-200/70 pt-4">
          <button type="button" onClick={() => setProjectsOpen((value) => !value)} className="flex w-full items-center justify-between px-1 text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">
            Projects
            <ChevronDown className={cn("h-4 w-4 transition", !projectsOpen && "-rotate-90")} />
          </button>
          {projectsOpen ? (
            <div className="mt-2 space-y-1">
              {(projects.length ? projects : exampleProjects).slice(0, 8).map((project) => {
                const realProject = "id" in project;
                const projectConversations = realProject ? conversations.filter((conversation) => conversation.project_id === project.id) : [];
                return (
                  <div key={project.name} className="rounded-lg px-2 py-1.5 text-sm text-stone-700">
                    <div className="flex items-center gap-2">
                      <Folder className="h-4 w-4 text-stone-500" />
                      <span className="truncate">{project.name}</span>
                      {projectConversations.length > 0 ? <span className="ml-auto text-xs text-stone-400">{projectConversations.length}</span> : null}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : null}
        </section>

        <section className="mt-5 border-t border-stone-200/70 pt-4">
          <p className="px-1 text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">Recent Chats</p>
          <div className="mt-2 space-y-5">
            {pinned.length > 0 ? (
              <ConversationGroup
                label="Pinned"
                conversations={pinned}
                activeConversationId={activeConversationId}
                projectById={projectById}
                projects={projects}
                menuId={menuId}
                moveMenuId={moveMenuId}
                setMenuId={setMenuId}
                setMoveMenuId={setMoveMenuId}
                onSelect={onSelect}
                onRename={onRename}
                onArchive={onArchive}
                onDelete={onDelete}
                onPin={onPin}
                onMoveToProject={onMoveToProject}
              />
            ) : null}
            {grouped.map((group) => (
              <ConversationGroup
                key={group.label}
                label={group.label}
                conversations={group.items}
                activeConversationId={activeConversationId}
                projectById={projectById}
                projects={projects}
                menuId={menuId}
                moveMenuId={moveMenuId}
                setMenuId={setMenuId}
                setMoveMenuId={setMoveMenuId}
                onSelect={onSelect}
                onRename={onRename}
                onArchive={onArchive}
                onDelete={onDelete}
                onPin={onPin}
                onMoveToProject={onMoveToProject}
              />
            ))}
            {!filtered.length ? <p className="px-2 py-6 text-sm text-stone-500">No chats found.</p> : null}
          </div>
        </section>
      </div>
    </aside>
  );
}

function ConversationGroup({
  label,
  conversations,
  activeConversationId,
  projectById,
  projects,
  menuId,
  moveMenuId,
  setMenuId,
  setMoveMenuId,
  onSelect,
  onRename,
  onArchive,
  onDelete,
  onPin,
  onMoveToProject,
}: {
  label: string;
  conversations: Conversation[];
  activeConversationId: string | null;
  projectById: Map<string, Project>;
  projects: Project[];
  menuId: string | null;
  moveMenuId: string | null;
  setMenuId: (id: string | null) => void;
  setMoveMenuId: (id: string | null) => void;
  onSelect: (conversation: Conversation) => void;
  onRename: (conversation: Conversation) => void;
  onArchive: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onPin: (conversation: Conversation, pinned: boolean) => void;
  onMoveToProject: (conversation: Conversation, projectId: string | null) => void;
}) {
  return (
    <div>
      <p className="mb-1.5 px-1 text-xs font-medium text-stone-400">{label}</p>
      <div className="space-y-1">
        {conversations.map((conversation) => {
          const active = conversation.id === activeConversationId;
          const project = conversation.project_id ? projectById.get(conversation.project_id) : null;
          return (
            <div key={conversation.id} className="relative">
              <button
                type="button"
                onClick={() => onSelect(conversation)}
                className={cn(
                  "group flex w-full gap-2 rounded-lg px-2 py-2 text-left transition",
                  active ? "bg-stone-900 text-white" : "text-stone-700 hover:bg-stone-100",
                )}
              >
                {conversation.pinned ? <Pin className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">{conversation.title || "Untitled conversation"}</span>
                  <span className={cn("mt-0.5 block truncate text-xs", active ? "text-stone-300" : "text-stone-500")}>
                    {conversation.summary || project?.name || "Continue the conversation"}
                  </span>
                  <span className={cn("mt-1 block text-[11px]", active ? "text-stone-300" : "text-stone-400")}>{formatUpdatedAt(conversation.updated_at)}</span>
                </span>
              </button>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  setMoveMenuId(null);
                  setMenuId(menuId === conversation.id ? null : conversation.id);
                }}
                className={cn("absolute right-1 top-1 grid h-7 w-7 place-items-center rounded-md", active ? "text-stone-300 hover:bg-white/10" : "text-stone-500 hover:bg-stone-200")}
                aria-label="Conversation menu"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
              {menuId === conversation.id ? (
                <div onClick={(event) => event.stopPropagation()} className="absolute right-1 top-9 z-20 w-52 rounded-lg border border-stone-200 bg-white p-1.5 shadow-xl">
                  <MenuButton icon={<Pencil />} label="Rename" onClick={() => onRename(conversation)} />
                  <div className="relative">
                    <MenuButton icon={<Folder />} label="Move to Project" onClick={() => setMoveMenuId(moveMenuId === conversation.id ? null : conversation.id)} />
                    {moveMenuId === conversation.id ? (
                      <div className="absolute left-full top-0 z-30 ml-2 max-h-64 w-52 overflow-y-auto rounded-lg border border-stone-200 bg-white p-1.5 shadow-xl">
                        <MenuButton icon={<X />} label="No Project" onClick={() => onMoveToProject(conversation, null)} />
                        {projects.map((project) => (
                          <MenuButton key={project.id} icon={<Folder />} label={project.name} onClick={() => onMoveToProject(conversation, project.id)} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <MenuButton icon={<Pin />} label={conversation.pinned ? "Unpin" : "Pin"} onClick={() => onPin(conversation, !conversation.pinned)} />
                  <MenuButton icon={<Archive />} label="Archive" onClick={() => onArchive(conversation)} />
                  <MenuButton icon={<Trash2 />} label="Delete" danger onClick={() => onDelete(conversation)} />
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MenuButton({ icon, label, danger, onClick }: { icon: React.ReactElement; label: string; danger?: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn("flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-stone-700 hover:bg-stone-100", danger && "text-rose-600 hover:bg-rose-50")}
    >
      {memoIcon(icon)}
      <span className="truncate">{label}</span>
    </button>
  );
}

function memoIcon(icon: React.ReactElement) {
  return <span className="grid h-4 w-4 shrink-0 place-items-center [&>svg]:h-4 [&>svg]:w-4">{icon}</span>;
}

const exampleProjects = [
  { name: "Synzept" },
  { name: "Startup" },
  { name: "Personal" },
  { name: "Learning" },
];

export const ConversationSidebar = memo(ConversationSidebarComponent);
