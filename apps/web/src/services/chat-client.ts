import type { ChatRequest } from "@/types/chat";

export type StreamOptions = {
  onChunk?: (chunk: string) => void;
  onStart?: () => void;
  onComplete?: () => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
};

export async function streamAssistantResponse(payload: ChatRequest, options: StreamOptions = {}): Promise<void> {
  const { onStart, onChunk, onComplete, onError, signal } = options;

  try {
    onStart?.();

    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal,
      credentials: "include"
    });

    if (!response.ok || !response.body) {
      const detail = await response.text();
      const error = new Error(detail || "Synzept could not start a response.");
      onError?.(error);
      throw error;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      if (signal?.aborted) {
        await reader.cancel();
        throw new DOMException("Request cancelled", "AbortError");
      }
      const { done, value } = await reader.read();
      if (done) break;
      onChunk?.(decoder.decode(value, { stream: true }));
    }

    onComplete?.();
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      onError?.(new Error("Request was cancelled"));
    } else {
      const err = error instanceof Error ? error : new Error("Unknown error");
      onError?.(err);
      throw err;
    }
  }
}
