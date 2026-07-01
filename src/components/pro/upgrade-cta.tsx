"use client";

import { useState } from "react";
import { ArrowRight, Sparkles } from "lucide-react";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { api } from "@/lib/api";
import { ProUpgradeModal } from "@/components/pro/pro-upgrade-modal";

export function UpgradeCta({ compact = false, className }: { compact?: boolean; className?: string }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => {
          void api.trackEvent("upgrade_clicked", "upgrade_cta", { compact });
          setOpen(true);
        }}
        className={cn(
          buttonVariants({ size: compact ? "sm" : "default" }),
          "gap-2",
          className,
        )}
      >
        <Sparkles className="h-4 w-4" />
        Upgrade to Pro
        {!compact && <ArrowRight className="h-4 w-4" />}
      </button>
      <ProUpgradeModal open={open} onOpenChange={setOpen} />
    </>
  );
}
