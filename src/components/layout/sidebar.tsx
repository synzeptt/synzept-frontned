"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Brain,
  CalendarDays,
  LayoutDashboard,
  ListChecks,
  History,
  Settings,
  Sparkles,
  Target,
} from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { UpgradeCta } from "@/components/pro/upgrade-cta";
import { cn } from "@/lib/cn";
import { useAuthStore } from "@/stores/auth";

const links = [
  { href: "/dashboard", label: "OS", icon: LayoutDashboard },
  { href: "/autonomous-workspace", label: "Execution", icon: Target },
  { href: "/agent", label: "Agent", icon: Sparkles },
  { href: "/daily-brief", label: "Daily Brief", icon: CalendarDays },
  { href: "/open-loops", label: "Open Loops", icon: ListChecks },
  { href: "/weekly-reflection", label: "Weekly", icon: History },
  { href: "/knows-you", label: "Knows You", icon: Brain },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useAuthStore();
  const isPro = Boolean(user?.is_pro);

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

      <div className="px-3 pb-3">
        <div className="rounded-lg border border-border bg-white p-3">
          <p className="text-xs font-medium text-stone-950">Current Plan: {isPro ? "Pro" : "Free"}</p>
          <p className="mt-1 text-[11px] leading-4 text-muted">{isPro ? "Pro continuity features are unlocked." : "Unlock Pro for ₹399/month."}</p>
          {!isPro && <UpgradeCta compact className="mt-3 w-full" />}
          {isPro && (
            <Link href="/billing" className="mt-3 inline-flex h-8 w-full items-center justify-center rounded-lg border border-border text-xs font-medium text-stone-700 hover:bg-stone-50">
              Manage Billing
            </Link>
          )}
        </div>
      </div>

      <p className="px-5 py-4 text-[11px] leading-relaxed text-muted">
        Memory · Context · Continuity
      </p>
    </aside>
  );
}
