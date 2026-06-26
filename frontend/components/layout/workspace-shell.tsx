"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { Bell, BookOpen, CalendarDays, ChevronDown, ChevronUp, Home, Menu, MessageSquare, Settings, X } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { CopyrightLine } from "@/components/copyright-line";
import { MobileNav } from "@/components/layout/mobile-nav";
import { UsageTracker } from "@/components/analytics/usage-tracker";
import { FeedbackButton } from "@/components/feedback/feedback-button";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar } from "@/components/ui/avatar";
import { UpgradeCta } from "@/components/pro/upgrade-cta";
import { useAuthStore } from "@/stores/auth";
import { api, type NotificationDigest } from "@/lib/api";
import { cn } from "@/lib/cn";
import { useWorkspaceUIStore } from "@frontend/store/workspace-ui";

const navItems = [
  { href: "/dashboard", label: "Home", icon: Home },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/memory", label: "Memory", icon: BookOpen },
  { href: "/daily-brief", label: "Daily Brief", icon: CalendarDays },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { hydrate, isAuthenticated, isLoading, user } = useAuthStore();
  const { sidebarOpen, setSidebarOpen } = useWorkspaceUIStore();
  const [digest, setDigest] = useState<NotificationDigest | null>(null);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [dismissedNotifications, setDismissedNotifications] = useState<Set<string>>(new Set());

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

  if (pathname === "/chat") {
    return (
      <div className="h-[100dvh] overflow-hidden bg-surface text-stone-900">
        {children}
        <UsageTracker />
      </div>
    );
  }

  const sidebar = (
    <aside className="flex h-full w-[264px] shrink-0 flex-col border-r border-border bg-white">
      <div className="flex h-16 items-center justify-between px-4">
        <Link href="/dashboard" className="flex items-center" aria-label="Synzept Home">
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

      <nav className="flex-1 overflow-y-auto px-3 pb-4">
        <div className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  "flex h-11 items-center gap-3 rounded-md px-3 text-sm transition duration-150",
                  active ? "bg-stone-100 text-stone-950 shadow-[inset_0_0_0_1px_rgba(32,31,28,0.04)]" : "text-stone-500 hover:bg-stone-50 hover:text-stone-900",
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>

      <div className="m-3 space-y-3">
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
      <NotificationTray
        digest={digest}
        open={notificationsOpen}
        dismissed={dismissedNotifications}
        onToggle={() => setNotificationsOpen((value) => !value)}
        onDismiss={(id) => {
          setDismissedNotifications((current) => new Set([...current, id]));
          void api.markNotificationRead(id).then(setDigest).catch(() => null);
        }}
        onRead={(id) => void api.markNotificationRead(id).then(setDigest).catch(() => null)}
      />
      <FeedbackButton />
      <UsageTracker />
      <MobileNav />
    </div>
  );
}

function NotificationTray({
  digest,
  open,
  dismissed,
  onToggle,
  onDismiss,
  onRead,
}: {
  digest: NotificationDigest | null;
  open: boolean;
  dismissed: Set<string>;
  onToggle: () => void;
  onDismiss: (id: string) => void;
  onRead: (id: string) => void;
}) {
  const items = (digest?.notifications || []).filter((item) => !dismissed.has(item.id)).slice(0, 4);
  const unread = items.filter((item) => !item.readAt).length;
  if (!items.length) return null;

  return (
    <div className="fixed right-3 top-16 z-30 w-[min(320px,calc(100vw-1.5rem))] md:right-4 md:top-4">
      <div className="rounded-lg border border-border bg-white/95 shadow-soft backdrop-blur">
        <button
          type="button"
          onClick={onToggle}
          className="flex h-10 w-full items-center justify-between gap-3 px-3 text-left text-sm"
          aria-expanded={open}
        >
          <span className="flex min-w-0 items-center gap-2 font-medium text-stone-950">
            <Bell className="h-4 w-4 text-stone-500" />
            <span className="truncate">Notifications</span>
          </span>
          <span className="flex items-center gap-2">
            {unread > 0 && <span className="rounded-md bg-stone-900 px-1.5 py-0.5 text-[10px] text-white">{unread}</span>}
            {open ? <ChevronUp className="h-4 w-4 text-stone-500" /> : <ChevronDown className="h-4 w-4 text-stone-500" />}
          </span>
        </button>

        {open && (
          <div className="max-h-[45vh] space-y-1 overflow-y-auto border-t border-border p-2">
            {items.map((item) => {
              const href = typeof item.metadata.href === "string" ? item.metadata.href : "/agent";
              return (
                <div key={item.id} className="group flex gap-2 rounded-md bg-stone-50 p-2 text-xs leading-5">
                  <Link href={href} onClick={() => onRead(item.id)} className="min-w-0 flex-1">
                    <span className="line-clamp-1 font-medium text-stone-950">{item.title}</span>
                    <span className="line-clamp-2 text-stone-500">{item.message}</span>
                  </Link>
                  <button
                    type="button"
                    onClick={() => onDismiss(item.id)}
                    className="grid h-6 w-6 shrink-0 place-items-center rounded-md text-stone-400 hover:bg-white hover:text-stone-900"
                    aria-label="Dismiss notification"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
