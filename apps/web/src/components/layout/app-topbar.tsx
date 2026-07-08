"use client";

import { Command, Menu, Search } from "lucide-react";
import { usePathname } from "next/navigation";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/stores/ui-store";

const TITLES: Record<string, string> = {
  "/app": "Dashboard",
  "/app/chat": "AI Chat",
  "/app/projects": "Projects",
  "/app/workflows": "Workflows",
  "/app/documents": "Documents",
  "/app/settings": "Settings"
};

export function AppTopbar({ onOpenCommand }: { onOpenCommand: () => void }) {
  const pathname = usePathname();
  const setMobileNavOpen = useUiStore((s) => s.setMobileNavOpen);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-border/60 bg-background/80 px-4 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={() => setMobileNavOpen(true)}>
          <Menu size={18} />
        </Button>
        <div>
          <h1 className="text-sm font-semibold">{TITLES[pathname] ?? "Workspace"}</h1>
          <p className="hidden text-xs text-muted-foreground sm:block">Connected to Synzept API</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="sm" className="hidden sm:inline-flex" onClick={onOpenCommand}>
          <Command size={14} />
          <span className="text-muted-foreground">⌘K</span>
        </Button>
        <Button variant="ghost" size="icon" onClick={onOpenCommand} aria-label="Search">
          <Search size={16} />
        </Button>
        <span className="hidden rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs text-emerald-300 sm:inline">
          Live
        </span>
      </div>
    </header>
  );
}
