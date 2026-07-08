"use client";

import { useEffect, useState } from "react";
import { AppSidebar, MobileNav } from "@/components/layout/app-sidebar";
import { AppTopbar } from "@/components/layout/app-topbar";
import { CommandPalette } from "@/components/command/command-palette";
import { useRuntimeStream } from "@/hooks/use-runtime-stream";
import { useConversationStore } from "@/stores/conversation-store";
import { useUiStore } from "@/stores/ui-store";
import { useWorkspaceStore } from "@/stores/workspace-store";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [commandOpen, setCommandOpen] = useState(false);
  const mobileNavOpen = useUiStore((s) => s.mobileNavOpen);
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);
  const hydrate = useWorkspaceStore((s) => s.hydrateFromApi);
  const createConversation = useConversationStore((s) => s.createConversation);
  const activeId = useConversationStore((s) => s.activeConversationId);
  const count = useConversationStore((s) => s.conversations.length);

  useRuntimeStream();

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!activeId && count === 0) createConversation();
  }, [activeId, count, createConversation]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen(true);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="flex h-dvh overflow-hidden bg-background">
      <AppSidebar />
      <MobileNav open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar onOpenCommand={() => setCommandOpen(true)} />
        <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
      </div>
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  );
}
