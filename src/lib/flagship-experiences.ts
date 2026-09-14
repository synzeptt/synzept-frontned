export type MeetingAssistantSnapshot = {
  title: string;
  objective: string;
  relationshipHistory: string[];
  previousDecisions: string[];
  relevantEmails: string[];
  relevantDocuments: string[];
  agenda: string[];
  questions: string[];
  risks: string[];
  decisionsRequired: string[];
  afterMeetingSummary: string;
  actionItems: string[];
  followUpEmailDraft: string;
  memoryUpdate: string;
};

export type DailyExecutiveBriefSnapshot = {
  headline: string;
  calendarOverview: string[];
  importantEmails: string[];
  projectHealth: string[];
  deadlines: string[];
  recommendedFocus: string;
  preparedDeliverables: string[];
  openRisks: string[];
  quickWins: string[];
};

export type WeeklyExecutiveReviewSnapshot = {
  headline: string;
  summary: string;
  wins: string[];
  challenges: string[];
  progressByProject: Array<{ project: string; detail: string }>;
  risks: string[];
  missedCommitments: string[];
  lessonsLearned: string[];
  suggestedPriorities: string[];
  strategicRecommendations: string[];
};

export function buildMeetingAssistantExperience(input: Partial<MeetingAssistantSnapshot> & { meetingName?: string; objective?: string }): MeetingAssistantSnapshot {
  const title = input.title || input.meetingName || "Meeting Assistant";
  const objective = input.objective || "Move the work forward without wasting time on preparation.";

  return {
    title,
    objective,
    relationshipHistory: input.relationshipHistory?.length ? input.relationshipHistory : ["Use the most recent context and recent memory to set the right tone for the room."],
    previousDecisions: input.previousDecisions?.length ? input.previousDecisions : ["Review the latest decision history so the conversation does not repeat old ground."],
    relevantEmails: input.relevantEmails?.length ? input.relevantEmails : ["Surface the most relevant email trail so the meeting stays grounded in recent context."],
    relevantDocuments: input.relevantDocuments?.length ? input.relevantDocuments : ["Bring the most useful notes, briefs, and project documents into the conversation."],
    agenda: input.agenda?.length ? input.agenda : ["Confirm the decision required", "Review the risk and tradeoff", "Leave with a clear owner and next step"],
    questions: input.questions?.length ? input.questions : ["What matters most right now?", "What would materially change the decision?"],
    risks: input.risks?.length ? input.risks : ["The discussion could become too broad without a clear decision point."],
    decisionsRequired: input.decisionsRequired?.length ? input.decisionsRequired : ["What should be prioritized now?", "Who owns the follow-up?"],
    afterMeetingSummary: input.afterMeetingSummary || "Capture the outcome, the agreements, and the follow-up in one place so the work does not lose momentum.",
    actionItems: input.actionItems?.length ? input.actionItems : ["Create the next task", "Draft the follow-up email", "Store the decision in memory"],
    followUpEmailDraft: input.followUpEmailDraft || "A concise follow-up email should recap the decision, owner, and next milestone.",
    memoryUpdate: input.memoryUpdate || "Update memory with the decision, the relationship context, and the next action so future prep is sharper.",
  };
}

export function buildDailyExecutiveBriefExperience(input: Partial<DailyExecutiveBriefSnapshot> & { recommendedFocus?: string; preparedDeliverables?: string[] }): DailyExecutiveBriefSnapshot {
  const headline = input.headline || "Your day is already scoped for the highest-value work.";
  const recommendedFocus = input.recommendedFocus || "Protect focus time before the day becomes reactive.";

  return {
    headline,
    calendarOverview: input.calendarOverview?.length ? input.calendarOverview : ["Keep the day structured enough to protect the most important work before meetings begin."],
    importantEmails: input.importantEmails?.length ? input.importantEmails : ["Use the most relevant recent email context to keep the day aligned with what matters."],
    projectHealth: input.projectHealth?.length ? input.projectHealth : ["Monitor the projects that are closest to a milestone or a potential risk."],
    deadlines: input.deadlines?.length ? input.deadlines : ["Surface the commitments that need attention before they become urgent."],
    recommendedFocus,
    preparedDeliverables: input.preparedDeliverables?.length ? input.preparedDeliverables : ["One high-quality deliverable is already prepared for review."],
    openRisks: input.openRisks?.length ? input.openRisks : ["Watch the blockers that could slow momentum if they do not get attention soon."],
    quickWins: input.quickWins?.length ? input.quickWins : ["Close one small loop before the day gets away from you."],
  };
}

export function buildWeeklyExecutiveReviewSnapshot(input: Partial<WeeklyExecutiveReviewSnapshot>): WeeklyExecutiveReviewSnapshot {
  return {
    headline: input.headline || "The week is clear enough to steer with confidence.",
    summary: input.summary || "This review turns the week into decisions, priorities, and the next best move.",
    wins: input.wins?.length ? input.wins : ["The strongest progress points are the outcomes that moved the work forward most clearly."],
    challenges: input.challenges?.length ? input.challenges : ["The biggest challenge is the friction that slowed momentum or consumed attention."],
    progressByProject: input.progressByProject?.length ? input.progressByProject : [{ project: "General priorities", detail: "The work still needs a stronger thread to stay coherent." }],
    risks: input.risks?.length ? input.risks : ["The next risk is allowing too much unresolved work to accumulate."],
    missedCommitments: input.missedCommitments?.length ? input.missedCommitments : ["Any missed commitments should be reframed as a decision about what deserves focus next."],
    lessonsLearned: input.lessonsLearned?.length ? input.lessonsLearned : ["One useful lesson should become the next operating principle for the week ahead."],
    suggestedPriorities: input.suggestedPriorities?.length ? input.suggestedPriorities : ["Protect the highest-value work and reduce the number of unfinished loops."],
    strategicRecommendations: input.strategicRecommendations?.length ? input.strategicRecommendations : ["Carry the best signal forward and make the next week narrower, not broader."],
  };
}
