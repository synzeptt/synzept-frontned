"use client";

import { useEffect, useRef } from "react";

export function useAutoScroll(deps: string) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: "smooth" });
  }, [deps]);
  return ref;
}
