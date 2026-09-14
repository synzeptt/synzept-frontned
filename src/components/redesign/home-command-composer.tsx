"use client";

import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";

interface HomeCommandComposerProps {
  onExecuting?: (executionId: string) => void;
  value?: string;
  onValueChange?: (value: string) => void;
}

export function HomeCommandComposer({ onExecuting, value, onValueChange }: HomeCommandComposerProps) {
  const [localInput, setLocalInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = value ?? localInput;
  const setInput = (nextValue: string) => {
    setLocalInput(nextValue);
    onValueChange?.(nextValue);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isSubmitting) return;

    setError(null);
    setIsSubmitting(true);

    try {
      const execution = await api.createActionExecution({
        request: input.trim(),
      });
      setInput("");
      onExecuting?.(execution.id);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not start the task. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-3" aria-label="Ask Synzept">
      <div className={cn(
        "border border-border/20 bg-surface-raised transition-colors duration-200",
        isSubmitting ? "border-border/25 bg-surface-overlay" : "hover:border-border/25"
      )}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tell Synzept what you want done..."
          aria-label="What do you want me to do?"
          className={cn(
            "w-full resize-none bg-transparent px-5 py-4 text-base text-stone-900 outline-none",
            "placeholder:text-muted focus:placeholder:text-muted-foreground",
            "min-h-[96px]",
            "disabled:opacity-75"
          )}
          disabled={isSubmitting}
          autoFocus
        />
        <div className="flex flex-col gap-3 border-t border-border/10 px-5 py-4">
          {error && (
            <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 rounded-lg p-3">
              <div className="flex-shrink-0 mt-0.5">
                <span className="text-red-500">⚠</span>
              </div>
              <p>{error}</p>
            </div>
          )}
          <div className="flex items-center justify-between">
            {isSubmitting && (
              <div className="flex items-center gap-2 text-sm text-stone-600">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Creating your Work item...</span>
              </div>
            )}
            {!isSubmitting && (
              <p className="text-xs text-stone-500">
                {input.trim().split(/\s+/).length} words
              </p>
            )}
            <Button
              type="submit"
              disabled={!input.trim() || isSubmitting}
              loading={isSubmitting}
              className={cn("px-4", !input.trim() && "bg-surface-overlay text-muted")}
            >
              <span>{isSubmitting ? "Starting" : "Do it"}</span>
              {!isSubmitting && <ArrowRight className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </div>
    </form>
  );
}
