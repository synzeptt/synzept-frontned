"use client";

import { RefObject, useCallback, useEffect } from "react";

export function useAutoScroll<T extends HTMLElement>(
  ref: RefObject<T | null>,
  deps: unknown[],
  enabled = true,
  smooth = true,
) {
  const scrollToBottom = useCallback(
    (useSmooth = smooth) => {
      const el = ref.current;
      if (!el || !enabled) return;
      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      if (distanceFromBottom > 220 && useSmooth) return;
      el.scrollTo({ top: el.scrollHeight, behavior: useSmooth ? "smooth" : "auto" });
    },
    [enabled, ref, smooth],
  );

  useEffect(() => {
    scrollToBottom();
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  return scrollToBottom;
}
