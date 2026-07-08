export type HomeFocus = {
  title: string;
  currentFocus: string;
  description: string;
};

export type SinceLastVisitItem = {
  id: string;
  text: string;
  completed?: boolean;
};

export type SuggestionCard = {
  id: string;
  title: string;
  description: string;
};

export type OpenLoopItem = {
  id: string;
  title: string;
};

export type HomeMockData = {
  userName: string;
  focus: HomeFocus;
  sinceLastVisit: SinceLastVisitItem[];
  suggestions: SuggestionCard[];
  openLoops: OpenLoopItem[];
  quickChatPrompts: string[];
};

export const homeMockData: HomeMockData = {
  userName: "Piyush",
  focus: {
    title: "Today’s focus",
    currentFocus: "Refine the Synzept home experience for returning users",
    description: "Keep the dashboard calm, clear, and focused on continuity, memory, and what to do next.",
  },
  sinceLastVisit: [
    { id: "item-1", text: "Deployment completed", completed: true },
    { id: "item-2", text: "Google Login fixed", completed: true },
    { id: "item-3", text: "Two memories learned" },
    { id: "item-4", text: "One project updated" },
  ],
  suggestions: [
    { id: "suggestion-1", title: "Improve onboarding", description: "Refine the first visit experience to keep context clear." },
    { id: "suggestion-2", title: "Review today’s memories", description: "Check what Synzept remembered about your current goals." },
    { id: "suggestion-3", title: "Finish Billing Flow", description: "Close the most important open loop before the next sprint." },
  ],
  openLoops: [
    { id: "loop-1", title: "Billing" },
    { id: "loop-2", title: "Landing Page" },
    { id: "loop-3", title: "First Beta" },
    { id: "loop-4", title: "Podcast Editing" },
  ],
  quickChatPrompts: ["What changed today?", "What should I focus on?", "Summarize my work."],
};
