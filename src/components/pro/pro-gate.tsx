"use client";

import { useEffect, useState, type ReactNode } from "react";
import { LockKeyhole, Sparkles } from "lucide-react";
import { api, type SubscriptionStatus } from "@/lib/api";
import { UpgradeCta } from "@/components/pro/upgrade-cta";
import { Skeleton } from "@/components/ui/skeleton";

export function ProGate({
  children,
  feature,
  description,
}: {
  children: ReactNode;
  feature: string;
  description: string;
}) {
  const [plan, setPlan] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getBilling()
      .then((data) => setPlan(data.plan))
      .catch(() => setPlan(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="mx-auto max-w-5xl p-5 md:p-7">
        <Skeleton className="h-64 rounded-lg" />
      </div>
    );
  }

  if (!plan?.isPro) {
    return (
      <div className="mx-auto max-w-4xl p-5 md:p-7">
        <section className="rounded-lg border border-stone-900 bg-stone-950 p-6 text-white shadow-soft">
          <p className="flex items-center gap-2 text-xs font-medium uppercase text-stone-400">
            <LockKeyhole className="h-3.5 w-3.5" />
            Synzept Pro
          </p>
          <h2 className="mt-3 text-2xl font-semibold">{feature}</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-stone-300">{description}</p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <UpgradeCta />
            <span className="inline-flex items-center gap-1 text-sm text-stone-300">
              <Sparkles className="h-4 w-4" />
              ₹399/month
            </span>
          </div>
        </section>
      </div>
    );
  }

  return <>{children}</>;
}
