import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export function RecoveryBanner({
  message,
  onRetry,
  className,
}: {
  message: string | null;
  onRetry?: () => void;
  className?: string;
}) {
  if (!message) return null;

  return (
    <div className={cn("flex flex-col gap-3 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 sm:flex-row sm:items-center sm:justify-between", className)}>
      <p className="flex items-start gap-2 leading-6">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
        <span>{message}</span>
      </p>
      {onRetry && (
        <Button type="button" variant="outline" size="sm" onClick={onRetry} className="bg-white">
          <RotateCcw className="mr-1.5 h-4 w-4" />
          Retry
        </Button>
      )}
    </div>
  );
}
