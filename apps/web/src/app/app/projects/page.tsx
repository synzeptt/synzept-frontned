"use client";

import { motion } from "framer-motion";
import { Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useWorkspaceStore } from "@/stores/workspace-store";

export default function ProjectsPage() {
  const projects = useWorkspaceStore((s) => s.projects);
  const createProject = useWorkspaceStore((s) => s.createProject);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Projects</h1>
          <p className="mt-1 text-sm text-muted-foreground">Organize work across AI-powered project spaces.</p>
        </div>
        <Button variant="primary" onClick={() => createProject("New Project")}>
          <Plus size={16} />
          Create project
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {projects.map((project, i) => (
          <motion.article
            key={project.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="surface p-5"
          >
            <div className="flex items-start justify-between gap-3">
              <h2 className="text-lg font-semibold">{project.name}</h2>
              <Badge variant="success">{project.status}</Badge>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">{project.description}</p>
            <div className="mt-4 flex flex-wrap gap-2">
              {project.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
                  {tag}
                </span>
              ))}
            </div>
          </motion.article>
        ))}
      </div>
    </div>
  );
}
