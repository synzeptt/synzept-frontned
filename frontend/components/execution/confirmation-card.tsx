"use client";

import { AlertCircle, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { ChatConfirmation } from "@/lib/api";
import { Button } from "@/components/ui/button";

export interface ConfirmationCardProps {
  confirmation: ChatConfirmation | null;
  status?: "pending" | "confirmed" | "executed" | "rejected" | "cancelled" | "expired" | "failed";
  onConfirm?: () => Promise<void> | void;
  onReject?: () => Promise<void> | void;
  isLoading?: boolean;
  message?: string | null;
}

/**
 * ConfirmationCard - Shows confirmation requirement and handles approval/rejection
 *
 * Displays:
 * - What Synzept wants to do (summary)
 * - Risk level (confirmation required)
 * - Tool being used (tool_name)
 * - Parameters (tool_arguments - but sanitized)
 * - Decision buttons
 * - Status after decision
 */
export function ConfirmationCard({ confirmation, status = "pending", onConfirm, onReject, isLoading = false, message }: ConfirmationCardProps) {
  if (!confirmation) return null;

  const isPending = status === "pending";
  const isConfirmed = status === "confirmed" || status === "executed";
  const isRejected = status === "rejected" || status === "cancelled";
  const isProcessing = isLoading;

  // Get human-readable description of what's being confirmed
  const getSummary = () => {
    if (confirmation.human_readable_summary) return confirmation.human_readable_summary;
    if (confirmation.summary) return confirmation.summary;
    return `Synzept wants to use ${confirmation.tool_name || "an external tool"}.`;
  };

  const getRiskMessage = () => {
    if (confirmation.risk_level === "confirmation_required") {
      return "This action requires your approval before it runs.";
    }
    return "";
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-amber-200 bg-gradient-to-br from-amber-50 to-yellow-50 shadow-sm overflow-hidden"
    >
      {/* Header */}
      <div className="bg-amber-100/30 p-4 sm:p-5 border-b border-amber-200">
        <div className="flex items-start gap-3 sm:gap-4">
          <AlertCircle className="h-5 w-5 text-amber-700 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-amber-900">Confirmation required</p>
            <p className="text-sm text-amber-800 mt-1">{getRiskMessage()}</p>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 sm:p-5 space-y-4">
        {/* What it wants to do */}
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-stone-600">What Synzept wants to do</p>
          <p className="text-sm text-stone-900 leading-relaxed">{getSummary()}</p>
        </div>

        {/* Tool information */}
        {confirmation.tool_name && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-stone-600">Tool</p>
            <p className="text-sm font-mono text-stone-700 bg-stone-50 rounded px-2 py-1">{confirmation.tool_name}</p>
          </div>
        )}

        {/* Status message */}
        {message && (
          <div className={`rounded-lg p-3 ${isConfirmed ? "bg-green-50 border border-green-200" : isRejected ? "bg-red-50 border border-red-200" : "bg-blue-50 border border-blue-200"}`}>
            <p className={`text-sm ${isConfirmed ? "text-green-900" : isRejected ? "text-red-900" : "text-blue-900"}`}>{message}</p>
          </div>
        )}

        {/* Show execution status after decision */}
        {!isPending && (
          <div className="flex items-center gap-2">
            {isConfirmed && (
              <>
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                <p className="text-sm text-green-900">Confirmed. Synzept is continuing the action.</p>
              </>
            )}
            {isRejected && (
              <>
                <XCircle className="h-4 w-4 text-red-600" />
                <p className="text-sm text-red-900">Cancelled. The action will not run.</p>
              </>
            )}
          </div>
        )}
      </div>

      {/* Actions - Only show if pending and no message yet */}
      {isPending && !message && (
        <div className="border-t border-amber-200 bg-amber-50/50 px-4 sm:px-5 py-4 flex flex-col sm:flex-row gap-2 sm:gap-3 sm:justify-end">
          <Button
            variant="outline"
            size="sm"
            onClick={onReject}
            disabled={isProcessing}
            className="border-stone-300 text-stone-700 hover:bg-white hover:border-stone-400"
          >
            {isProcessing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Reject
          </Button>
          <Button
            size="sm"
            onClick={onConfirm}
            disabled={isProcessing}
            className="bg-amber-600 hover:bg-amber-700 text-white"
          >
            {isProcessing ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Approve
          </Button>
        </div>
      )}
    </motion.div>
  );
}
