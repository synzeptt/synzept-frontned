"use client";

/**
 * PHASE 3: Execution Lifecycle Mapping
 * 
 * This utility maps backend ActionExecution status values to clear UI states
 * with consistent messaging, icons, and progress indicators.
 * 
 * Replaces: execution-state-utils.ts for ExecutionCard usage
 */

import { ActionExecution } from "@/lib/api";

// Status constants from backend
export const EXECUTION_STATUS = {
  PLANNING: "planning",
  QUEUED: "queued",
  RUNNING: "running",
  EXECUTING: "executing",
  WAITING_APPROVAL: "waiting_approval",
  AWAITING_CONFIRMATION: "awaiting_confirmation",
  COMPLETED: "completed",
  FAILED: "failed",
  CANCELLED: "cancelled",
} as const;

/**
 * Execution phase for clear UI grouping
 */
export type ExecutionPhase = "planning" | "executing" | "confirmation" | "completed" | "failed";

/**
 * Human-friendly status for display
 */
export type ExecutionDisplayStatus = 
  | "Planning the work"
  | "Preparing"
  | "Working on it"
  | "Waiting for approval"
  | "Complete"
  | "Couldn't complete this"
  | "Stopped";

/**
 * Maps backend status to execution phase
 */
export function getExecutionPhase(status: string): ExecutionPhase {
  switch (status) {
    case EXECUTION_STATUS.PLANNING:
    case EXECUTION_STATUS.QUEUED:
      return "planning";
    
    case EXECUTION_STATUS.RUNNING:
    case EXECUTION_STATUS.EXECUTING:
      return "executing";
    
    case EXECUTION_STATUS.WAITING_APPROVAL:
    case EXECUTION_STATUS.AWAITING_CONFIRMATION:
      return "confirmation";
    
    case EXECUTION_STATUS.COMPLETED:
      return "completed";
    
    case EXECUTION_STATUS.FAILED:
    case EXECUTION_STATUS.CANCELLED:
      return "failed";
    
    default:
      return "planning";
  }
}

/**
 * Maps backend status to human-friendly display string
 */
export function getExecutionDisplayStatus(status: string): ExecutionDisplayStatus {
  switch (status) {
    case EXECUTION_STATUS.PLANNING:
      return "Planning the work";
    case EXECUTION_STATUS.QUEUED:
      return "Preparing";
    case EXECUTION_STATUS.RUNNING:
    case EXECUTION_STATUS.EXECUTING:
      return "Working on it";
    case EXECUTION_STATUS.WAITING_APPROVAL:
    case EXECUTION_STATUS.AWAITING_CONFIRMATION:
      return "Waiting for approval";
    case EXECUTION_STATUS.COMPLETED:
      return "Complete";
    case EXECUTION_STATUS.FAILED:
      return "Couldn't complete this";
    case EXECUTION_STATUS.CANCELLED:
      return "Stopped";
    default:
      return "Planning the work";
  }
}

/**
 * Determines if execution is in a terminal state
 */
export function isExecutionTerminal(status: string): boolean {
  return [
    EXECUTION_STATUS.COMPLETED,
    EXECUTION_STATUS.FAILED,
    EXECUTION_STATUS.CANCELLED,
  ].includes(status as any);
}

/**
 * Determines if execution is waiting for user input
 */
export function isExecutionAwaitingInput(status: string): boolean {
  return [
    EXECUTION_STATUS.WAITING_APPROVAL,
    EXECUTION_STATUS.AWAITING_CONFIRMATION,
  ].includes(status as any);
}

/**
 * Determines if execution is actively working
 */
export function isExecutionActive(status: string): boolean {
  return [
    EXECUTION_STATUS.PLANNING,
    EXECUTION_STATUS.QUEUED,
    EXECUTION_STATUS.RUNNING,
    EXECUTION_STATUS.EXECUTING,
  ].includes(status as any);
}

/**
 * Gets icon type for status
 */
export function getExecutionStatusIcon(status: string): "loader" | "check" | "alert" | "clock" | "zap" {
  const phase = getExecutionPhase(status);
  
  switch (phase) {
    case "planning":
    case "executing":
      return "loader";
    case "completed":
      return "check";
    case "confirmation":
      return "clock";
    case "failed":
      return "alert";
    default:
      return "zap";
  }
}

/**
 * Gets progress percentage based on status
 * Returns 0-100 for visual progress bar
 */
export function getExecutionProgressPercentage(
  status: string,
  currentProgress?: number
): number {
  // If backend provides progress, use it (but cap at 95% while executing)
  if (currentProgress !== undefined && currentProgress > 0) {
    if (isExecutionTerminal(status)) {
      return currentProgress === 100 ? 100 : Math.max(currentProgress, 95);
    }
    return Math.min(currentProgress, 95);
  }

  // Fallback based on phase
  const phase = getExecutionPhase(status);
  switch (phase) {
    case "planning":
      return 15;
    case "confirmation":
      return 30;
    case "executing":
      return 60;
    case "completed":
      return 100;
    case "failed":
      return 35;
    default:
      return 0;
  }
}

