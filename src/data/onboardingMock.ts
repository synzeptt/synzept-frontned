import type {
  OnboardingGoal,
  OnboardingPreference,
  OnboardingProject,
  OnboardingRole,
  OnboardingTimeOfDay,
  OnboardingPlanningStyle,
} from "@/types/onboarding";

export const onboardingRoles: OnboardingRole[] = [
  "Student",
  "Founder",
  "Professional",
  "Developer",
  "Designer",
  "Creator",
  "Freelancer",
  "Other",
];

export const onboardingGoals: OnboardingGoal[] = [
  "Build a company",
  "Study",
  "Become healthier",
  "Grow my career",
  "Manage life",
  "Learn new skills",
  "Write consistently",
];

export const onboardingPreferences: OnboardingPreference[] = [
  "Remember important things",
  "Organize projects",
  "Plan my day",
  "Keep me accountable",
  "Answer questions",
  "Think with me",
  "Suggest next steps",
];

export const onboardingTimeOfDay: OnboardingTimeOfDay[] = [
  "Morning",
  "Afternoon",
  "Night",
  "Flexible",
];

export const onboardingPlanningStyles: OnboardingPlanningStyle[] = [
  "Daily",
  "Weekly",
  "Long-term",
  "Mixed",
];

export const onboardingSampleProjects: OnboardingProject[] = [
  { id: "project-1", name: "Synzept V2" },
  { id: "project-2", name: "BITS Preparation" },
  { id: "project-3", name: "Podcast" },
  { id: "project-4", name: "Fitness Journey" },
];
