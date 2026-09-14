"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, AlertCircle, Loader2, ChevronDown, FileText, Download, ExternalLink, Pencil, Send } from "lucide-react";
import { api, type ActionExecution } from "@/lib/api";
import { ExecutionConfirmation } from "./execution-confirmation";
import { cn } from "@/lib/cn";
import { DEFAULT_EXECUTION_DETAILS_EXPANDED, downloadResultArtifact, hasUsableArtifact, isSimpleInformationalResult, openResultArtifact, type ResultArtifact } from "@/lib/execution-result-actions";

interface ExecutionTimelineProps {
  executionId: string;
  onComplete?: () => void;
  onError?: (error: string) => void;
}

type ExecutionPhase = "understanding" | "planning" | "executing" | "confirming" | "completed" | "failed";
type EmailDraft = { from?: string; to?: string; subject?: string; context?: string; reason?: string; suggested_reply?: string };

function determinePhase(execution: ActionExecution): ExecutionPhase {
  const status = execution.status.toLowerCase();
  
  if (status === "completed") return "completed";
  if (status === "failed" || status === "cancelled") return "failed";
  if (status === "awaiting_confirmation" || status === "waiting_approval") return "confirming";
  if (status === "executing" || status === "running") return "executing";
  if (status === "planning") return "planning";
  if (status === "queued" || status === "created") return "understanding";
  
  return "executing";
}

// Parse execution metadata to get activity steps
function getActivitySteps(execution: ActionExecution): Array<{ icon: string; title: string; status: "done" | "pending" | "current" }> {
  // Check metadata for activity log or use generic steps
  const metadata = execution.metadata as Record<string, unknown> || {};
  const activities = (metadata.activities as Array<{ title: string }> || []);
  
  // If we have logged activities, use them
  if (activities.length > 0) {
    const phase = determinePhase(execution);
    const phaseIndex = ["understanding", "planning", "executing", "completed"].indexOf(phase);
    
    return activities.slice(0, 5).map((activity, idx) => ({
      icon: "✓",
      title: activity.title || `Step ${idx + 1}`,
      status: idx < phaseIndex ? "done" : idx === phaseIndex ? "current" : "pending"
    }));
  }
  
  // Fallback: use generic steps based on phase
  const phase = determinePhase(execution);
  const steps: Array<{ icon: string; title: string; status: "done" | "pending" | "current" }> = [];
  
  if (phase === "understanding" || (["planning", "executing", "completed"].includes(phase))) {
    steps.push({ icon: "🧠", title: "Understanding your request", status: "done" });
  } else {
    steps.push({ icon: "🧠", title: "Understanding your request", status: "current" });
  }
  
  if (["planning", "executing", "completed"].includes(phase)) {
    steps.push({ icon: "📋", title: "Planning the approach", status: phase !== "planning" ? "done" : "current" });
  }
  
  if (["executing", "completed"].includes(phase)) {
    steps.push({ icon: "⚙️", title: "Executing the work", status: phase === "executing" ? "current" : "done" });
  }
  
  if (phase === "completed") {
    steps.push({ icon: "✅", title: "Work completed", status: "done" });
  } else if (phase === "failed") {
    steps.push({ icon: "❌", title: "Encountered an error", status: "done" });
  }
  
  return steps;
}

