export type OnboardingRole =
  | "Student"
  | "Founder"
  | "Professional"
  | "Developer"
  | "Designer"
  | "Creator"
  | "Freelancer"
  | "Other";

export type OnboardingGoal =
  | "Build a company"
  | "Study"
  | "Become healthier"
  | "Grow my career"
  | "Manage life"
  | "Learn new skills"
  | "Write consistently";

export type OnboardingPreference =
  | "Remember important things"
  | "Organize projects"
  | "Plan my day"
  | "Keep me accountable"
  | "Answer questions"
  | "Think with me"
  | "Suggest next steps";

export type OnboardingTimeOfDay = "Morning" | "Afternoon" | "Night" | "Flexible";
export type OnboardingPlanningStyle = "Daily" | "Weekly" | "Long-term" | "Mixed";

export type OnboardingProject = {
  id: string;
  name: string;
};

export interface OnboardingState {
  step: number;
  role?: OnboardingRole;
  goals: OnboardingGoal[];
  projects: OnboardingProject[];
  preferences: OnboardingPreference[];
  timeOfDay?: OnboardingTimeOfDay;
  planningStyle?: OnboardingPlanningStyle;
}
