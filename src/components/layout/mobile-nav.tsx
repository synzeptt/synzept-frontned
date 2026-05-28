"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, FolderKanban, LayoutDashboard, MessageSquare, NotebookText } from "lucide-react";
import { cn } from "@/lib/cn";

const links = [
  { href: "/dashboard", label: "Home", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/chat", label: "AI", icon: MessageSquare },
  { href: "/notes", label: "Notes", icon: NotebookText },
  { href: "/settings", label: "Memory", icon: Brain },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 grid grid-cols-5 border-t border-border bg-surface-raised/95 px-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur-md md:hidden">
      {links.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex min-h-12 flex-col items-center justify-center gap-1 rounded-md px-1 text-[10px] font-medium transition",
              active ? "bg-stone-100 text-stone-950" : "text-muted hover:bg-stone-50 hover:text-stone-800",
            )}
            aria-label={label}
          >
            <Icon className="h-5 w-5" />
            <span className="truncate">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
