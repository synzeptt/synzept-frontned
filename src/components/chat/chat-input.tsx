"use client";

import { FormEvent, KeyboardEvent, useLayoutEffect, useRef } from "react";
import { ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

type Props = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
};

export function ChatInput({ value, onChange, onSubmit, disabled, placeholder }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) onSubmit();
    }
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (value.trim() && !disabled) onSubmit();
  };

  return (
    <form onSubmit={submit} className="border-t border-border bg-white/85 p-4 backdrop-blur-md">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <textarea
          ref={ref}
          rows={1}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKey}
          disabled={disabled}
          placeholder={placeholder ?? "Continue your work, ask for clarity, or share context..."}
          className={cn(
            "max-h-40 min-h-[48px] flex-1 resize-none rounded-lg border border-border bg-white px-4 py-3 text-[15px] text-stone-900 shadow-soft outline-none transition",
            "placeholder:text-muted focus:border-accent/40 focus:ring-2 focus:ring-accent/10",
            disabled && "opacity-60",
          )}
        />
        <Button type="submit" disabled={disabled || !value.trim()} size="lg" className="h-12 w-12 shrink-0 p-0">
          <ArrowUp className="h-5 w-5" />
        </Button>
      </div>
      <p className="mx-auto mt-2 max-w-3xl text-center text-[11px] text-muted">
        Enter to send - Shift+Enter for new line
      </p>
    </form>
  );
}
