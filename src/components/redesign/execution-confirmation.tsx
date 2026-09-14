"use client";

import { AlertCircle, CheckCircle2, Mail, FileText, Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

interface ConfirmationDetail {
  label: string;
  value: string;
}

interface ExecutionConfirmationProps {
  description?: string;
  action: string; // "send_email", "edit_document", "post_message", etc.
  details: ConfirmationDetail[];
  isPending?: boolean;
  onApprove: () => void;
  onReject: () => void;
}

function getActionIcon(action: string) {
  switch (action) {
    case "send_email":
      return <Mail className="h-5 w-5 text-blue-600" />;
    case "create_document":
    case "edit_document":
      return <FileText className="h-5 w-5 text-orange-600" />;
    default:
      return <CheckCircle2 className="h-5 w-5 text-stone-600" />;
  }
}

function getActionLabel(action: string): string {
  const labels: Record<string, string> = {
    send_email: "Email ready to send",
    create_document: "Document ready to create",
    edit_document: "Document ready to update",
    post_message: "Message ready to post",
    book_reservation: "Ready to book",
    schedule_meeting: "Ready to schedule",
  };
  return labels[action] || "Ready to proceed";
}

export function ExecutionConfirmation({
  description,
  action,
  details,
  isPending = false,
  onApprove,
  onReject,
}: ExecutionConfirmationProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          {getActionIcon(action)}
          <div>
            <h3 className="text-lg font-semibold text-stone-900">
              {getActionLabel(action)}
            </h3>
            {description && (
              <p className="mt-1 text-sm text-stone-600">{description}</p>
            )}
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="rounded-xl border border-stone-200 bg-stone-50 overflow-hidden">
        <div className="space-y-1 divide-y divide-stone-200">
          {details.map((detail, index) => (
            <div key={index} className="p-4 last:pb-4 first:pt-4">
              <p className="text-xs font-medium text-stone-600 uppercase tracking-wide">
                {detail.label}
              </p>
              <p className="mt-2 text-sm font-medium text-stone-900 break-words">
                {detail.value}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Approval message */}
      <div className="flex items-start gap-2 px-4 py-3 rounded-lg bg-blue-50 border border-blue-200">
        <AlertCircle className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <p className="text-sm text-blue-900">
          This action cannot be undone. Please review the details above carefully.
        </p>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <button
          onClick={onApprove}
          disabled={isPending}
          className={cn(
            "flex-1 px-4 py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2",
            isPending
              ? "bg-green-600 text-white cursor-wait"
              : "bg-green-600 text-white hover:bg-green-700 active:bg-green-800"
          )}
        >
          {isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Processing...</span>
            </>
          ) : (
            <>
              <CheckCircle2 className="h-4 w-4" />
              <span>Approve & Continue</span>
            </>
          )}
        </button>
        <button
          onClick={onReject}
          disabled={isPending}
          className={cn(
            "flex-1 px-4 py-3 rounded-lg font-medium transition-all",
            isPending
              ? "bg-stone-100 text-stone-400 cursor-not-allowed"
              : "bg-stone-100 text-stone-900 hover:bg-stone-200 active:bg-stone-300"
          )}
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
