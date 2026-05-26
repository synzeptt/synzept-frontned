"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  FolderKanban,
  StickyNote,
  ListTodo,
  Settings,
} from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { cn } from "@/lib/cn";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Work", icon: MessageSquare },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/notes", label: "Notes", icon: StickyNote },
  { href: "/tasks", label: "Tasks", icon: ListTodo },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden h-screen w-[220px] shrink-0 flex-col border-r border-border bg-surface-raised/50 md:flex">
      <div className="flex items-center gap-2.5 px-5 py-6">
        <BrandLogo imageClassName="h-8" />
      </div>

      <nav className="flex flex-1 flex-col gap-0.5 px-3">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
                active
                  ? "bg-accent-muted font-medium text-accent-foreground"
                  : "text-muted-foreground hover:bg-stone-50 hover:text-stone-800",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      <p className="px-5 py-4 text-[11px] leading-relaxed text-muted">
        Memory · Context · Continuity
      </p>
    </aside>
  );
}
