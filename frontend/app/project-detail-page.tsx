"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Archive, MessageSquare, Save } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Conversation, type Memory, type Note, type Project, type Task } from "@/lib/api";
import { useChatStore } from "@/stores/chat";
import { PageFrame } from "@frontend/components/layout/page-frame";

export function ProjectDetailPage({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [continuitySummary, setContinuitySummary] = useState("");
  const [loading, setLoading] = useState(true);
  const [editingSummary, setEditingSummary] = useState("");
  const setActiveProject = useChatStore().setActiveProject;

  useEffect(() => {
    setLoading(true);
    api.getProjectContext(projectId)
      .then((context) => {
        setProject(context.project);
        setConversations(context.conversations);
        setNotes(context.notes);
        setTasks(context.tasks);
        setMemories(context.memories);
        setContinuitySummary(context.continuity_summary);
        setEditingSummary(context.project.context_summary || context.continuity_summary);
      })
      .finally(() => setLoading(false));
  }, [projectId]);

  const openTasks = useMemo(() => tasks.filter((task) => !["done", "completed", "archived"].includes(task.status)), [tasks]);

  const saveSummary = async () => {
    if (!project) return;
    const updated = await api.updateProject(project.id, { context_summary: editingSummary });
    setProject(updated);
    setContinuitySummary(editingSummary);
  };

  const archive = async () => {
    if (!project) return;
    const updated = await api.archiveProject(project.id);
    setProject(updated);
  };

  return (
    <PageFrame
      eyebrow="Project"
      title={project?.name || "Project"}
      action={
        <div className="flex gap-2">
          <Link href="/chat" onClick={() => setActiveProject(projectId)}>
            <Button size="sm" variant="outline">
              <MessageSquare className="mr-1.5 h-4 w-4" />
              Continue
            </Button>
          </Link>
          <Button size="sm" variant="ghost" onClick={archive}>
            <Archive className="mr-1.5 h-4 w-4" />
            Archive
          </Button>
        </div>
      }
    >
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        {loading ? (
          <Skeleton className="h-40 rounded-md" />
        ) : (
          <>
            <section className="rounded-md border border-border bg-white p-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-sm font-medium text-stone-950">Continuity summary</p>
                <Button size="sm" variant="outline" onClick={saveSummary}>
                  <Save className="mr-1.5 h-4 w-4" />
                  Save
                </Button>
              </div>
              <textarea
                value={editingSummary}
                onChange={(event) => setEditingSummary(event.target.value)}
                className="min-h-28 w-full resize-none rounded-md border border-border bg-stone-50 px-3 py-2 text-sm leading-6 text-stone-700 outline-none focus:border-accent/40"
              />
              <p className="mt-3 text-xs leading-5 text-muted-foreground">{continuitySummary}</p>
            </section>
            <div className="grid gap-4 lg:grid-cols-3">
              <LinkedList title="Linked conversations" items={conversations.map((item) => ({ id: item.id, label: item.title || "Untitled", detail: item.summary || "" }))} />
              <LinkedList title="Linked notes" items={notes.map((item) => ({ id: item.id, label: item.title || "Untitled", detail: item.content }))} />
              <section className="rounded-md border border-border bg-white p-4">
                <p className="mb-3 text-sm font-medium text-stone-950">Linked tasks</p>
                <div className="space-y-2">
                  {openTasks.map((task) => (
                    <div key={task.id} className="rounded-md bg-stone-50 px-3 py-2">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm text-stone-700">{task.title}</p>
                        <Badge variant={task.priority === "high" ? "accent" : "muted"}>{task.priority}</Badge>
                      </div>
                    </div>
                  ))}
                  {!openTasks.length && <p className="text-sm text-muted-foreground">No open linked tasks.</p>}
                </div>
              </section>
            </div>
            <LinkedList title="Project memory context" items={memories.map((item) => ({ id: item.id, label: item.category || item.memory_type, detail: item.content }))} />
          </>
        )}
      </div>
    </PageFrame>
  );
}

function LinkedList({ title, items }: { title: string; items: Array<{ id: string; label: string; detail: string }> }) {
  return (
    <section className="rounded-md border border-border bg-white p-4">
      <p className="mb-3 text-sm font-medium text-stone-950">{title}</p>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="rounded-md bg-stone-50 px-3 py-2">
            <p className="truncate text-sm text-stone-700">{item.label}</p>
            {item.detail && <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>}
          </div>
        ))}
        {!items.length && <p className="text-sm text-muted-foreground">Nothing linked yet.</p>}
      </div>
    </section>
  );
}
