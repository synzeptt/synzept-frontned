"use client";

import { memo, useDeferredValue, useMemo, useState } from "react";
import {
  Archive,
  ChevronDown,
  ChevronsLeft,
  ChevronsRight,
  Copy,
  Folder,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Pin,
  Plus,
  Search,
  Share2,
  Trash2,
  X,
} from "lucide-react";
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
  collapsed: boolean;
  onToggleCollapsed: () => void;
  onSelect: (conversation: Conversation) => void;
  onRename: (conversation: Conversation, title: string) => void;
  onArchive: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onPin: (conversation: Conversation, pinned: boolean) => void;
  onDuplicate: (conversation: Conversation) => void;
  onShare: (conversation: Conversation) => void;
  onMoveToProject: (conversation: Conversation, projectId: string | null) => void;
  onCreate: () => void;
  onCreateProject: (name: string) => void;
  onRenameProject: (project: Project, name: string) => void;
  onArchiveProject: (project: Project) => void;
  onDeleteProject: (project: Project) => void;
  open?: boolean;
  onClose?: () => void;
};

function ConversationSidebarComponent({
  conversations,
  projects,
  activeConversationId,
  collapsed,
  onToggleCollapsed,
  onSelect,
  onRename,
  onArchive,
  onDelete,
  onPin,
  onDuplicate,
  onShare,
  onMoveToProject,
  onCreate,
  onCreateProject,
  onRenameProject,
  onArchiveProject,
  onDeleteProject,
  open,
  onClose,
}: Props) {
  const [query, setQuery] = useState("");
  const [projectsOpen, setProjectsOpen] = useState(true);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [projectMenuId, setProjectMenuId] = useState<string | null>(null);
  const [moveMenuId, setMoveMenuId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [renamingProjectId, setRenamingProjectId] = useState<string | null>(null);
  const [projectRenameDraft, setProjectRenameDraft] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);
  const [projectDraft, setProjectDraft] = useState("");
  const [draggedConversationId, setDraggedConversationId] = useState<string | null>(null);
  const deferredQuery = useDeferredValue(query);
  const projectById = useMemo(() => new Map(projects.map((project) => [project.id, project])), [projects]);
  const effectiveCollapsed = collapsed && !open;

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

  const submitRename = (conversation: Conversation) => {
    const title = renameDraft.trim();
    setRenamingId(null);
    if (title && title !== conversation.title) onRename(conversation, title);
  };

  const submitProjectRename = (project: Project) => {
    const name = projectRenameDraft.trim();
    setRenamingProjectId(null);
    if (name && name !== project.name) onRenameProject(project, name);
  };

  const submitCreateProject = () => {
    const name = projectDraft.trim();
    if (!name) return;
    onCreateProject(name);
    setProjectDraft("");
    setCreatingProject(false);
  };

  const draggedConversation = draggedConversationId ? conversations.find((conversation) => conversation.id === draggedConversationId) : null;

  if (effectiveCollapsed) {
    return (
      <aside className="hidden h-full w-16 shrink-0 flex-col items-center border-r border-stone-200/70 bg-[#fbfaf7] py-3 md:flex">
        <button type="button" onClick={onToggleCollapsed} className="mt-2 grid h-10 w-10 place-items-center rounded-lg text-stone-500 hover:bg-stone-100 hover:text-stone-950" aria-label="Expand chat sidebar">
          <ChevronsRight className="h-5 w-5" />
        </button>
        <button type="button" onClick={onCreate} className="mt-3 grid h-10 w-10 place-items-center rounded-lg bg-stone-950 text-white hover:bg-stone-800" aria-label="New Chat" title="New Chat">
          <Plus className="h-5 w-5" />
        </button>
        <div className="mt-5 h-px w-8 bg-stone-200" />
        <MessageSquare className="mt-5 h-5 w-5 text-stone-400" />
      </aside>
    );
  }

  return (
    <aside
      className={cn(
        "z-50 flex h-full w-[320px] shrink-0 flex-col border-r border-stone-200/70 bg-[#fbfaf7]",
        open ? "fixed inset-y-0 left-0 shadow-2xl md:static md:shadow-none" : "hidden md:flex",
      )}
    >
      <div className="px-4 pb-3 pt-4">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-stone-400">Synzept</p>
            <h2 className="text-lg font-semibold text-stone-950">Chats</h2>
          </div>
          <div className="flex items-center gap-1">
            <button type="button" onClick={onToggleCollapsed} className="hidden h-8 w-8 place-items-center rounded-md text-stone-500 hover:bg-stone-100 md:grid" aria-label="Collapse chat sidebar">
              <ChevronsLeft className="h-4 w-4" />
            </button>
            <button type="button" onClick={onClose} className="grid h-8 w-8 place-items-center rounded-md text-stone-500 hover:bg-stone-100 md:hidden" aria-label="Close chats">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        <button type="button" onClick={onCreate} className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-stone-950 px-3 text-sm font-medium text-white transition hover:bg-stone-800">
          <Plus className="h-4 w-4" />
          New Chat
        </button>
        <label className="mt-3 flex h-10 items-center gap-2 rounded-lg border border-stone-200 bg-white px-3 text-stone-500 shadow-sm">
          <Search className="h-4 w-4" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search Chats..." className="min-w-0 flex-1 bg-transparent text-sm text-stone-900 outline-none placeholder:text-stone-400" />
        </label>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
        <section className="border-t border-stone-200/70 pt-4">
          <div className="flex items-center justify-between gap-1 px-1">
            <button type="button" onClick={() => setProjectsOpen((value) => !value)} className="flex min-w-0 flex-1 items-center gap-1 text-left text-xs font-semibold uppercase tracking-[0.12em] text-stone-500">
              Projects
              <ChevronDown className={cn("h-4 w-4 transition", !projectsOpen && "-rotate-90")} />
            </button>
            <button type="button" onClick={() => setCreatingProject(true)} className="grid h-7 w-7 place-items-center rounded-md text-stone-500 hover:bg-stone-100 hover:text-stone-950" aria-label="Create project">
              <Plus className="h-4 w-4" />
            </button>
          </div>

          {projectsOpen ? (
            <div className="mt-2 space-y-1">
              {creatingProject ? (
                <ProjectEditor
                  label="Create project"
                  value={projectDraft}
                  onChange={setProjectDraft}
                  onCancel={() => {
                    setCreatingProject(false);
                    setProjectDraft("");
                  }}
                  onSubmit={submitCreateProject}
                  placeholder="Project name"
                />
              ) : null}
              {projects.map((project) => {
                const count = conversations.filter((conversation) => conversation.project_id === project.id).length;
                const dropActive = draggedConversation && draggedConversation.project_id !== project.id;
                return (
                  <div
                    key={project.id}
                    onDragOver={(event) => {
                      if (!draggedConversation) return;
                      event.preventDefault();
                    }}
                    onDrop={(event) => {
                      event.preventDefault();
                      if (draggedConversation) onMoveToProject(draggedConversation, project.id);
                      setDraggedConversationId(null);
                    }}
                    className={cn("relative rounded-lg", dropActive && "bg-stone-100 ring-1 ring-stone-300")}
                  >
                    {renamingProjectId === project.id ? (
                      <ProjectEditor label="Rename project" value={projectRenameDraft} onChange={setProjectRenameDraft} onCancel={() => setRenamingProjectId(null)} onSubmit={() => submitProjectRename(project)} placeholder="Project name" />
                    ) : (
                      <div className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-stone-700 hover:bg-stone-100">
                        <Folder className="h-4 w-4 text-stone-500" />
                        <span className="min-w-0 flex-1 truncate">{project.name}</span>
                        {count > 0 ? <span className="text-xs text-stone-400">{count}</span> : null}
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            setMenuId(null);
                            setProjectMenuId(projectMenuId === project.id ? null : project.id);
                          }}
                          className="relative z-10 grid h-7 w-7 place-items-center rounded-md text-stone-500 hover:bg-stone-200"
                          aria-label={`${project.name} menu`}
                        >
                          <MoreHorizontal className="h-4 w-4" />
                        </button>
                      </div>
                    )}
                    {projectMenuId === project.id ? (
                      <div onClick={(event) => event.stopPropagation()} className="absolute right-1 top-9 z-30 w-44 rounded-lg border border-stone-200 bg-white p-1.5 shadow-xl">
                        <MenuButton icon={<Pencil />} label="Rename" onClick={() => {
                          setRenamingProjectId(project.id);
                          setProjectRenameDraft(project.name);
                          setProjectMenuId(null);
                        }} />
                        <MenuButton icon={<Archive />} label="Archive" onClick={() => onArchiveProject(project)} />
                        <MenuButton icon={<Trash2 />} label="Delete" danger onClick={() => onDeleteProject(project)} />
                      </div>
                    ) : null}
                  </div>
                );
              })}
              {draggedConversation ? (
                <button
                  type="button"
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => {
                    event.preventDefault();
                    onMoveToProject(draggedConversation, null);
                    setDraggedConversationId(null);
                  }}
                  className="flex w-full items-center gap-2 rounded-lg border border-dashed border-stone-300 px-2 py-2 text-left text-sm text-stone-500 hover:bg-stone-100"
                >
                  <X className="h-4 w-4" />
                  Remove from project
                </button>
              ) : null}
            </div>
          ) : null}
        </section>

        <section className="mt-5 border-t border-stone-200/70 pt-4">
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
                renamingId={renamingId}
                renameDraft={renameDraft}
                setMenuId={setMenuId}
                setMoveMenuId={setMoveMenuId}
                setRenamingId={setRenamingId}
                setRenameDraft={setRenameDraft}
                setDraggedConversationId={setDraggedConversationId}
                onSelect={onSelect}
                onRename={submitRename}
                onArchive={onArchive}
                onDelete={onDelete}
                onPin={onPin}
                onDuplicate={onDuplicate}
                onShare={onShare}
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
                renamingId={renamingId}
                renameDraft={renameDraft}
                setMenuId={setMenuId}
                setMoveMenuId={setMoveMenuId}
                setRenamingId={setRenamingId}
                setRenameDraft={setRenameDraft}
                setDraggedConversationId={setDraggedConversationId}
                onSelect={onSelect}
                onRename={submitRename}
                onArchive={onArchive}
                onDelete={onDelete}
                onPin={onPin}
                onDuplicate={onDuplicate}
                onShare={onShare}
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
  renamingId,
  renameDraft,
  setMenuId,
  setMoveMenuId,
  setRenamingId,
  setRenameDraft,
  setDraggedConversationId,
  onSelect,
  onRename,
  onArchive,
  onDelete,
  onPin,
  onDuplicate,
  onShare,
  onMoveToProject,
}: {
  label: string;
  conversations: Conversation[];
  activeConversationId: string | null;
  projectById: Map<string, Project>;
  projects: Project[];
  menuId: string | null;
  moveMenuId: string | null;
  renamingId: string | null;
  renameDraft: string;
  setMenuId: (id: string | null) => void;
  setMoveMenuId: (id: string | null) => void;
  setRenamingId: (id: string | null) => void;
  setRenameDraft: (value: string) => void;
  setDraggedConversationId: (id: string | null) => void;
  onSelect: (conversation: Conversation) => void;
  onRename: (conversation: Conversation) => void;
  onArchive: (conversation: Conversation) => void;
  onDelete: (conversation: Conversation) => void;
  onPin: (conversation: Conversation, pinned: boolean) => void;
  onDuplicate: (conversation: Conversation) => void;
  onShare: (conversation: Conversation) => void;
  onMoveToProject: (conversation: Conversation, projectId: string | null) => void;
}) {
  return (
    <div>
      <p className="mb-1.5 px-1 text-xs font-medium text-stone-400">{label}</p>
      <div className="space-y-1">
        {conversations.map((conversation) => {
          const active = conversation.id === activeConversationId;
          const project = conversation.project_id ? projectById.get(conversation.project_id) : null;
          const renaming = renamingId === conversation.id;
          return (
            <div key={conversation.id} className="relative">
              <button
                type="button"
                draggable={!renaming}
                onDragStart={() => setDraggedConversationId(conversation.id)}
                onDragEnd={() => setDraggedConversationId(null)}
                onClick={() => {
                  if (!renaming) onSelect(conversation);
                }}
                className={cn("group flex w-full gap-2 rounded-lg px-2 py-2 text-left transition", active ? "bg-stone-900 text-white" : "text-stone-700 hover:bg-stone-100")}
              >
                {conversation.pinned ? <Pin className="mt-0.5 h-3.5 w-3.5 shrink-0" /> : <MessageSquare className="mt-0.5 h-3.5 w-3.5 shrink-0" />}
                <span className="min-w-0 flex-1">
                  {renaming ? (
                    <input
                      autoFocus
                      aria-label="Rename conversation"
                      value={renameDraft}
                      onChange={(event) => setRenameDraft(event.target.value)}
                      onClick={(event) => event.stopPropagation()}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") onRename(conversation);
                        if (event.key === "Escape") setRenamingId(null);
                      }}
                      onBlur={() => onRename(conversation)}
                      className="h-7 w-full rounded-md border border-stone-300 bg-white px-2 text-sm font-medium text-stone-950 outline-none"
                    />
                  ) : (
                    <>
                      <span className="block truncate text-sm font-medium">{conversation.title || "Untitled conversation"}</span>
                      <span className={cn("mt-0.5 block truncate text-xs", active ? "text-stone-300" : "text-stone-500")}>
                        {conversation.summary || project?.name || "Continue the conversation"}
                      </span>
                      <span className={cn("mt-1 block text-[11px]", active ? "text-stone-300" : "text-stone-400")}>{formatUpdatedAt(conversation.updated_at)}</span>
                    </>
                  )}
                </span>
              </button>
              {!renaming ? (
                <button
                  type="button"
                  onClick={(event) => {
                    event.stopPropagation();
                    setMoveMenuId(null);
                    setMenuId(menuId === conversation.id ? null : conversation.id);
                  }}
                  className={cn("absolute right-1 top-1 z-10 grid h-7 w-7 place-items-center rounded-md", active ? "text-stone-300 hover:bg-white/10" : "text-stone-500 hover:bg-stone-200")}
                  aria-label={`${conversation.title || "Untitled conversation"} menu`}
                >
                  <MoreHorizontal className="h-4 w-4" />
                </button>
              ) : null}
              {menuId === conversation.id ? (
                <div onClick={(event) => event.stopPropagation()} className="absolute right-1 top-9 z-20 w-52 rounded-lg border border-stone-200 bg-white p-1.5 shadow-xl">
                  <MenuButton icon={<Pencil />} label="Rename" onClick={() => {
                    setRenamingId(conversation.id);
                    setRenameDraft(conversation.title || "");
                    setMenuId(null);
                  }} />
                  <MenuButton icon={<Pin />} label={conversation.pinned ? "Unpin" : "Pin"} onClick={() => {
                    setMenuId(null);
                    onPin(conversation, !conversation.pinned);
                  }} />
                  <div className="relative">
                    <MenuButton icon={<Folder />} label="Move to Project" onClick={() => setMoveMenuId(moveMenuId === conversation.id ? null : conversation.id)} />
                    {moveMenuId === conversation.id ? (
                      <div className="absolute left-full top-0 z-30 ml-2 max-h-64 w-52 overflow-y-auto rounded-lg border border-stone-200 bg-white p-1.5 shadow-xl">
                        <MenuButton icon={<X />} label="No Project" onClick={() => {
                          setMenuId(null);
                          setMoveMenuId(null);
                          onMoveToProject(conversation, null);
                        }} />
                        {projects.map((project) => (
                          <MenuButton key={project.id} icon={<Folder />} label={project.name} onClick={() => {
                            setMenuId(null);
                            setMoveMenuId(null);
                            onMoveToProject(conversation, project.id);
                          }} />
                        ))}
                      </div>
                    ) : null}
                  </div>
                  <MenuButton icon={<Copy />} label="Duplicate" onClick={() => {
                    setMenuId(null);
                    onDuplicate(conversation);
                  }} />
                  <MenuButton icon={<Share2 />} label="Share" onClick={() => {
                    setMenuId(null);
                    onShare(conversation);
                  }} />
                  <MenuButton icon={<Archive />} label="Archive" onClick={() => {
                    setMenuId(null);
                    onArchive(conversation);
                  }} />
                  <MenuButton icon={<Trash2 />} label="Delete" danger onClick={() => {
                    setMenuId(null);
                    onDelete(conversation);
                  }} />
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ProjectEditor({
  label,
  value,
  onChange,
  onSubmit,
  onCancel,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  placeholder: string;
}) {
  return (
    <div className="flex items-center gap-1 rounded-lg bg-white p-1 shadow-sm">
      <input
        autoFocus
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") onSubmit();
          if (event.key === "Escape") onCancel();
        }}
        placeholder={placeholder}
        className="min-w-0 flex-1 rounded-md px-2 py-1.5 text-sm text-stone-950 outline-none placeholder:text-stone-400"
      />
      <button type="button" onClick={onSubmit} className="rounded-md px-2 py-1.5 text-xs font-medium text-stone-950 hover:bg-stone-100">Save</button>
      <button type="button" onClick={onCancel} className="grid h-7 w-7 place-items-center rounded-md text-stone-500 hover:bg-stone-100" aria-label="Cancel">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

function MenuButton({ icon, label, danger, onClick }: { icon: React.ReactElement; label: string; danger?: boolean; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className={cn("flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm text-stone-700 hover:bg-stone-100", danger && "text-rose-600 hover:bg-rose-50")}>
      <span className="grid h-4 w-4 shrink-0 place-items-center [&>svg]:h-4 [&>svg]:w-4">{icon}</span>
      <span className="truncate">{label}</span>
    </button>
  );
}

export const ConversationSidebar = memo(ConversationSidebarComponent);
