"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  FileText,
  FolderKanban,
  LayoutDashboard,
  MessageSquare,
  PanelLeft,
  PanelLeftClose,
  Settings,
  Sparkles,
  Workflow
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui-store";

const NAV = [
  { href: "/app", label: "Dashboard", icon: LayoutDashboard },
  { href: "/app/chat", label: "Chat", icon: MessageSquare },
  { href: "/app/projects", label: "Projects", icon: FolderKanban },
  { href: "/app/workflows", label: "Workflows", icon: Workflow },
  { href: "/app/documents", label: "Documents", icon: FileText },
  { href: "/app/settings", label: "Settings", icon: Settings }
] as const;

export function AppSidebar() {
  const pathname = usePathname();
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggle = useUiStore((s) => s.toggleSidebar);

  return (
    <motion.aside
      animate={{ width: collapsed ? 72 : 256 }}
      className="hidden h-full shrink-0 border-r border-border/60 bg-card/50 backdrop-blur-xl lg:flex lg:flex-col"
    >
      <div className="flex h-full flex-col p-3">
        <div className={cn("mb-6 flex items-center gap-2", collapsed && "justify-center")}>
          <div className="grid size-9 place-items-center rounded-xl bg-primary text-primary-foreground shadow-glow">
            <Sparkles size={16} />
          </div>
          {!collapsed ? (
            <div>
              <div className="text-sm font-semibold">Synzept</div>
              <div className="text-[11px] text-muted-foreground">AI workspace</div>
            </div>
          ) : null}
        </div>

        <nav className="flex-1 space-y-1">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || (item.href !== "/app" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? item.label : undefined}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm transition-all",
                  active ? "bg-primary/12 text-primary" : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                  collapsed && "justify-center"
                )}
              >
                <Icon size={18} />
                {!collapsed ? item.label : null}
              </Link>
            );
          })}
        </nav>

        <button
          type="button"
          onClick={toggle}
          className="mt-3 flex items-center justify-center rounded-lg border border-border p-2 text-muted-foreground hover:bg-secondary"
        >
          {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
        </button>
      </div>
    </motion.aside>
  );
}

export function MobileNav({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();

  return (
    <AnimatePresence>
      {open ? (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/60 lg:hidden"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: -280 }}
            animate={{ x: 0 }}
            exit={{ x: -280 }}
            className="fixed inset-y-0 left-0 z-50 w-72 border-r border-border bg-card p-4 lg:hidden"
          >
            <p className="mb-4 text-sm font-semibold">Menu</p>
            <nav className="space-y-1">
              {NAV.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onClose}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm",
                      active ? "bg-primary/12 text-primary" : "text-muted-foreground"
                    )}
                  >
                    <Icon size={18} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );
}
