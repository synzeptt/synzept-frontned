"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { NotebookText, Save, Trash2 } from "lucide-react";
import { Markdown } from "@/components/chat/markdown";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, type Note, type Project } from "@/lib/api";
import { cn } from "@/lib/cn";
import { PageFrame } from "@frontend/components/layout/page-frame";

export function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Note | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [projectId, setProjectId] = useState("");
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    setError(null);
    Promise.all([api.listNotes(), api.listProjects().catch(() => [])])
      .then(([noteRows, projectRows]) => {
        setNotes(noteRows);
        setProjects(projectRows);
      })
      .catch(() => setError("Notes could not load. Retry when the connection settles."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const q = search.toLowerCase().trim();
    if (!q) return notes;
    return notes.filter((note) => [note.title, note.content].some((value) => value?.toLowerCase().includes(q)));
  }, [notes, search]);

  const create = async (event: FormEvent) => {
    event.preventDefault();
    if (!content.trim()) return;
    setError(null);
    try {
      const note = await api.createNote({
        title: title.trim() || undefined,
        content: content.trim(),
        project_id: projectId || undefined,
      });
      void api.trackEvent("note_created", "notes", {
        note_id: note.id,
        project_id: projectId || null,
        has_title: Boolean(title.trim()),
      });
      setTitle("");
      setContent("");
      setProjectId("");
      setSelected(note);
      load();
    } catch {
      setError("Note could not be saved. Your draft is still here; try again.");
    }
  };

  const selectNote = (note: Note) => {
    setSelected(note);
    setEditTitle(note.title || "");
    setEditContent(note.content);
  };

  const updateSelected = async () => {
    if (!selected || !editContent.trim()) return;
    setError(null);
    try {
      const note = await api.updateNote(selected.id, {
        title: editTitle.trim() || null,
        content: editContent.trim(),
      });
      void api.trackEvent("note_updated", "notes", {
        note_id: note.id,
        project_id: note.project_id,
      });
      setSelected(note);
      load();
    } catch {
      setError("Note update failed. Your edited text is still on screen; retry before leaving.");
    }
  };

  const deleteSelected = async () => {
    if (!selected) return;
    setError(null);
    try {
      await api.deleteNote(selected.id);
      setSelected(null);
      setEditTitle("");
      setEditContent("");
      load();
    } catch {
      setError("Note could not be deleted. Try again when the connection is stable.");
    }
  };

  return (
    <PageFrame eyebrow="Context" title="Notes">
      <div className="grid h-full min-h-0 md:grid-cols-[320px_1fr]">
        <aside className="min-h-0 border-b border-border p-4 md:border-b-0 md:border-r">
          <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search notes" />
          <div className="mt-3 max-h-[34dvh] space-y-1 overflow-y-auto md:max-h-[calc(100dvh-160px)]">
            {loading ? (
              <Skeleton className="h-20 rounded-md" />
            ) : filtered.length ? (
              filtered.map((note) => (
                <button
                  key={note.id}
                  type="button"
                  onClick={() => selectNote(note)}
                  className={cn(
                    "w-full rounded-md px-3 py-2.5 text-left transition",
                    selected?.id === note.id ? "bg-stone-100" : "hover:bg-stone-50",
                  )}
                >
                  <p className="truncate text-sm text-stone-800">{note.title || "Untitled"}</p>
                  <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">{note.content}</p>
                </button>
              ))
            ) : (
              <EmptyState
                icon={<NotebookText className="h-5 w-5" />}
                title="No notes yet"
                description="Notes become useful context when you return to a project, decision, or conversation later."
                steps={[
                  "Save decisions you do not want to rediscover.",
                  "Capture open questions that should guide the next session.",
                  "Link notes to projects when they belong to ongoing work.",
                ]}
                className="mt-3 px-4 py-8"
              />
            )}
          </div>
        </aside>

        <section className="grid min-h-0 grid-rows-[auto_1fr]">
          <form onSubmit={create} className="border-b border-border p-4">
            <div className="mx-auto max-w-3xl space-y-3">
              <RecoveryBanner message={error} onRetry={load} />
              <div className="grid gap-3 md:grid-cols-[1fr_220px]">
                <Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Title" />
                <select
                  value={projectId}
                  onChange={(event) => setProjectId(event.target.value)}
                  className="h-10 rounded-md border border-border bg-white px-3 text-sm text-stone-800 outline-none"
                >
                  <option value="">No project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>
              <Textarea value={content} onChange={(event) => setContent(event.target.value)} placeholder="Capture context, a decision, or an open question" rows={5} />
              <Button type="submit" size="sm">
                <Save className="mr-1.5 h-4 w-4" />
                Save note
              </Button>
            </div>
          </form>
          <div className="min-h-0 overflow-y-auto p-5 md:p-7">
            {selected ? (
              <div className="mx-auto grid max-w-5xl gap-5 lg:grid-cols-2">
                <section className="space-y-3">
                  <Input value={editTitle} onChange={(event) => setEditTitle(event.target.value)} placeholder="Title" />
                  <Textarea value={editContent} onChange={(event) => setEditContent(event.target.value)} rows={14} />
                  <div className="flex gap-2">
                    <Button size="sm" onClick={updateSelected}>
                      <Save className="mr-1.5 h-4 w-4" />
                      Update
                    </Button>
                    <Button size="sm" variant="ghost" onClick={deleteSelected}>
                      <Trash2 className="mr-1.5 h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </section>
                <article>
                  <h2 className="mb-4 text-xl font-semibold text-stone-950">{editTitle || "Untitled"}</h2>
                  <Markdown content={editContent} />
                </article>
              </div>
            ) : (
              <EmptyState
                icon={<NotebookText className="h-5 w-5" />}
                title="Capture context worth returning to"
                description="Capture a decision, project thought, or open question. Synzept can use it later to restore context."
                steps={[
                  "A note can be rough.",
                  "The most useful notes explain what changed, why it matters, or what remains open.",
                ]}
              />
            )}
          </div>
        </section>
      </div>
    </PageFrame>
  );
}
