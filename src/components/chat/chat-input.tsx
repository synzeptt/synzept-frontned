"use client";

import { DragEvent, FormEvent, KeyboardEvent, useLayoutEffect, useRef, useState } from "react";
import { ArrowUp, File, Mic, Paperclip, X } from "lucide-react";
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

export function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder,
  attachments,
  onAttachFiles,
  onRemoveAttachment,
  uploading,
  uploadProgress,
  uploadFileName,
}: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [dragging, setDragging] = useState(false);
  const canSubmit = Boolean(value.trim() || attachments?.length);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "0px";
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [value]);

  const handleDragOver = (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (event.dataTransfer.types.includes("Files")) setDragging(true);
  };

  const handleDrop = (event: DragEvent<HTMLFormElement>) => {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files.length) onAttachFiles?.(event.dataTransfer.files);
  };

  const handleAttach = (event: FormEvent<HTMLInputElement>) => {
    if (!event.currentTarget.files) return;
    onAttachFiles?.(event.currentTarget.files);
    event.currentTarget.value = "";
  };

  const handleKey = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSubmit && !disabled) onSubmit();
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (canSubmit && !disabled) onSubmit();
  };

  return (
    <form
      onSubmit={submit}
      onDragEnter={handleDragOver}
      onDragOver={handleDragOver}
      onDragLeave={(event) => {
        event.preventDefault();
        setDragging(false);
      }}
      onDrop={handleDrop}
      className="fixed bottom-0 left-0 right-0 z-30 border-t border-stone-200/80 bg-[#f8f7f3]/92 px-3 pb-3 pt-3 backdrop-blur-xl md:left-[320px] md:px-6"
    >
      <div className="mx-auto max-w-3xl">
        <div className="relative rounded-2xl border border-stone-200 bg-white shadow-[0_18px_50px_rgba(28,25,23,0.10)]">
          {dragging ? (
            <div className="absolute inset-2 z-10 grid place-items-center rounded-xl border border-dashed border-stone-400 bg-white/90 text-sm font-medium text-stone-700">
              Drop images, PDFs, documents, videos, or other files
            </div>
          ) : null}

          {attachments && attachments.length > 0 ? (
            <div className="flex gap-2 overflow-x-auto px-3 pt-3">
              {attachments.map((attachment) => (
                <div key={attachment.id} className="flex max-w-[220px] shrink-0 items-center gap-2 rounded-lg border border-stone-200 bg-stone-50 px-2.5 py-2 text-sm text-stone-700">
                  <File className="h-4 w-4 shrink-0 text-stone-500" />
                  <span className="min-w-0 flex-1 truncate">{attachment.filename}</span>
                  <button type="button" onClick={() => onRemoveAttachment?.(attachment.id)} className="grid h-5 w-5 place-items-center rounded-md text-stone-500 hover:bg-stone-200" aria-label={`Remove ${attachment.filename}`}>
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>
          ) : null}

          {uploading ? (
            <div className="mx-3 mt-3 rounded-lg bg-stone-100 px-3 py-2 text-sm text-stone-600">
              {uploadFileName ? `${uploadFileName} - ` : "Uploading - "}
              {uploadProgress !== null ? `${uploadProgress}%` : "Starting..."}
            </div>
          ) : null}

          <div className="flex items-end gap-2 p-2">
            <label className="grid h-10 w-10 shrink-0 cursor-pointer place-items-center rounded-lg text-stone-500 transition hover:bg-stone-100 hover:text-stone-950" title="Attach files">
              <Paperclip className="h-5 w-5" />
              <input
                type="file"
                multiple
                accept="image/*,application/pdf,.doc,.docx,.txt,.md,.csv,.xls,.xlsx,.ppt,.pptx,video/*,*"
                className="hidden"
                onChange={handleAttach}
              />
            </label>
            <textarea
              ref={ref}
              rows={1}
              value={value}
              onChange={(event) => onChange(event.target.value)}
              onKeyDown={handleKey}
              disabled={disabled}
              placeholder={placeholder ?? "Message Synzept..."}
              className={cn(
                "max-h-44 min-h-10 flex-1 resize-none bg-transparent px-1 py-2.5 text-[15px] leading-6 text-stone-950 outline-none placeholder:text-stone-400",
                disabled && "opacity-60",
              )}
            />
            <button type="button" disabled className="grid h-10 w-10 shrink-0 place-items-center rounded-lg text-stone-400" title="Voice input coming soon" aria-label="Voice input coming soon">
              <Mic className="h-5 w-5" />
            </button>
            <button
              type="submit"
              disabled={disabled || !canSubmit}
              className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-stone-950 text-white transition hover:bg-stone-800 disabled:bg-stone-200 disabled:text-stone-400"
              aria-label="Send message"
            >
              <ArrowUp className="h-5 w-5" />
            </button>
          </div>
        </div>
        <p className="mt-2 text-center text-[11px] text-stone-500">Synzept can make mistakes. Please verify important information.</p>
      </div>
    </form>
  );
}
