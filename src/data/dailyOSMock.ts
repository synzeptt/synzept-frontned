export type DailyOSHighestPriority = {
  title: string;
  reason: string;
  impact: string;
  actionLabel: string;
};

export type DailyOSChangeItem = {
  id: string;
  text: string;
  completed: boolean;
};

export type DailyOSOpenLoop = {
  id: string;
  title: string;
  priority: "High" | "Medium" | "Low";
  lastUpdated: string;
  nextStep: string;
};

export type DailyOSProgressItem = {
  id: string;
  area: string;
  detail: string;
  value: string;
};

export type DailyOSInsight = {
  id: string;
  title: string;
  detail: string;
};

export type DailyOSRecommendation = {
  id: string;
  title: string;
  reason: string;
  benefit: string;
  actionLabel: string;
};

export type DailyOSMockData = {
  userName: string;
  highestPriority: DailyOSHighestPriority;
  sinceLastVisit: DailyOSChangeItem[];
  openLoops: DailyOSOpenLoop[];
  progress: DailyOSProgressItem[];
  insights: DailyOSInsight[];
  recommendations: DailyOSRecommendation[];
  quickChatPrompts: string[];
};

export const dailyOSMock: DailyOSMockData = {
  userName: "Piyush",
  highestPriority: {
    title: "Finalize the Synzept Daily OS experience",
    reason: "This is the first screen returning users see, and it should clearly surface priorities, progress, and what to do next.",
    impact: "High impact: improves daily return, focus, and trust.",
    actionLabel: "Continue Working",
  },
  sinceLastVisit: [
    { id: "change-1", text: "Homepage brief updated", completed: true },
    { id: "change-2", text: "Google Login fixed", completed: true },
    { id: "change-3", text: "Three new memories learned", completed: false },
    { id: "change-4", text: "Project intelligence refreshed", completed: false },
  ],
  openLoops: [
    { id: "loop-1", title: "Landing page copy", priority: "High", lastUpdated: "2 days ago", nextStep: "Confirm messaging with design" },
    { id: "loop-2", title: "Billing flow review", priority: "Medium", lastUpdated: "4 days ago", nextStep: "Audit status and fix validation" },
    { id: "loop-3", title: "Podcast planning", priority: "Medium", lastUpdated: "5 days ago", nextStep: "Draft the episode outline" },
    { id: "loop-4", title: "Beta onboarding checklist", priority: "Low", lastUpdated: "6 days ago", nextStep: "Add the final test case" },
  ],
  progress: [
    { id: "progress-1", area: "Projects", detail: "2 active projects being tracked", value: "On track" },
    { id: "progress-2", area: "Goals", detail: "One goal is within reach", value: "72% complete" },
    { id: "progress-3", area: "Habits", detail: "Daily return streak maintained", value: "4 days" },
    { id: "progress-4", area: "Learning", detail: "New memory signals captured", value: "3 topics" },
  ],
  insights: [
    { id: "insight-1", title: "Focus drift detected", detail: "Marketing has not been touched in five days. Consider a small action to keep momentum." },
    { id: "insight-2", title: "Priority cadence looks strong", detail: "You usually complete the highest priority before noon on days with clear focus." },
    { id: "insight-3", title: "Open loop risk", detail: "The billing flow loop has been waiting for review for 4 days." },
    { id: "insight-4", title: "Memory signal", detail: "Synzept remembered your last research idea about customer onboarding." },
  ],
  recommendations: [
    { id: "rec-1", title: "Finish onboarding testing", reason: "This closes a key open loop and frees time for new work.", benefit: "Reduces friction for new users.", actionLabel: "Review tests" },
    { id: "rec-2", title: "Invite five beta users", reason: "Early feedback will validate the launch direction.", benefit: "Improves product-market fit.", actionLabel: "Send invites" },
    { id: "rec-3", title: "Review yesterday’s memories", reason: "Use yesterday’s signals to refine today’s priorities.", benefit: "Keeps context fresh.", actionLabel: "Review memories" },
    { id: "rec-4", title: "Prepare tomorrow’s priorities", reason: "A short planning note makes tomorrow easier to start.", benefit: "Increases next-day clarity.", actionLabel: "Plan ahead" },
  ],
  quickChatPrompts: ["What changed?", "Summarize my week.", "What should I do next?", "What am I forgetting?"],
};