/**
 * Gets color scheme based on phase
 */
export function getExecutionPhaseColors(phase: ExecutionPhase): {
  border: string;
  background: string;
  text: string;
  accent: string;
} {
  switch (phase) {
    case "planning":
      return {
        border: "border-stone-200",
        background: "bg-stone-50",
        text: "text-stone-900",
        accent: "text-stone-600",
      };
    
    case "executing":
      return {
        border: "border-blue-200",
        background: "bg-blue-50",
        text: "text-blue-900",
        accent: "text-blue-600",
      };
    
    case "confirmation":
      return {
        border: "border-amber-200",
        background: "bg-amber-50",
        text: "text-amber-900",
        accent: "text-amber-600",
      };
    
    case "completed":
      return {
        border: "border-green-200",
        background: "bg-green-50",
        text: "text-green-900",
        accent: "text-green-600",
      };
    
    case "failed":
      return {
        border: "border-red-200",
        background: "bg-red-50",
        text: "text-red-900",
        accent: "text-red-600",
      };
    
    default:
      return {
        border: "border-stone-200",
        background: "bg-stone-50",
        text: "text-stone-900",
        accent: "text-stone-600",
      };
  }
}

/**
 * Gets step status badge text
 */
export function getStepStatusBadge(stepStatus?: string): string {
  switch (stepStatus) {
    case "completed":
      return "Done";
    case "running":
      return "Now";
    case "pending":
      return "Upcoming";
    case "failed":
      return "Failed";
    default:
      return "Pending";
  }
}

/**
 * Determines if user can interact with execution (approve/reject)
 */
export function canUserInteract(status: string): boolean {
  return isExecutionAwaitingInput(status);
}

/**
 * Determines if user can retry execution
 */
export function canUserRetry(status: string): boolean {
  return [EXECUTION_STATUS.FAILED, EXECUTION_STATUS.CANCELLED].includes(status as any);
}

/**
 * Determines if user can cancel execution
 */
export function canUserCancel(status: string): boolean {
  return isExecutionActive(status);
}

/**
 * Full execution lifecycle description for tooltips/help
 */
export const EXECUTION_LIFECYCLE = {
  planning: {
    description: "Synzept is planning the best approach to your request.",
    action: "Synzept is understanding your goal and preparing steps.",
    nextStep: "Will move to confirmation or execution.",
  },
  queued: {
    description: "Your execution is queued and waiting to start.",
    action: "The work is being prepared.",
    nextStep: "Will begin executing soon.",
  },
  executing: {
    description: "Synzept is actively working on your request.",
    action: "Tools are running, information is being gathered, and work is progressing.",
    nextStep: "Will complete or may require confirmation.",
  },
  confirmation: {
    description: "Synzept has paused and is waiting for your approval.",
    action: "Review the action and decide whether to approve or reject.",
    nextStep: "Approve to continue, or reject to stop.",
  },
  completed: {
    description: "Your execution has completed successfully.",
    action: "Results are ready and artifacts have been created.",
    nextStep: "Review the results and download artifacts.",
  },
  failed: {
    description: "The execution encountered an error and could not complete.",
    action: "An issue occurred that prevented completion.",
    nextStep: "Review the error and try again.",
  },
  cancelled: {
    description: "The execution was stopped.",
    action: "You or the system cancelled this run.",
    nextStep: "You can start a new execution.",
  },
} as const;

/**
 * Debug helper: Show full status info
 */
export function getExecutionDebugInfo(execution: ActionExecution): string {
  const phase = getExecutionPhase(execution.status);
  const displayStatus = getExecutionDisplayStatus(execution.status);
  const progress = getExecutionProgressPercentage(execution.status, execution.progress);
  const isTerminal = isExecutionTerminal(execution.status);
  const isAwaitingInput = isExecutionAwaitingInput(execution.status);
  const isActive = isExecutionActive(execution.status);

  return `
Execution Debug Info:
- Backend Status: ${execution.status}
- Phase: ${phase}
- Display: ${displayStatus}
- Progress: ${progress}%
- Terminal: ${isTerminal}
- Awaiting Input: ${isAwaitingInput}
- Active: ${isActive}
- Title: ${execution.title}
- Request: ${execution.request}
- Created: ${execution.created_at}
- Updated: ${execution.updated_at}
- Error: ${execution.error || "none"}
- Output: ${execution.output ? execution.output.substring(0, 50) + "..." : "none"}
  `.trim();
}
