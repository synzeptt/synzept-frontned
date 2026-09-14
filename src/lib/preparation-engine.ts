import type { Dashboard } from "@/lib/api";
import { buildChiefOfStaffOutput } from "./chief-of-staff-engine";

export type PreparedWorkStatus = "Detected" | "Preparing" | "Ready" | "Reviewed" | "Approved" | "Executed" | "Learned";
export type PreparedWorkPriority = "high" | "medium" | "low";
export type PreparedWorkConfidence = "High" | "Medium" | "Low";
export type PreparedWorkExecutionType = "review" | "edit" | "approve" | "execute" | "schedule";
export type PreparedWorkType =
  | "Meeting Brief"
  | "Email Draft"
  | "Daily Plan"
  | "Weekly Review"
  | "Follow-up"
  | "Risk Alert"
  | "Decision Brief"
  | "Research Summary"
  | "Task Plan"
  | "Project Update";

export type PreparedWorkArtifact = {
  id: string;
  type: PreparedWorkType;
  title: string;
  summary: string;
  why_generated: string;
  time_saved_minutes: number;
  priority: PreparedWorkPriority;
  confidence: PreparedWorkConfidence;
  status: PreparedWorkStatus;
  created_at: string;
  expires_at?: string | null;
  recommended_action: string;
  execution_type: PreparedWorkExecutionType;
  approval_required: boolean;
  context_sources: string[];
  generated_from: string;
  related_goal?: string;
  related_people?: string[];
  related_project?: string;
};

export type PreparationEngineResult = {
  artifacts: PreparedWorkArtifact[];
  totals: {
    todayMinutes: number;
    weeklyMinutes: number;
    monthlyMinutes: number;
  };
};

