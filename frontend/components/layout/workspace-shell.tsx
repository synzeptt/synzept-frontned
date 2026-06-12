"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, CalendarDays, Clock3, CreditCard, FolderKanban, Menu, PanelsTopLeft, Settings, X } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { CopyrightLine } from "@/components/copyright-line";
import { MobileNav } from "@/components/layout/mobile-nav";
import { UsageTracker } from "@/components/analytics/usage-tracker";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar } from "@/components/ui/avatar";
import { UpgradeCta } from "@/components/pro/upgrade-cta";
import { useAuthStore } from "@/stores/auth";
import { api, type NotificationDigest } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useWorkspaceUIStore } from "@frontend/store/workspace-ui";

const navSections = [
  {
    label: "Launch workflow",
    items: [
      { href: "/dashboard", label: "Dashboard", icon: PanelsTopLeft },
      { href: "/projects", label: "Projects", icon: FolderKanban },
      { href: "/daily-brief", label: "Daily Brief", icon: CalendarDays },
      { href: "/timeline", label: "Timeline", icon: Clock3 },
      { href: "/billing", label: "Billing", icon: CreditCard },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { hydrate, isAuthenticated, isLoading, user } = useAuthStore();
  const { sidebarOpen, setSidebarOpen } = useWorkspaceUIStore();
  const [digest, setDigest] = useState<NotificationDigest | null>(null);

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

  useEffect(() => {
    if (!isAuthenticated || isLoading) return;
    api.getNotifications(true).then(setDigest).catch(() => setDigest(null));
  }, [isAuthenticated, isLoading]);

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

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 pb-4">
        {navSections.map((section) => (
          <div key={section.label}>
            <p className="px-3 pb-1.5 text-[10px] font-medium uppercase tracking-[0.14em] text-stone-400">{section.label}</p>
            <div className="space-y-1">
              {section.items.map((item) => {
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
            </div>
          </div>
        ))}
      </nav>

      <div className="m-3 space-y-3">
        {digest && digest.notifications.length > 0 && (
          <div className="rounded-lg border border-border bg-white p-3">
            <div className="flex items-center justify-between gap-2">
              <p className="flex items-center gap-2 text-xs font-medium text-stone-950">
                <Bell className="h-3.5 w-3.5 text-stone-500" />
                Notifications
              </p>
              {digest.unread > 0 && <span className="rounded-md bg-stone-900 px-1.5 py-0.5 text-[10px] text-white">{digest.unread}</span>}
            </div>
            <div className="mt-2 space-y-1">
              {digest.notifications.slice(0, 2).map((item) => {
                const href = typeof item.metadata.href === "string" ? item.metadata.href : "/dashboard";
                return (
                  <Link
                    key={item.id}
                    href={href}
                    onClick={() => {
                      setSidebarOpen(false);
                      void api.markNotificationRead(item.id).then(setDigest).catch(() => null);
                    }}
                    className="block rounded-md bg-stone-50 px-2 py-2 text-xs leading-5 text-stone-700 hover:bg-stone-100"
                  >
                    <span className="line-clamp-1 font-medium text-stone-950">{item.title}</span>
                    <span className="line-clamp-2 text-stone-500">{item.message}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        )}
        <div className="rounded-lg border border-border bg-stone-50 p-3">
          <p className="text-xs font-medium text-stone-950">Current Plan: {user?.is_pro ? "Pro" : "Free"}</p>
          <p className="mt-1 text-[11px] leading-4 text-stone-500">{user?.is_pro ? "Pro features are unlocked." : "Upgrade for ₹399/month."}</p>
          {!user?.is_pro && <UpgradeCta compact className="mt-3 w-full" />}
        </div>
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
    </div>
  );
}
