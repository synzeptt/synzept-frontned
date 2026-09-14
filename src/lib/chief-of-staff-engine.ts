import type { Dashboard } from "@/lib/api";
import type { PreparedWorkArtifact } from "./preparation-engine";

export type ChiefOfStaffReasoningCategory =
  | "Mission"
  | "Projects"
  | "Meetings"
  | "Communication"
  | "Deadlines"
  | "Relationships"
  | "Learning"
  | "Health"
  | "Personal Goals"
  | "Business";

export type ChiefOfStaffRecommendation = {
  id: string;
  reason: string;
  priority: "high" | "medium" | "low";
  urgency: "high" | "medium" | "low";
  importance: "high" | "medium" | "low";
  estimated_value: number;
  estimated_time_saved: number;
  confidence: "High" | "Medium" | "Low";
  suggested_artifact_types: Array<PreparedWorkArtifact["type"]>;
  suggested_automation: string[];
  deadline_sensitivity: "high" | "medium" | "low";
  affected_people: string[];
  affected_goals: string[];
  affected_projects: string[];
  evidence: string[];
  category: ChiefOfStaffReasoningCategory;
  recommended_action: string;
  conflict?: string;
};

export type ChiefOfStaffEngineResult = {
  recommendations: ChiefOfStaffRecommendation[];
  selectedArtifacts: PreparedWorkArtifact[];
};

export function buildChiefOfStaffRecommendations(dashboard: Dashboard | null): ChiefOfStaffRecommendation[] {
  if (!dashboard) return [];

  const tasks = (dashboard.tasks || []).filter((task) => task.title && !isDone(task));
  const noteItems = (dashboard.notes || []).filter((note) => note.title || note.content);
  const focusAreas = (dashboard.daily?.focus_areas || []).filter(Boolean);
  const mission = dashboard.personal_os?.current_mission || "";
  const nextAction = dashboard.personal_os?.suggested_next_action;
  const projects = (dashboard.projects || []).filter((project) => project.status === "active");
  const memories = (dashboard.memories || []).slice(0, 3);
  const recommendations: ChiefOfStaffRecommendation[] = [];

  if (focusAreas.length > 0) {
    recommendations.push(createRecommendation({
      id: "recommend-meeting-brief",
      reason: "A priority focus is active and a meeting-ready brief would reduce friction before work begins.",
      priority: "high",
      urgency: "high",
      importance: "high",
      estimated_value: 92,
      estimated_time_saved: 25,
      confidence: "High",
      suggested_artifact_types: ["Meeting Brief"],
      suggested_automation: ["Auto-open the brief at start of day"],
      deadline_sensitivity: "high",
      affected_people: ["You"],
      affected_goals: [mission].filter(Boolean),
      affected_projects: projects.map((project) => project.name).slice(0, 1),
      evidence: [focusAreas[0], ...(noteItems.slice(0, 1).map((note) => note.title || note.content))],
      category: "Meetings",
      recommended_action: "Prepare the meeting brief now",
    }));
  }

  if (tasks.length > 0) {
    recommendations.push(createRecommendation({
      id: "recommend-daily-plan",
      reason: "An upcoming task is waiting for a clear next move.",
      priority: "high",
      urgency: "medium",
      importance: "high",
      estimated_value: 88,
      estimated_time_saved: 18,
      confidence: "High",
      suggested_artifact_types: ["Daily Plan"],
      suggested_automation: ["Add to tomorrow's checklist"],
      deadline_sensitivity: "medium",
      affected_people: ["You"],
      affected_goals: [mission].filter(Boolean),
      affected_projects: tasks[0].project_id ? projects.filter((project) => project.id === tasks[0].project_id).map((project) => project.name) : projects.map((project) => project.name).slice(0, 1),
      evidence: [tasks[0].title, tasks[0].description || ""],
      category: "Deadlines",
      recommended_action: "Prepare the next step for today",
    }));
  }

  if (nextAction?.title) {
    recommendations.push(createRecommendation({
      id: "recommend-follow-up",
      reason: "The recommended next action has clear execution value and should be staged before the day starts.",
      priority: "medium",
      urgency: "medium",
      importance: "medium",
      estimated_value: 76,
      estimated_time_saved: 12,
      confidence: "Medium",
      suggested_artifact_types: ["Follow-up"],
      suggested_automation: ["Queue the follow-up in the next available slot"],
      deadline_sensitivity: "low",
      affected_people: ["You"],
      affected_goals: [mission].filter(Boolean),
      affected_projects: projects.map((project) => project.name).slice(0, 1),
      evidence: [nextAction.title, nextAction.reason || ""],
      category: "Communication",
      recommended_action: "Stage the follow-up now",
    }));
  }

  if (noteItems.some((note) => /email|follow-up|client/i.test(note.content))) {
    recommendations.push(createRecommendation({
      id: "recommend-email-draft",
      reason: "An email or follow-up appears to be waiting and benefits from a ready draft.",
      priority: "medium",
      urgency: "medium",
      importance: "medium",
      estimated_value: 72,
      estimated_time_saved: 15,
      confidence: "High",
      suggested_artifact_types: ["Email Draft"],
      suggested_automation: ["Draft the reply and store it in the workspace"],
      deadline_sensitivity: "medium",
      affected_people: ["You"],
      affected_goals: [mission].filter(Boolean),
      affected_projects: projects.map((project) => project.name).slice(0, 1),
      evidence: noteItems.filter((note) => /email|follow-up|client/i.test(note.content)).slice(0, 1).map((note) => note.title || note.content),
      category: "Communication",
      recommended_action: "Prepare the email draft",
    }));
  }

  if (tasks.length > 1) {
    recommendations.push(createRecommendation({
      id: "recommend-conflict",
      reason: "Multiple active tasks may compete for the same focus window.",
      priority: "medium",
      urgency: "high",
      importance: "high",
      estimated_value: 81,
      estimated_time_saved: 10,
      confidence: "Medium",
      suggested_artifact_types: ["Decision Brief"],
      suggested_automation: ["Highlight the most important task first"],
      deadline_sensitivity: "high",
      affected_people: ["You"],
      affected_goals: [mission].filter(Boolean),
      affected_projects: projects.map((project) => project.name).slice(0, 1),
      evidence: tasks.slice(0, 2).map((task) => task.title),
      category: "Projects",
      recommended_action: "Resolve the priority conflict",
      conflict: "Too much work today",
    }));
  }

  if (memories.length > 0) {
    recommendations.push(createRecommendation({
      id: "recommend-learning",
      reason: "Recent memory signals suggest this user benefits from a personalized follow-up or reminder.",
      priority: "low",
      urgency: "low",
      importance: "medium",
      estimated_value: 58,
      estimated_time_saved: 8,
      confidence: "Low",
      suggested_artifact_types: ["Research Summary"],
      suggested_automation: ["Store as a follow-up prompt for later"],
      deadline_sensitivity: "low",
      affected_people: ["You"],
      affected_goals: [mission].filter(Boolean),
      affected_projects: projects.map((project) => project.name).slice(0, 1),
      evidence: memories.map((memory) => memory.summary || memory.content),
      category: "Learning",
      recommended_action: "Capture the learning signal",
    }));
  }

  return recommendations.sort((left, right) => scoreRecommendation(right) - scoreRecommendation(left));
}