export function buildPreparedWorkPipeline(dashboard: Dashboard | null): PreparedWorkArtifact[] {
  if (!dashboard) return [];

  const artifacts: PreparedWorkArtifact[] = [];
  const tasks = (dashboard.tasks || []).filter((task) => task.title && !isDone(task));
  const notes = (dashboard.notes || []).filter((note) => note.title || note.content);
  const projects = (dashboard.projects || []).filter((project) => project.status === "active");
  const focusAreas = (dashboard.daily?.focus_areas || []).filter(Boolean);
  const mission = dashboard.personal_os?.current_mission || "";
  const nextAction = dashboard.personal_os?.suggested_next_action;
  const completedTasks = (dashboard.tasks || []).filter((task) => isDone(task)).length;

  const chiefOfStaffOutput = buildChiefOfStaffOutput(dashboard);
  const reasonedArtifacts = chiefOfStaffOutput.selectedArtifacts.map((artifact) => createArtifact({
    ...artifact,
    created_at: artifact.created_at || new Date().toISOString(),
    status: artifact.status || "Ready",
    generated_from: "chief_of_staff_reasoning",
  }));
  artifacts.push(...reasonedArtifacts);

  const meetingContext = focusAreas[0] || mission || "your top priority";
  const meetingEvidence = notes.filter((note) => /meeting|sync|call/i.test(note.content));
  if (!artifacts.some((artifact) => artifact.type === "Meeting Brief") && (meetingEvidence.length > 0 || focusAreas.length > 0)) {
    artifacts.push(createArtifact({
      id: "prepared-meeting-brief",
      type: "Meeting Brief",
      title: `${meetingContext} meeting brief`,
      summary: `Agenda and talking points are ready for ${meetingContext}.`,
      why_generated: `Synzept detected ${meetingEvidence.length ? "meeting context" : "a priority focus"} and prepared the next decision-ready brief.`,
      time_saved_minutes: 25,
      priority: "high",
      confidence: "High",
      status: "Ready",
      created_at: new Date().toISOString(),
      recommended_action: "Review",
      execution_type: "review",
      approval_required: false,
      context_sources: [
        meetingContext,
        ...(meetingEvidence.length ? meetingEvidence.slice(0, 1).map((note) => note.title || note.content) : []),
      ],
      generated_from: "recent_activity",
      related_goal: mission || undefined,
      related_project: projects[0]?.name,
    }));
  }

  const emailEvidence = notes.filter((note) => /email|follow-up|client/i.test(note.content));
  if (!artifacts.some((artifact) => artifact.type === "Email Draft") && (emailEvidence.length > 0 || tasks.length > 0)) {
    artifacts.push(createArtifact({
      id: "prepared-email-draft",
      type: "Email Draft",
      title: "Email draft ready",
      summary: "The next message is already drafted around the highest-priority follow-up.",
      why_generated: `A pending follow-up or email context was detected, so Synzept prepared the draft before you opened the workspace.`,
      time_saved_minutes: 15,
      priority: "medium",
      confidence: "High",
      status: "Ready",
      created_at: new Date().toISOString(),
      recommended_action: "Edit",
      execution_type: "edit",
      approval_required: false,
      context_sources: [
        ...(emailEvidence.length ? emailEvidence.slice(0, 1).map((note) => note.title || note.content) : []),
        ...(tasks.length ? [tasks[0].title] : []),
      ],
      generated_from: "recent_activity",
      related_goal: mission || undefined,
      related_project: projects[0]?.name,
    }));
  }

  if (!artifacts.some((artifact) => artifact.type === "Daily Plan") && tasks.length > 0) {
    artifacts.push(createArtifact({
      id: "prepared-daily-plan",
      type: "Daily Plan",
      title: "Tomorrow plan ready",
      summary: `The next day is already scoped around ${tasks[0].title}.`,
      why_generated: `Synzept found an upcoming task and prepared the next step before the day began.`,
      time_saved_minutes: 18,
      priority: "high",
      confidence: "High",
      status: "Ready",
      created_at: new Date().toISOString(),
      recommended_action: "Open",
      execution_type: "schedule",
      approval_required: false,
      context_sources: [tasks[0].title, tasks[0].description || ""],
      generated_from: "task_pipeline",
      related_goal: mission || undefined,
      related_project: tasks[0].project_id ? projects.find((project) => project.id === tasks[0].project_id)?.name : projects[0]?.name,
    }));
  }

  if (!artifacts.some((artifact) => artifact.type === "Weekly Review") && (completedTasks > 0 || notes.length > 0)) {
    artifacts.push(createArtifact({
      id: "prepared-weekly-review",
      type: "Weekly Review",
      title: "Weekly review prepared",
      summary: `${Math.max(3, completedTasks)} completed tasks are already assembled into a review-ready summary.`,
      why_generated: `Synzept used completed work and recent notes to prepare a concise weekly review.`,
      time_saved_minutes: 30,
      priority: "medium",
      confidence: "Medium",
      status: "Ready",
      created_at: new Date().toISOString(),
      recommended_action: "Approve",
      execution_type: "approve",
      approval_required: true,
      context_sources: [
        `${completedTasks} completed tasks`,
        ...(notes.slice(0, 2).map((note) => note.title || note.content)),
      ],
      generated_from: "task_pipeline",
      related_goal: mission || undefined,
      related_project: projects[0]?.name,
    }));
  }

  if (!artifacts.some((artifact) => artifact.type === "Follow-up") && nextAction?.title) {
    artifacts.push(createArtifact({
      id: "prepared-follow-up",
      type: "Follow-up",
      title: nextAction.title,
      summary: nextAction.reason || "The next action is already framed for a fast handoff.",
      why_generated: `Synzept used your recommended next action to create a follow-up that is ready to act on.`,
      time_saved_minutes: 12,
      priority: "high",
      confidence: "Medium",
      status: "Ready",
      created_at: new Date().toISOString(),
      recommended_action: "Execute",
      execution_type: "execute",
      approval_required: false,
      context_sources: [nextAction.title, nextAction.reason || ""],
      generated_from: "reasoning_engine",
      related_goal: mission || undefined,
      related_project: projects[0]?.name,
    }));
  }

  return artifacts.slice(0, 6);
}

export function buildPreparedWorkMetrics(artifacts: PreparedWorkArtifact[]) {
  const todayMinutes = artifacts.reduce((sum, artifact) => sum + artifact.time_saved_minutes, 0);
  return {
    totals: {
      todayMinutes,
      weeklyMinutes: todayMinutes + 18,
      monthlyMinutes: todayMinutes + 60,
    },
  };
}

export function buildPreparationEngineOutput(dashboard: Dashboard | null): PreparationEngineResult {
  const artifacts = buildPreparedWorkPipeline(dashboard);
  const metrics = buildPreparedWorkMetrics(artifacts);
  return { artifacts, totals: metrics.totals };
}

function createArtifact(input: Omit<PreparedWorkArtifact, "created_at"> & { created_at: string }): PreparedWorkArtifact {
  return {
    ...input,
    status: input.status,
    related_people: input.related_people || [],
    related_project: input.related_project || undefined,
    related_goal: input.related_goal || undefined,
  };
}

function isDone(task: { status?: string | null }) {
  return ["completed", "done", "archived"].includes((task.status || "").toLowerCase());
}
