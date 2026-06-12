"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Activity, ArrowDownRight, BarChart3, RefreshCw, TrendingUp } from "lucide-react";
import { PageFrame } from "@frontend/components/layout/page-frame";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type ProductAnalytics } from "@/lib/api";

const metricOrder = [
  "signups",
  "logins",
  "projectsCreated",
  "dailyActiveUsers",
  "weeklyActiveUsers",
  "dailyBriefViews",
  "openLoopViews",
  "upgradeClicks",
  "checkoutStarts",
  "successfulPayments",
];

export default function FounderAnalyticsPage() {
  const [data, setData] = useState<ProductAnalytics | null>(null);
  const [windowDays, setWindowDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return api
      .getProductAnalytics(windowDays)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Analytics could not load."))
      .finally(() => setLoading(false));
  }, [windowDays]);

  useEffect(() => {
    load();
  }, [load]);

  const metrics = useMemo(() => {
    const byKey = new Map((data?.metrics || []).map((item) => [item.key, item]));
    return metricOrder.map((key) => byKey.get(key)).filter(Boolean);
  }, [data]);

  return (
    <PageFrame
      eyebrow="Internal"
      title="Founder Analytics"
      action={
        <div className="flex items-center gap-2">
          <select
            value={windowDays}
            onChange={(event) => setWindowDays(Number(event.target.value))}
            className="h-9 rounded-md border border-border bg-white px-2 text-sm"
          >
            <option value={7}>7 days</option>
            <option value={30}>30 days</option>
            <option value={90}>90 days</option>
          </select>
          <Button size="sm" variant="outline" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-1.5 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      }
    >
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-7">
        <RecoveryBanner message={error} onRetry={load} />
        {loading && !data ? (
          <AnalyticsSkeleton />
        ) : data ? (
          <>
            <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
              {metrics.map((metric) => metric && <MetricCard key={metric.key} label={metric.label} value={metric.value} change={metric.change} />)}
            </section>

            <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
                <SectionTitle icon={<BarChart3 className="h-4 w-4" />} title="Activation Funnel" />
                <div className="mt-4 space-y-3">
                  {data.funnel.map((step, index) => (
                    <div key={step.key} className="rounded-md bg-stone-50 px-3 py-3">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-sm font-medium text-stone-950">{index + 1}. {step.label}</p>
                        <p className="text-lg font-semibold text-stone-950">{step.count}</p>
                      </div>
                      <div className="mt-2 h-2 overflow-hidden rounded-full bg-stone-200">
                        <div className="h-full rounded-full bg-stone-900" style={{ width: `${Math.min(step.conversionFromPrevious ?? 100, 100)}%` }} />
                      </div>
                      {step.conversionFromPrevious !== null && (
                        <p className="mt-1 text-xs text-muted">{step.conversionFromPrevious}% from previous step</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-lg border border-border bg-white p-5 shadow-soft">
                <SectionTitle icon={<ArrowDownRight className="h-4 w-4" />} title="Largest Drop-Offs" />
                <div className="mt-4 space-y-2">
                  {data.dropOffs.slice(0, 5).map((item) => (
                    <div key={item.label} className="rounded-md bg-stone-50 px-3 py-3">
                      <p className="text-sm font-medium text-stone-950">{item.label}</p>
                      <p className="mt-1 text-xs text-muted">{item.lost} users lost, {item.dropOffRate}% drop-off</p>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
              <SectionTitle icon={<Activity className="h-4 w-4" />} title="Daily Movement" />
              <div className="mt-4 overflow-x-auto">
                <table className="w-full min-w-[760px] text-left text-sm">
                  <thead className="text-xs uppercase text-muted">
                    <tr>
                      <th className="py-2">Date</th>
                      <th>Active</th>
                      <th>Signups</th>
                      <th>Projects</th>
                      <th>Brief</th>
                      <th>Loops</th>
                      <th>Upgrade</th>
                      <th>Checkout</th>
                      <th>Paid</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border">
                    {data.daily.slice(-14).reverse().map((row) => (
                      <tr key={row.date}>
                        <td className="py-2 font-medium text-stone-900">{row.date}</td>
                        <td>{row.activeUsers}</td>
                        <td>{row.signups}</td>
                        <td>{row.projectsCreated}</td>
                        <td>{row.dailyBriefViews}</td>
                        <td>{row.openLoopViews}</td>
                        <td>{row.upgradeClicks}</td>
                        <td>{row.checkoutStarts}</td>
                        <td>{row.successfulPayments}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        ) : null}
      </div>
    </PageFrame>
  );
}

function MetricCard({ label, value, change }: { label: string; value: number; change: number }) {
  return (
    <div className="rounded-lg border border-border bg-white p-4 shadow-soft">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-stone-950">{value}</p>
      <p className={`mt-2 flex items-center gap-1 text-xs ${change >= 0 ? "text-emerald-700" : "text-red-700"}`}>
        <TrendingUp className="h-3.5 w-3.5" />
        {change >= 0 ? "+" : ""}{change} vs previous window
      </p>
    </div>
  );
}

function SectionTitle({ icon, title }: { icon: ReactNode; title: string }) {
  return (
    <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
      {icon}
      {title}
    </p>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} className="h-32 rounded-lg" />)}
      </div>
      <Skeleton className="h-96 rounded-lg" />
    </div>
  );
}
