"use client";

import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Brain, FolderKanban, Menu, MessageSquare, PanelsTopLeft, X } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { CopyrightLine } from "@/components/copyright-line";
import { FeedbackButton } from "@/components/feedback/feedback-button";
import { MobileNav } from "@/components/layout/mobile-nav";
import { UsageTracker } from "@/components/analytics/usage-tracker";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar } from "@/components/ui/avatar";
import { useAuthStore } from "@/stores/auth";
import { cn } from "@/lib/cn";
import { useWorkspaceUIStore } from "@frontend/store/workspace-ui";

const nav = [
  { href: "/dashboard", label: "Workspace", icon: PanelsTopLeft },
  { href: "/projects", label: "Projects", icon: FolderKanban },
  { href: "/settings", label: "Memory", icon: Brain },
  { href: "/chat", label: "AI", icon: MessageSquare },
];

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { hydrate, isAuthenticated, isLoading, user } = useAuthStore();
  const { sidebarOpen, setSidebarOpen } = useWorkspaceUIStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated && pathname !== "/login") {
      router.replace("/login");
      return;
    }
    if (isAuthenticated && user && user.onboarding_state !== "complete" && !pathname.startsWith("/onboarding")) {
      router.replace("/onboarding");
    }
  }, [isAuthenticated, isLoading, pathname, router, user]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-surface">
        <div className="w-56 space-y-3">
          <Skeleton className="h-8 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const sidebar = (
    <aside className="flex h-full w-[264px] shrink-0 flex-col border-r border-border bg-white">
      <div className="flex h-16 items-center justify-between px-4">
        <Link href="/dashboard" className="flex items-center" aria-label="Synzept dashboard">
          <BrandLogo imageClassName="h-8" />
        </Link>
        <button
          type="button"
          className="grid h-9 w-9 place-items-center rounded-md text-stone-500 hover:bg-stone-100 md:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        {nav.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setSidebarOpen(false)}
              className={cn(
                "flex h-10 items-center gap-3 rounded-md px-3 text-sm transition duration-150",
                active ? "bg-stone-100 text-stone-950 shadow-[inset_0_0_0_1px_rgba(32,31,28,0.04)]" : "text-stone-500 hover:bg-stone-50 hover:text-stone-900",
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="m-3 space-y-3">
        <Link
          href="/settings"
          onClick={() => setSidebarOpen(false)}
          className={cn(
            "flex items-center gap-3 rounded-lg border border-transparent p-2.5 transition",
            pathname.startsWith("/settings")
              ? "border-border bg-stone-100"
              : "hover:border-border hover:bg-stone-50",
          )}
          aria-label="Open account settings"
        >
          <Avatar name={user?.display_name} email={user?.email} src={user?.avatar_url} size="sm" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-stone-900">{user?.display_name || "Workspace"}</p>
            <p className="truncate text-xs text-stone-500">{user?.email}</p>
          </div>
        </Link>
        <CopyrightLine className="px-2 text-[10px]" />
      </div>
    </aside>
  );

  return (
    <div className="min-h-screen bg-surface text-stone-900">
      <div className="flex h-[100dvh] overflow-hidden">
        <div className="hidden md:block">{sidebar}</div>
        <AnimatePresence>
          {sidebarOpen && (
            <motion.div
              className="fixed inset-0 z-50 flex bg-stone-900/20 md:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <motion.div initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} transition={{ duration: 0.16 }}>
                {sidebar}
              </motion.div>
              <button className="flex-1" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-14 shrink-0 items-center border-b border-border bg-white px-4 md:hidden">
            <button
              type="button"
              className="grid h-9 w-9 place-items-center rounded-md text-stone-600 hover:bg-stone-100"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
            <BrandLogo className="ml-2" imageClassName="h-7" />
          </header>
          <main className="min-h-0 flex-1 overflow-hidden pb-[74px] md:pb-0">{children}</main>
        </div>
      </div>
      <UsageTracker />
      <MobileNav />
      <FeedbackButton />
    </div>
  );
}