export function buildChiefOfStaffOutput(dashboard: Dashboard | null) {
  const recommendations = buildChiefOfStaffRecommendations(dashboard);
  const selected = recommendations
    .filter((recommendation) => recommendation.priority === "high" || recommendation.estimated_value >= 80)
    .slice(0, 4);

  return {
    recommendations,
    selectedArtifacts: selected.map((recommendation) => ({
      id: recommendation.id,
      type: recommendation.suggested_artifact_types[0] || "Daily Plan",
      title: recommendation.reason,
      summary: recommendation.recommended_action,
      why_generated: recommendation.reason,
      time_saved_minutes: recommendation.estimated_time_saved,
      priority: recommendation.priority,
      confidence: recommendation.confidence,
      status: "Ready" as const,
      created_at: new Date().toISOString(),
      recommended_action: recommendation.recommended_action,
      execution_type: (recommendation.suggested_artifact_types[0] === "Email Draft" ? "edit" : recommendation.suggested_artifact_types[0] === "Follow-up" ? "execute" : recommendation.suggested_artifact_types[0] === "Decision Brief" ? "review" : "schedule") as PreparedWorkArtifact["execution_type"],
      approval_required: recommendation.confidence === "Low",
      context_sources: recommendation.evidence,
      generated_from: "chief_of_staff_reasoning",
      related_goal: recommendation.affected_goals[0],
      related_people: recommendation.affected_people,
      related_project: recommendation.affected_projects[0],
    })),
  };
}

function createRecommendation(input: Omit<ChiefOfStaffRecommendation, "id"> & { id: string }): ChiefOfStaffRecommendation {
  return input;
}

function scoreRecommendation(recommendation: ChiefOfStaffRecommendation) {
  return recommendation.estimated_value + (recommendation.priority === "high" ? 20 : 0) + (recommendation.urgency === "high" ? 10 : 0) + (recommendation.confidence === "High" ? 10 : 0);
}

function isDone(task: { status?: string | null }) {
  return ["completed", "done", "archived"].includes((task.status || "").toLowerCase());
}
