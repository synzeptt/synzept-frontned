import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { OnboardingProject } from "@/types/onboarding";

export type ProjectInputProps = {
  projects: OnboardingProject[];
  projectName: string;
  onProjectNameChange: (value: string) => void;
  onAddProject: () => void;
  onRemoveProject: (id: string) => void;
};

export function ProjectInput({ projects, projectName, onProjectNameChange, onAddProject, onRemoveProject }: ProjectInputProps) {
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <Input
          value={projectName}
          onChange={(event) => onProjectNameChange(event.target.value)}
          placeholder="Add a project like Synzept V2"
          aria-label="Current project name"
        />
        <Button onClick={onAddProject} disabled={!projectName.trim()} className="h-10 px-4">
          Add
        </Button>
      </div>
      <div className="space-y-2">
        {projects.map((project) => (
          <div key={project.id} className="flex items-center justify-between rounded-3xl border border-stone-200 bg-stone-50 px-4 py-3">
            <span className="text-sm text-stone-900">{project.name}</span>
            <button type="button" onClick={() => onRemoveProject(project.id)} className="text-sm font-medium text-stone-500 hover:text-stone-900 focus:outline-none focus:ring-2 focus:ring-accent/20 rounded-full px-2 py-1">
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
