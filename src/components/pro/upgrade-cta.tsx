"use client";

import Link from "next/link";
import { ArrowRight, Sparkles } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";

export function UpgradeCta({ compact = false, className }: { compact?: boolean; className?: string }) {
  return (
    <Link
      href="/pricing"
      onClick={() => api.trackEvent("upgrade_clicked", "upgrade_cta", { compact })}
      className={cn(
        buttonVariants({ size: compact ? "sm" : "default" }),
        "gap-2",
        className,
      )}
    >
      <Sparkles className="h-4 w-4" />
      Upgrade to Pro
      {!compact && <ArrowRight className="h-4 w-4" />}
    </Link>
  );
}
