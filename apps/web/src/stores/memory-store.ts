"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { createId } from "@/lib/id";
import type { MemoryRecord, MemorySnapshot } from "@/types/chat";

type MemoryState = {
  shortTerm: string[];
  longTerm: MemoryRecord[];
};

type MemoryActions = {
  rememberShortTerm: (content: string) => void;
  rememberLongTerm: (content: string, tags?: string[]) => void;
  snapshot: () => MemorySnapshot;
};

export const useMemoryStore = create<MemoryState & MemoryActions>()(
  persist(
    (set, get) => ({
      shortTerm: [],
      longTerm: [],
      rememberShortTerm: (content) =>
        set((s) => ({ shortTerm: [content, ...s.shortTerm].slice(0, 12) })),
      rememberLongTerm: (content, tags = []) =>
        set((s) => ({
          longTerm: [
            { id: createId("mem"), content, createdAt: new Date().toISOString(), tags },
            ...s.longTerm
          ].slice(0, 50)
        })),
      snapshot: () => {
        const s = get();
        return { shortTerm: s.shortTerm, longTerm: s.longTerm };
      }
    }),
    { name: "synzept-web-memory" }
  )
);
