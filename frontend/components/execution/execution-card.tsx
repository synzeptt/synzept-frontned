"use client";

import { CheckCircle2, AlertCircle, Loader2, Clock, Zap, FileText, Link2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ActionExecution } from "@/lib/api";
import { getExecutionPhase, getExecutionDisplayStatus, getExecutionProgressPercentage } from "@frontend/features/chat/execution-lifecycle";

export interface ExecutionStep {
  id?: string;
  title: string;
  tools?: string[];
  expected_output?: string;
  status?: "pending" | "running" | "completed" | "failed";
  progress?: number;
  tool_hint?: string;
  detail?: string;
}

export interface ExecutionCardProps {
  execution: ActionExecution | null;
  isStreaming?: boolean;
  pendingConfirmation?: boolean;
  onViewDetails?: () => void;
}

/**
 * ExecutionCard - Shows real execution progress with tool visibility
 *
 * Displays:
 * - What Synzept understood (goal)
 * - Planning status
 * - Current step being executed
 * - Which tools are being used
 * - Confirmation state if needed
 * - Progress percentage
 */
export function ExecutionCard({ execution, isStreaming = false, pendingConfirmation = false, onViewDetails }: ExecutionCardProps) {
  if (!execution) return null;

  const metadata = execution.metadata || {};
  const executionPlan = metadata.execution_plan as { steps?: ExecutionStep[] } | undefined;
  const steps = (executionPlan.steps || []) as ExecutionStep[];
  const currentStepIndex = steps.findIndex((s) => s.status === "running" || s.status === "pending");
  const currentStep = currentStepIndex >= 0 ? steps[currentStepIndex] : null;
  const completedSteps = steps.filter((s) => s.status === "completed" || s.status === "running").length;

  const isPlanning = execution.status === "planning";
  const isAwaiting = execution.status === "awaiting_confirmation";
  const isExecuting = execution.status === "executing" || execution.status === "running" || isStreaming;
  const isCompleted = execution.status === "completed";
  const isFailed = execution.status === "failed" || execution.status === "cancelled";

  // Use lifecycle utilities
  const phase = getExecutionPhase(execution.status);
  const displayStatus = getExecutionDisplayStatus(execution.status);
  const displayProgress = getExecutionProgressPercentage(execution.status, execution.progress);
  const hasSteps = steps.length > 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-stone-200 bg-white shadow-sm overflow-hidden"
    >
      {/* Header */}
      <div className="bg-gradient-to-r from-stone-50 to-white p-4 sm:p-5 border-b border-stone-200">
        <div className="flex items-start gap-3 sm:gap-4">
          <StatusIcon status={execution.status} isStreaming={isStreaming} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-stone-900">{execution.title}</p>
            <p className="text-xs text-stone-600 mt-1 line-clamp-2">{execution.request}</p>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-4 sm:p-5 space-y-4">
        {/* Status Message */}
        <div className="flex items-start gap-2">
          <div className="text-xs font-medium text-stone-600 mt-0.5">Status</div>
          <p className="text-sm text-stone-700">{displayStatus}</p>
        </div>

        {/* Progress Bar */}
        {(isPlanning || isExecuting) && (
          <div className="space-y-2">
            <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-black rounded-full"
                initial={{ width: "0%" }}
                animate={{ width: `${Math.min(displayProgress, 95)}%` }}
                transition={{ duration: 1 }}
              />
            </div>
            <p className="text-xs text-stone-500 text-right">{Math.min(displayProgress, 99)}%</p>
          </div>
        )}

        {/* Steps */}
        {hasSteps && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-stone-600">Steps</p>
            <div className="space-y-1.5">
              <AnimatePresence>
                {steps.map((step, idx) => (
                  <motion.div
                    key={step.id || idx}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: idx * 0.1 }}
                    className="flex items-start gap-2 text-sm"
                  >
                    <StepIcon status={step.status} />
                    <div className="flex-1 min-w-0">
                      <p className="text-stone-700 font-medium truncate">{step.title}</p>
                      {step.tool_hint && <p className="text-xs text-stone-500 mt-0.5">{step.tool_hint}</p>}
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>
        )}

        {/* Confirmation Required */}
        {pendingConfirmation && isAwaiting && (
          <div className="rounded-lg bg-amber-50 border border-amber-200 p-3">
            <p className="text-sm text-amber-900">
              Synzept needs your approval before continuing with {execution.action_type || "this action"}.
            </p>
          </div>
        )}

        {/* Error State */}
        {isFailed && execution.error && (
          <div className="rounded-lg bg-red-50 border border-red-200 p-3">
            <p className="text-sm text-red-900">{execution.error}</p>
          </div>
        )}

        {/* Result/Output */}
        {isCompleted && execution.output && (
          <div className="rounded-lg bg-green-50 border border-green-200 p-3">
            <p className="text-sm text-green-900 line-clamp-3">{execution.output}</p>
          </div>
        )}
      </div>

      {/* Footer - Actions */}
      {(isExecuting || isCompleted || isFailed) && (
        <div className="border-t border-stone-200 bg-stone-50 px-4 sm:px-5 py-3 flex items-center justify-end gap-2">
          {onViewDetails && (
            <button
              onClick={onViewDetails}
              className="text-xs font-medium text-stone-600 hover:text-stone-900 transition-colors"
            >
              View details
            </button>
          )}
        </div>
      )}
    </motion.div>
  );
}

/**
 * StatusIcon - Shows status indicator
 */
function StatusIcon({
  status,
  isStreaming,
}: {
  status: string;
  isStreaming: boolean;
}): React.ReactNode {
  if (isStreaming || status === "running" || status === "executing") {
    return (
      <div className="flex-shrink-0">
        <Loader2 className="h-5 w-5 text-stone-400 animate-spin" />
      </div>
    );
  }

  if (status === "completed") {
    return (
      <div className="flex-shrink-0">
        <CheckCircle2 className="h-5 w-5 text-green-600" />
      </div>
    );
  }

  if (status === "failed" || status === "cancelled") {
    return (
      <div className="flex-shrink-0">
        <AlertCircle className="h-5 w-5 text-red-600" />
      </div>
    );
  }

  if (status === "awaiting_confirmation" || status === "waiting_approval") {
    return (
      <div className="flex-shrink-0">
        <Clock className="h-5 w-5 text-amber-600" />
      </div>
    );
  }

  return (
    <div className="flex-shrink-0">
      <Zap className="h-5 w-5 text-stone-400" />
    </div>
  );
}

/**
 * StepIcon - Shows step status with icon
 */
function StepIcon({ status }: { status?: string }): React.ReactNode {
  if (status === "completed") {
    return (
      <div className="flex-shrink-0 mt-0.5">
        <CheckCircle2 className="h-4 w-4 text-green-600" />
      </div>
    );
  }

  if (status === "running") {
    return (
      <div className="flex-shrink-0 mt-0.5">
        <Loader2 className="h-4 w-4 text-stone-400 animate-spin" />
      </div>
    );
  }

  if (status === "failed") {
    return (
      <div className="flex-shrink-0 mt-0.5">
        <AlertCircle className="h-4 w-4 text-red-600" />
      </div>
    );
  }

  return (
    <div className="flex-shrink-0 mt-0.5 h-4 w-4 rounded-full border border-stone-300 bg-white" />
  );
}
