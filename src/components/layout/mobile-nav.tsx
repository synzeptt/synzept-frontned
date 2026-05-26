"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, MessageSquare, FolderKanban, ListTodo } from "lucide-react";
import { cn } from "@/lib/cn";

const links = [
  { href: "/dashboard", icon: LayoutDashboard },
  { href: "/chat", icon: MessageSquare },
  { href: "/projects", icon: FolderKanban },
  { href: "/tasks", icon: ListTodo },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-border bg-surface-raised/95 px-2 py-2 backdrop-blur-md md:hidden">
      {links.map(({ href, icon: Icon }) => {
        const active = pathname === href || pathname.startsWith(`${href}/`);
        return (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex flex-1 items-center justify-center rounded-xl py-2.5 transition",
              active ? "text-accent" : "text-muted",
            )}
          >
            <Icon className="h-5 w-5" />
          </Link>
        );
      })}
    </nav>
  );
}
