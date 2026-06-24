"use client";

import { FormEvent, DragEvent, KeyboardEvent, useLayoutEffect, useRef, useState } from "react";
import { ArrowUp, Paperclip, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export type AttachmentMetadata = {
  id: string;
  filename: string;
  url: string;
  size: number;
  content_type?: string | null;
};

type Props = {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
  attachments?: AttachmentMetadata[];
  onAttachFiles?: (files: FileList) => void;
  onRemoveAttachment?: (attachmentId: string) => void;
  uploading?: boolean;
  uploadProgress?: number | null;
  uploadFileName?: string | null;
};

export function ChatInput({ value, onChange, onSubmit, disabled, placeholder, attachments, onAttachFiles, onRemoveAttachment, uploading, uploadProgress, uploadFileName }: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [dragging, setDragging] = useState(false);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const handleDragOver = (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (event.dataTransfer.types.includes("Files")) {
      setDragging(true);
    }
  };

  const handleDragLeave = (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
    setDragging(false);
  };

  const handleDrop = (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files) {
      onAttachFiles?.(event.dataTransfer.files);
    }
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if ((value.trim() || (attachments && attachments.length > 0)) && !disabled) onSubmit();
    }
  };

  const handleAttach = (event: FormEvent<HTMLInputElement>) => {
    if (!event.currentTarget.files) return;
    onAttachFiles?.(event.currentTarget.files);
    event.currentTarget.value = "";
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if ((value.trim() || (attachments && attachments.length > 0)) && !disabled) onSubmit();
  };

  return (
    <form
      onSubmit={submit}
      onDragOver={handleDragOver}
      onDragEnter={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className="relative border-t border-border bg-white/85 p-4 backdrop-blur-md"
    >
      {dragging ? (
        <div className="pointer-events-none absolute inset-x-4 top-4 z-10 flex h-[calc(100%-2rem)] items-center justify-center rounded-3xl border-2 border-dashed border-accent/70 bg-white/80 text-sm font-semibold text-accent shadow-soft">
          Drop files to attach
        </div>
      ) : null}
      <div className="mx-auto flex max-w-3xl flex-col gap-3">
        {attachments && attachments.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {attachments.map((attachment) => (
              <div key={attachment.id} className="inline-flex items-center gap-2 rounded-full bg-stone-100 px-3 py-2 text-sm text-stone-700 shadow-sm">
                <span className="max-w-[14rem] truncate">{attachment.filename}</span>
                <button
                  type="button"
                  onClick={() => onRemoveAttachment?.(attachment.id)}
                  className="rounded-full p-1 text-stone-500 transition hover:bg-stone-200 hover:text-stone-900"
                  aria-label={`Remove attachment ${attachment.filename}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
        {uploading ? (
          <div className="rounded-2xl border border-accent/25 bg-accent/10 px-3 py-2 text-sm text-accent">
            {uploadFileName ? `${uploadFileName} — ` : "Uploading attachment"}
            {uploadProgress !== null ? `${uploadProgress}%` : "Starting..."}
          </div>
        ) : null}
        <div className="flex items-end gap-2">
          <label className="inline-flex h-12 items-center gap-2 rounded-lg border border-border bg-white px-4 py-3 text-sm text-stone-700 shadow-soft transition hover:border-stone-300 hover:bg-stone-50">
            <Paperclip className="h-4 w-4" />
            <span>Attach</span>
            <input type="file" multiple className="hidden" onChange={handleAttach} />
          </label>
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
          <Button type="submit" disabled={disabled || (!value.trim() && !(attachments && attachments.length > 0))} size="lg" className="h-12 w-12 shrink-0 p-0">
            <ArrowUp className="h-5 w-5" />
          </Button>
        </div>
        <p className="mx-auto text-center text-[11px] text-muted">
          Enter to send - Shift+Enter for new line
        </p>
      </div>
    </form>
  );
}
