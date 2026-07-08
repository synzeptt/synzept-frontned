import type { OnboardingProject, OnboardingPreference, OnboardingGoal, OnboardingPlanningStyle, OnboardingRole, OnboardingTimeOfDay } from "@/types/onboarding";
import { Button } from "@/components/ui/button";

export type SummaryScreenProps = {
  role?: OnboardingRole;
  goals: OnboardingGoal[];
  projects: OnboardingProject[];
  preferences: OnboardingPreference[];
  timeOfDay?: OnboardingTimeOfDay;
  planningStyle?: OnboardingPlanningStyle;
  onEdit: () => void;
  onComplete: () => void;
};

function ItemRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-3xl border border-stone-200 bg-stone-50 px-5 py-4">
      <p className="text-xs uppercase tracking-[0.24em] text-stone-400">{label}</p>
      <p className="text-sm font-medium text-stone-950">{value}</p>
    </div>
  );
}

export function SummaryScreen({ role, goals, projects, preferences, timeOfDay, planningStyle, onEdit, onComplete }: SummaryScreenProps) {
  return (
    <section className="rounded-[32px] border border-stone-200 bg-white px-6 py-8 shadow-soft sm:px-8 sm:py-10">
      <div className="space-y-4">
        <p className="text-sm font-semibold uppercase tracking-[0.28em] text-stone-400">Here's what I learned</p>
        <h2 className="text-3xl font-semibold tracking-tight text-stone-950">A personalized workspace is almost ready.</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <ItemRow label="Role" value={role ?? "Not selected"} />
          <ItemRow label="Time of day" value={timeOfDay ?? "Not selected"} />
          <ItemRow label="Planning style" value={planningStyle ?? "Not selected"} />
          <ItemRow label="Goals" value={goals.length > 0 ? goals.join(", ") : "Not selected"} />
        </div>
        <div className="rounded-3xl border border-stone-200 bg-stone-50 p-5">
          <p className="text-xs uppercase tracking-[0.24em] text-stone-400">Projects</p>
          <div className="mt-3 space-y-2">
            {projects.length > 0 ? (
              projects.map((project) => (
                <p key={project.id} className="text-sm text-stone-700">{project.name}</p>
              ))
            ) : (
              <p className="text-sm text-stone-700">No projects added yet.</p>
            )}
          </div>
        </div>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <Button onClick={onComplete} className="w-full py-4 text-base font-semibold">
            Enter Workspace
          </Button>
          <button type="button" onClick={onEdit} className="text-sm font-medium text-stone-700 underline-offset-4 hover:underline">
            Edit responses
          </button>
        </div>
      </div>
    </section>
  );
}
