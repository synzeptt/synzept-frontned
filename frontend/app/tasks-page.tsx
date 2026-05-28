"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { Check, Circle, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type Project, type Task } from "@/lib/api";
import { cn } from "@/lib/cn";
import { PageFrame } from "@frontend/components/layout/page-frame";

const priorities = ["low", "medium", "high"] as const;
const filters = ["open", "done", "all"] as const;

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState("medium");
  const [projectId, setProjectId] = useState("");
  const [filter, setFilter] = useState<(typeof filters)[number]>("open");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([api.listTasks(), api.listProjects().catch(() => [])])
      .then(([taskRows, projectRows]) => {
        setTasks(taskRows);
        setProjects(projectRows);
      })
      .catch(() => setError("Tasks could not load. Retry when the connection settles."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const visible = useMemo(
    () =>
      tasks.filter((task) => {
        if (filter === "open") return !["completed", "archived", "done"].includes(task.status);
        if (filter === "done") return ["completed", "done"].includes(task.status);
        return true;
      }),
    [filter, tasks],
  );

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) return;
    setError(null);
    try {
      const task = await api.createTask({ title: title.trim(), priority, project_id: projectId || undefined });
      void api.trackEvent("task_created", "tasks", {
        task_id: task.id,
        priority,
        project_id: projectId || null,
      });
      setTitle("");
      setProjectId("");
      load();
    } catch {
      setError("Task could not be saved. Your text is still here; try again.");
    }
  };

  const toggle = async (task: Task) => {
    const previousTasks = tasks;
    const nextStatus = ["completed", "done"].includes(task.status) ? "todo" : "completed";
    setError(null);
    setTasks((current) => current.map((item) => (item.id === task.id ? { ...item, status: nextStatus } : item)));
    try {
      const updated = await api.updateTask(task.id, { status: nextStatus });
      void api.trackEvent(nextStatus === "completed" ? "task_completed" : "task_reopened", "tasks", {
        task_id: task.id,
        project_id: task.project_id,
      });
      setTasks((current) => current.map((item) => (item.id === task.id ? updated : item)));
    } catch {
      setTasks(previousTasks);
      setError("Task status could not be updated. Nothing was lost; try again.");
    }
  };

  return (
    <PageFrame eyebrow="Next actions" title="Tasks">
      <div className="mx-auto max-w-4xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        <form onSubmit={create} className="grid gap-3 rounded-xl border border-border bg-white p-4 shadow-soft md:grid-cols-[1fr_140px_180px_auto]">
          <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="What should stay visible?" />
          <select value={priority} onChange={(event) => setPriority(event.target.value)} className="h-10 rounded-md border border-border bg-white px-3 text-sm text-stone-800 outline-none">
            {priorities.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
          <select value={projectId} onChange={(event) => setProjectId(event.target.value)} className="h-10 rounded-md border border-border bg-white px-3 text-sm text-stone-800 outline-none">
            <option value="">No project</option>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </select>
          <Button type="submit">
            <Plus className="mr-1.5 h-4 w-4" />
            Add
          </Button>
        </form>

        <div className="flex gap-1 rounded-md border border-border bg-white p-1 w-fit">
          {filters.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setFilter(item)}
              className={cn(
                "h-8 rounded px-3 text-xs capitalize transition",
                filter === item ? "bg-stone-100 text-stone-950" : "text-muted-foreground hover:text-stone-800",
              )}
            >
              {item}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-14 rounded-md" />
            <Skeleton className="h-14 rounded-md" />
          </div>
        ) : (
          <div className="space-y-2">
            {visible.map((task) => (
              <div key={task.id} className="flex items-center justify-between gap-4 rounded-lg border border-border bg-white px-4 py-3 shadow-soft transition duration-150 hover:bg-stone-50">
                <button type="button" onClick={() => toggle(task)} className="flex min-w-0 items-start gap-3 text-left">
                  <span className="mt-0.5 text-muted-foreground">{["completed", "done"].includes(task.status) ? <Check className="h-4 w-4" /> : <Circle className="h-4 w-4" />}</span>
                  <span className={cn("text-sm", ["completed", "done"].includes(task.status) ? "text-muted line-through" : "text-stone-800")}>{task.title}</span>
                </button>
                <Badge variant={task.priority === "high" ? "accent" : "muted"}>{task.priority}</Badge>
              </div>
            ))}
            {!visible.length && (
              <EmptyState
                icon={<Circle className="h-5 w-5" />}
                title={filter === "done" ? "Completed work will collect here" : "No open tasks need attention"}
                description={
                  filter === "done"
                    ? "As you close loops, Synzept keeps a quiet record of momentum."
                    : "Add the next concrete action so tomorrow starts with less searching and more continuity."
                }
                steps={
                  filter === "done"
                    ? ["Completed tasks stay available as progress context."]
                    : ["Write the next visible action.", "Choose high only when it truly needs attention.", "Link it to a project when it belongs to ongoing work."]
                }
              />
            )}
          </div>
        )}
      </div>
    </PageFrame>
  );
}
