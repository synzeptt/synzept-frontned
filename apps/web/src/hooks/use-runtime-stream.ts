"use client";

import { useEffect } from "react";
import { useWorkspaceStore } from "@/stores/workspace-store";

export function useRuntimeStream() {
  const ingest = useWorkspaceStore((s) => s.ingestRuntimeEvent);

  useEffect(() => {
    const events = new EventSource("/api/workspace/activity/stream");
    const handler = (event: MessageEvent) => {
      try {
        ingest(JSON.parse(event.data));
      } catch {
        /* heartbeat */
      }
    };
    events.onmessage = handler;
    ["chat.completed", "execution.updated", "workflow.updated", "document.indexed"].forEach((type) => {
      events.addEventListener(type, handler as EventListener);
    });
    return () => events.close();
  }, [ingest]);
}
