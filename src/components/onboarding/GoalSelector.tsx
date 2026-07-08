import { OptionCard } from "@/components/onboarding/OptionCard";
import type { OnboardingGoal } from "@/types/onboarding";

export type GoalSelectorProps = {
  goals: OnboardingGoal[];
  selectedGoals: OnboardingGoal[];
  onToggleGoal: (goal: OnboardingGoal) => void;
};

export function GoalSelector({ goals, selectedGoals, onToggleGoal }: GoalSelectorProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {goals.map((goal) => (
        <OptionCard
          key={goal}
          label={goal}
          selected={selectedGoals.includes(goal)}
          onSelect={() => onToggleGoal(goal)}
        />
      ))}
    </div>
  );
}