export function ExecutionTimeline({ executionId, onComplete, onError }: ExecutionTimelineProps) {
  const [execution, setExecution] = useState<ActionExecution | null>(null);
  const [loading, setLoading] = useState(true);
  const [isApproving, setIsApproving] = useState(false);
  const [isConfirmingSend, setIsConfirmingSend] = useState(false);
  const [editingDraft, setEditingDraft] = useState<number | null>(null);
  const [draftEdits, setDraftEdits] = useState<Record<number, EmailDraft>>({});
  const [expandedSteps, setExpandedSteps] = useState(DEFAULT_EXECUTION_DETAILS_EXPANDED);
  const [showFullResult, setShowFullResult] = useState(false);
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    const unsubscribe = api.subscribeToActionExecution(
      executionId,
      (exec) => {
        setExecution(exec);
        setLoading(false);

        const phase = determinePhase(exec);
        if (phase === "completed") {
          onComplete?.();
        } else if (phase === "failed") {
          onError?.(exec.error || "Task failed");
        }
      },
      3500,
      (err) => {
        setLoading(false);
        onError?.(err instanceof Error ? err.message : "Could not load execution");
      },
    );
    return unsubscribe;
  }, [executionId, onComplete, onError]);

  if (loading || !execution) {
    return (
      <div className="space-y-6">
        <div className="h-12 rounded-lg bg-stone-200 animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-lg bg-stone-100 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  const currentPhase = determinePhase(execution);
  const activitySteps = getActivitySteps(execution);
  const isError = currentPhase === "failed";
  const isCompleted = currentPhase === "completed";
  const isConfirming = currentPhase === "confirming";
  const emailDrafts = ((execution.metadata as Record<string, unknown> | undefined)?.email_work as { drafts?: EmailDraft[] } | undefined)?.drafts || [];
  const resultArtifacts = (((execution.metadata as Record<string, unknown> | undefined)?.artifacts || []) as ResultArtifact[]).filter((artifact) => artifact && typeof artifact === "object");
  const firstArtifact = resultArtifacts[0];
  const hasArtifact = hasUsableArtifact(firstArtifact);
  const isSimpleResult = isSimpleInformationalResult(execution);

  const downloadArtifact = () => {
    if (typeof document !== "undefined") downloadResultArtifact(firstArtifact, document);
  };

  const openArtifact = () => {
    if (typeof window !== "undefined") openResultArtifact(firstArtifact, window);
  };

  // Handle confirmation approval
  const handleApprove = async () => {
    if (!isConfirmingSend) {
      setIsConfirmingSend(true);
      return;
    }
    setIsApproving(true);
    try {
      await api.approveActionExecution(executionId);
      // Execution will continue after approval
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Could not approve";
      onError?.(errorMsg);
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    try {
      await api.rejectActionExecution(executionId);
      // Action was cancelled, execution will update on next poll
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Could not reject";
      onError?.(errorMsg);
    }
  };

  return (
    <div className="space-y-8">
      {/* CONFIRMATION STATE */}
      {isConfirming && emailDrafts.length > 0 ? (
        <div className="space-y-4 rounded-xl border border-amber-200 bg-amber-50/70 p-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-800">Review before sending</p>
            <h3 className="mt-2 text-lg font-semibold text-stone-900">Emails needing your response</h3>
            <p className="mt-1 text-sm leading-6 text-stone-700">Synzept prepared these replies. Nothing has been sent yet.</p>
          </div>
          <div className="space-y-3">
            {emailDrafts.map((draft, index) => (
              <article key={`${draft.subject || "draft"}-${index}`} className="rounded-lg border border-amber-200 bg-white p-4">
                <p className="text-sm font-semibold text-stone-900">{draft.from || "Email"} {draft.subject ? `- ${draft.subject}` : ""}</p>
                {draft.context && <p className="mt-2 text-sm leading-6 text-stone-600">{draft.context}</p>}
                {draft.reason && <p className="mt-2 text-xs font-medium text-amber-900">Why it needs attention: {draft.reason}</p>}
                {editingDraft === index ? (
                  <div className="mt-3 space-y-2 border-t border-stone-100 pt-3">
                    <input aria-label="Reply subject" value={draftEdits[index]?.subject ?? draft.subject ?? ""} onChange={(event) => setDraftEdits((current) => ({ ...current, [index]: { ...current[index], subject: event.target.value } }))} className="w-full rounded border border-stone-300 px-2 py-1 text-sm" />
                    <textarea aria-label="Suggested reply" value={draftEdits[index]?.suggested_reply ?? draft.suggested_reply ?? ""} onChange={(event) => setDraftEdits((current) => ({ ...current, [index]: { ...current[index], suggested_reply: event.target.value } }))} className="min-h-24 w-full rounded border border-stone-300 px-2 py-1 text-sm" />
                    <button type="button" onClick={async () => { const updated = await api.updateEmailDraft(executionId, index, draftEdits[index] || {}); setExecution(updated); setEditingDraft(null); }} className="rounded bg-stone-900 px-3 py-1.5 text-xs font-semibold text-white">Save edit</button>
                  </div>
                ) : draft.suggested_reply ? <p className="mt-3 border-t border-stone-100 pt-3 text-sm leading-6 text-stone-800"><span className="font-semibold">Suggested reply:</span> {draft.suggested_reply}</p> : null}
                {editingDraft !== index && <button type="button" onClick={() => setEditingDraft(index)} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-stone-700"><Pencil className="h-3 w-3" /> Edit draft</button>}
              </article>
            ))}
          </div>
          <div className="flex flex-wrap gap-2 border-t border-amber-200 pt-4">
            <button type="button" onClick={() => setShowFullResult((current) => !current)} className="rounded-lg border border-stone-300 bg-white px-4 py-2 text-sm font-medium text-stone-900 hover:bg-stone-50">{showFullResult ? "Hide details" : "Review details"}</button>
            {isConfirmingSend && <span className="flex items-center text-sm text-amber-950">This will send the reviewed replies through Gmail.</span>}
            <button type="button" onClick={handleApprove} disabled={isApproving} className="inline-flex items-center gap-2 rounded-lg bg-stone-900 px-4 py-2 text-sm font-semibold text-white hover:bg-stone-800 disabled:opacity-50"><Send className="h-4 w-4" />{isApproving ? "Approving..." : isConfirmingSend ? "Confirm send" : "Approve and send replies"}</button>
          </div>
        </div>
      ) : isConfirming && (
        <ExecutionConfirmation
          description={execution.request}
          action="send_email"
          details={[
            { label: "To", value: "rahul@company.com" },
            { label: "Subject", value: "Your AI Opportunities Report" },
          ]}
          isPending={isApproving}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}

      {/* ERROR STATE */}
      {isError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-6 space-y-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-red-900">Something went wrong</h3>
              <p className="mt-2 text-sm text-red-800 max-w-2xl">
                {execution.error || "An unexpected error occurred while processing your request"}
              </p>
            </div>
          </div>
          <button
            onClick={async () => {
              if (isRetrying) return;
              setIsRetrying(true);
              try {
                setExecution(await api.retryActionExecution(executionId));
              } catch (err) {
                onError?.(err instanceof Error ? err.message : "Could not retry execution");
              } finally {
                setIsRetrying(false);
              }
            }}
            disabled={isRetrying}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors text-sm font-medium"
          >
            {isRetrying ? "Retrying..." : "Try again"}
          </button>
        </div>
      )}

      {/* TASK HEADER */}
      {isCompleted && execution.output && (
        <div className="space-y-3">
          {!isSimpleResult && <h3 className="font-semibold text-stone-900">Here is what I prepared</h3>}
          <div className="rounded-xl border border-stone-200 bg-stone-50 p-6 space-y-4">
            {!isSimpleResult && <p className="text-xs font-medium text-stone-600 uppercase tracking-wide">Result</p>}
            <p className="text-sm text-stone-900 leading-relaxed max-w-2xl whitespace-pre-wrap">
              {showFullResult ? execution.output : execution.output.substring(0, 500)}
              {!showFullResult && execution.output.length > 500 && "..."}
            </p>
            {(execution.output.length > 500 || hasArtifact) && (
              <div className="flex flex-wrap gap-2 pt-2 border-t border-stone-200">
                {execution.output.length > 500 && <button type="button" onClick={() => setShowFullResult((current) => !current)} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white border border-stone-300 hover:bg-stone-50 text-sm font-medium text-stone-900 transition-colors"><FileText className="h-4 w-4" />{showFullResult ? "Hide Full Result" : "View Full Result"}</button>}
                {hasArtifact && <button type="button" onClick={downloadArtifact} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white border border-stone-300 hover:bg-stone-50 text-sm font-medium text-stone-900 transition-colors"><Download className="h-4 w-4" />Download</button>}
                {hasArtifact && <button type="button" onClick={openArtifact} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white border border-stone-300 hover:bg-stone-50 text-sm font-medium text-stone-900 transition-colors"><ExternalLink className="h-4 w-4" />Open</button>}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-stone-900">
          {execution.title}
        </h2>
        <p className="text-base text-stone-600 leading-relaxed max-w-2xl">
          {execution.request}
        </p>
      </div>

      {/* ACTIVITY STEPS */}
      <div className="space-y-3">
        <button
          onClick={() => setExpandedSteps(!expandedSteps)}
          className="flex items-center gap-2 text-sm font-medium text-stone-700 hover:text-stone-900 transition-colors"
        >
          <ChevronDown className={cn(
            "h-4 w-4 transition-transform",
            expandedSteps && "rotate-180"
          )} />
          <span>{isCompleted ? "Execution details" : "What Synzept is doing"}</span>
        </button>
        
        {expandedSteps && (
          <div className="space-y-2 pl-6">
            {activitySteps.map((step, index) => (
              <div key={index} className="flex items-center gap-3">
                <div className="flex-shrink-0">
                  {step.status === "done" && (
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                  )}
                  {step.status === "current" && (
                    <Loader2 className="h-5 w-5 animate-spin text-stone-900" />
                  )}
                  {step.status === "pending" && (
                    <div className="h-5 w-5 rounded-full border-2 border-stone-300" />
                  )}
                </div>
                <p className={cn(
                  "text-sm",
                  step.status === "pending" ? "text-stone-400" : "text-stone-700"
                )}>
                  {step.title}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* PROGRESS */}
      {!isCompleted && !isError && !isConfirming && (
        <div className="space-y-2">
          <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-stone-900 to-stone-700 transition-all duration-500"
              style={{
                width: `${Math.max(20, Math.min(95, execution.progress))}%`,
              }}
            />
          </div>
          <div className="flex items-center justify-between text-xs text-stone-600">
            <span>Moving this work forward</span>
            <span className="font-medium">{Math.round(execution.progress)}%</span>
          </div>
        </div>
      )}

    </div>
  );
}
