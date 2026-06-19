"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, BarChart3, MessageSquareText, RefreshCw, TrendingDown, TrendingUp, Users } from "lucide-react";
import { PageFrame } from "@frontend/components/layout/page-frame";
import { Button } from "@/components/ui/button";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type FeedbackSignal, type FounderAlert, type ProductAnalytics, type ProductAnalyticsFeatureUsage } from "@/lib/api";

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
      .catch((err) => setError(err instanceof Error ? err.message : "Founder Mode could not load."))
      .finally(() => setLoading(false));
  }, [windowDays]);

  useEffect(() => {
    load();
  }, [load]);

  const nextImprovement = useMemo(() => data?.founderAlerts?.[0], [data]);

  return (
    <PageFrame
      eyebrow="Founder"
      title="Product Health"
      action={
        <div className="flex items-center gap-2">
          <select value={windowDays} onChange={(event) => setWindowDays(Number(event.target.value))} className="h-9 rounded-md border border-border bg-white px-2 text-sm">
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
      <div className="min-h-full bg-white">
        <div className="mx-auto max-w-7xl space-y-5 px-4 py-6 pb-24 sm:px-6 lg:px-8">
          <RecoveryBanner message={error} onRetry={load} />
          {loading && !data ? (
            <FounderSkeleton />
          ) : data ? (
            <>
              <section className="rounded-lg border border-stone-200 bg-stone-950 p-5 text-white shadow-[0_18px_60px_rgba(32,31,28,0.16)] sm:p-6">
                <p className="text-xs font-medium uppercase tracking-[0.16em] text-stone-400">What to improve next</p>
                <h1 className="mt-3 max-w-4xl text-3xl font-semibold leading-tight sm:text-5xl">
                  {nextImprovement?.title || "Product health is ready to inspect."}
                </h1>
                <p className="mt-4 max-w-3xl text-sm leading-6 text-stone-300">
                  {nextImprovement?.detail || "Founder Mode combines users, activation, retention, usage, and feedback into one product-health view."}
                </p>
              </section>

              <Section title="Users" icon={<Users className="h-4 w-4" />}>
                <div className="grid gap-3 md:grid-cols-3">
                  <MetricCard label="Total users" value={data.users.totalUsers} />
                  <MetricCard label="New users" value={data.users.newUsers} />
                  <MetricCard label="Active users" value={data.users.activeUsers} />
                </div>
              </Section>

              <div className="grid gap-5 xl:grid-cols-2">
                <Section title="Activation" icon={<TrendingUp className="h-4 w-4" />}>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <MetricCard label="Completed onboarding" value={data.activation.completedOnboarding} detail={`${data.activation.completedOnboardingRate}% of new users`} />
                    <MetricCard label="Created first mission" value={data.activation.createdFirstMission} detail={`${data.activation.createdFirstMissionRate}% of new users`} />
                    <MetricCard label="Returned next day" value={data.activation.returnedNextDay} detail={`${data.activation.returnedNextDayRate}% of new users`} />
                  </div>
                </Section>

                <Section title="Retention" icon={<BarChart3 className="h-4 w-4" />}>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <MetricCard label="Day 1" value={`${data.retention.day1}%`} detail={`${data.retention.returnedUsers} returned`} />
                    <MetricCard label="Day 7" value={`${data.retention.day7}%`} detail={`${data.retention.signupCohort} in cohort`} />
                    <MetricCard label="Day 30" value={`${data.retention.day30}%`} detail={`${data.retention.retentionRate}% any return`} />
                  </div>
                </Section>
              </div>

              <div className="grid gap-5 xl:grid-cols-2">
                <Section title="Most Used Features" icon={<TrendingUp className="h-4 w-4" />}>
                  <FeatureList features={data.mostUsedFeatures} empty="Feature usage appears after users browse the app." />
                </Section>
                <Section title="Least Used Features" icon={<TrendingDown className="h-4 w-4" />}>
                  <FeatureList features={data.leastUsedFeatures} empty="No low-usage feature signal yet." />
                </Section>
              </div>

              <div className="grid gap-5 xl:grid-cols-[1fr_420px]">
                <Section title="Drop-off Points" icon={<TrendingDown className="h-4 w-4" />}>
                  <div className="space-y-2">
                    {data.dropOffs.slice(0, 6).map((item) => (
                      <div key={item.label} className="rounded-md bg-stone-50 px-3 py-3">
                        <div className="flex items-center justify-between gap-3">
                          <p className="text-sm font-medium text-stone-950">{item.label}</p>
                          <span className="text-sm font-semibold text-stone-950">{item.dropOffRate}%</span>
                        </div>
                        <p className="mt-1 text-xs text-stone-500">{item.lost} users lost from {item.fromStep} to {item.toStep}</p>
                      </div>
                    ))}
                  </div>
                </Section>

                <Section title="Founder Alerts" icon={<AlertTriangle className="h-4 w-4" />}>
                  <AlertList alerts={data.founderAlerts} />
                </Section>
              </div>

              <Section title="Feedback" icon={<MessageSquareText className="h-4 w-4" />}>
                <div className="grid gap-4 lg:grid-cols-3">
                  <FeedbackList title="User feedback" items={[...data.feedback.most_common_frustrations, ...data.feedback.most_common_compliments]} empty="No feedback yet." />
                  <FeedbackList title="Feature requests" items={data.feedback.most_requested_features} empty="No feature requests yet." />
                  <FeedbackList title="Confusing areas" items={data.confusingAreas} empty="No confusion signal yet." />
                </div>
              </Section>

              <Section title="Daily Movement" icon={<BarChart3 className="h-4 w-4" />}>
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[760px] text-left text-sm">
                    <thead className="text-xs uppercase text-stone-400">
                      <tr>
                        <th className="py-2">Date</th>
                        <th>Active</th>
                        <th>Signups</th>
                        <th>Projects</th>
                        <th>Brief</th>
                        <th>Loops</th>
                        <th>Upgrade</th>
                        <th>Paid</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-200">
                      {data.daily.slice(-14).reverse().map((row) => (
                        <tr key={row.date}>
                          <td className="py-2 font-medium text-stone-900">{row.date}</td>
                          <td>{row.activeUsers}</td>
                          <td>{row.signups}</td>
                          <td>{row.projectsCreated}</td>
                          <td>{row.dailyBriefViews}</td>
                          <td>{row.openLoopViews}</td>
                          <td>{row.upgradeClicks}</td>
                          <td>{row.successfulPayments}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>
            </>
          ) : null}
        </div>
      </div>
    </PageFrame>
  );
}

function Section({ title, icon, children }: { title: string; icon: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-[0_10px_30px_rgba(32,31,28,0.05)] sm:p-5">
      <p className="mb-4 flex items-center gap-2 text-sm font-semibold text-stone-950">
        {icon}
        {title}
      </p>
      {children}
    </section>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: number | string; detail?: string }) {
  return (
    <div className="rounded-md bg-stone-50 px-3 py-4">
      <p className="text-xs font-medium uppercase tracking-[0.12em] text-stone-400">{label}</p>
      <p className="mt-3 text-3xl font-semibold text-stone-950">{value}</p>
      {detail ? <p className="mt-2 text-xs leading-5 text-stone-500">{detail}</p> : null}
    </div>
  );
}

function FeatureList({ features, empty }: { features: ProductAnalyticsFeatureUsage[]; empty: string }) {
  return (
    <div className="space-y-2">
      {features.slice(0, 8).map((feature) => (
        <div key={feature.feature} className="rounded-md bg-stone-50 px-3 py-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium capitalize text-stone-950">{feature.feature.replace(/[_-]/g, " ")}</p>
            <span className="text-sm font-semibold text-stone-950">{feature.users}</span>
          </div>
          <p className="mt-1 text-xs text-stone-500">{feature.events} events / {Math.round(feature.timeSpentSeconds / 60)} min</p>
        </div>
      ))}
      {!features.length ? <p className="text-sm leading-6 text-stone-500">{empty}</p> : null}
    </div>
  );
}

function AlertList({ alerts }: { alerts: FounderAlert[] }) {
  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div key={`${alert.metric}-${alert.title}`} className="rounded-md bg-stone-50 px-3 py-3">
          <p className="text-sm font-medium text-stone-950">{alert.title}</p>
          <p className="mt-1 text-xs leading-5 text-stone-500">{alert.detail}</p>
          <p className="mt-2 text-[11px] uppercase tracking-[0.12em] text-stone-400">{alert.severity}</p>
        </div>
      ))}
      {!alerts.length ? <p className="text-sm leading-6 text-stone-500">No urgent founder alerts in this window.</p> : null}
    </div>
  );
}

function FeedbackList({ title, items, empty }: { title: string; items: FeedbackSignal[]; empty: string }) {
  return (
    <div className="rounded-md bg-stone-50 p-3">
      <p className="text-sm font-semibold text-stone-950">{title}</p>
      <div className="mt-3 space-y-2">
        {items.slice(0, 5).map((item) => (
          <div key={`${item.id || item.title}-${item.category}`} className="rounded-md bg-white px-3 py-2">
            <p className="line-clamp-2 text-sm font-medium text-stone-900">{item.title}</p>
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-stone-500">{item.detail || item.category}</p>
            <p className="mt-2 text-[11px] text-stone-400">{item.category} / {item.status.replace(/_/g, " ")} / {item.votes} votes</p>
          </div>
        ))}
        {!items.length ? <p className="text-sm leading-6 text-stone-500">{empty}</p> : null}
      </div>
    </div>
  );
}

function FounderSkeleton() {
  return (
    <div className="space-y-5">
      <Skeleton className="h-56 rounded-lg" />
      <div className="grid gap-3 md:grid-cols-3">
        {Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-32 rounded-lg" />)}
      </div>
      <Skeleton className="h-96 rounded-lg" />
    </div>
  );
}
