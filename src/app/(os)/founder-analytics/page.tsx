"use client";

import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, BarChart3, Copy, MessageSquareText, RefreshCw, Send, TrendingDown, TrendingUp, UserCheck, Users } from "lucide-react";
import { PageFrame } from "@frontend/components/layout/page-frame";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RecoveryBanner } from "@/components/ui/recovery-banner";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { api, type FeedbackSignal, type FirstUserSession, type FirstUsersLaunch, type FounderAlert, type ProductAnalytics, type ProductAnalyticsFeatureUsage } from "@/lib/api";

const EMPTY_INTERVIEW = {
  target_user_email: "",
  understood: "",
  useful: "",
  confusing: "",
  come_back_tomorrow: "",
  confusing_moments: "",
  exciting_moments: "",
  drop_off_points: "",
};

export default function FounderAnalyticsPage() {
  const [data, setData] = useState<ProductAnalytics | null>(null);
  const [launch, setLaunch] = useState<FirstUsersLaunch | null>(null);
  const [windowDays, setWindowDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [interview, setInterview] = useState(EMPTY_INTERVIEW);
  const [savingInvite, setSavingInvite] = useState(false);
  const [savingInterview, setSavingInterview] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    return Promise.all([api.getProductAnalytics(windowDays), api.getFirstUsersLaunch()])
      .then(([analytics, launchData]) => {
        setData(analytics);
        setLaunch(launchData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Founder Mode could not load."))
      .finally(() => setLoading(false));
  }, [windowDays]);

  useEffect(() => {
    load();
  }, [load]);

  const nextImprovement = useMemo(() => data?.founderAlerts?.[0], [data]);
  const selectedUser = launch?.first_users.find((user) => user.email === interview.target_user_email);

  const createInvite = async () => {
    setSavingInvite(true);
    setError(null);
    try {
      await api.createInvite({ email: inviteEmail.trim() || undefined, max_uses: 1, notes: "First real users launch" });
      setInviteEmail("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite could not be created.");
    } finally {
      setSavingInvite(false);
    }
  };

  const saveInterview = async () => {
    if (!interview.target_user_email.trim()) {
      setError("Choose the user this interview belongs to.");
      return;
    }
    setSavingInterview(true);
    setError(null);
    try {
      await api.sendFeedback({
        feedback_type: "user_interview",
        rating: normalizeTomorrow(interview.come_back_tomorrow) === "yes" ? 5 : normalizeTomorrow(interview.come_back_tomorrow) === "no" ? 2 : 3,
        message: [
          `What did they think Synzept does? ${interview.understood}`,
          `What was useful? ${interview.useful}`,
          `What was confusing? ${interview.confusing}`,
          `Would they come back tomorrow? ${interview.come_back_tomorrow}`,
        ].join("\n"),
        metadata: {
          target_user_email: interview.target_user_email.trim().toLowerCase(),
          understood: interview.understood,
          useful: interview.useful,
          confusing: interview.confusing,
          come_back_tomorrow: normalizeTomorrow(interview.come_back_tomorrow),
          confusing_moments: splitLines(interview.confusing_moments || interview.confusing),
          exciting_moments: splitLines(interview.exciting_moments || interview.useful),
          drop_off_points: splitLines(interview.drop_off_points),
          session_watched: true,
        },
      });
      setInterview(EMPTY_INTERVIEW);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Interview feedback could not be saved.");
    } finally {
      setSavingInterview(false);
    }
  };

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

              {launch ? (
                <Section title="First 10 Users Launch" icon={<UserCheck className="h-4 w-4" />}>
                  <div className="grid gap-4 xl:grid-cols-[1fr_380px]">
                    <div className="space-y-4">
                      <div className="grid gap-3 sm:grid-cols-3">
                        <MetricCard label="Invited" value={`${launch.invited_users}/${launch.target_users}`} detail={`${launch.accepted_invites} accepted`} />
                        <MetricCard label="Active users" value={`${launch.active_users}/${launch.target_users}`} detail={`${launch.completed_onboarding} completed onboarding`} />
                        <MetricCard label="Interviews" value={`${launch.interviews_completed}/${launch.target_users}`} detail={`${launch.sessions_watched} sessions watched`} />
                      </div>
                      <FirstUserTable users={launch.first_users} onSelect={(email) => setInterview((current) => ({ ...current, target_user_email: email }))} />
                    </div>

                    <div className="space-y-4">
                      <div className="rounded-md bg-stone-50 p-3">
                        <p className="text-sm font-semibold text-stone-950">Create onboarding invite</p>
                        <div className="mt-3 flex gap-2">
                          <Input value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="user@email.com" />
                          <Button onClick={createInvite} disabled={savingInvite}>
                            {savingInvite ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                          </Button>
                        </div>
                        <div className="mt-3 space-y-2">
                          {launch.invites.slice(0, 5).map((invite) => (
                            <InviteRow key={invite.id} baseUrl={launch.invite_url_base} code={invite.code} email={invite.email} used={invite.use_count} max={invite.max_uses} />
                          ))}
                        </div>
                      </div>

                      <InterviewForm
                        interview={interview}
                        selectedUser={selectedUser}
                        users={launch.first_users}
                        saving={savingInterview}
                        onChange={setInterview}
                        onSave={saveInterview}
                      />
                    </div>
                  </div>
                </Section>
              ) : null}

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

function FirstUserTable({ users, onSelect }: { users: FirstUserSession[]; onSelect: (email: string) => void }) {
  return (
    <div className="overflow-x-auto rounded-md bg-stone-50">
      <table className="w-full min-w-[720px] text-left text-sm">
        <thead className="text-xs uppercase text-stone-400">
          <tr>
            <th className="px-3 py-2">User</th>
            <th>Onboarding</th>
            <th>Events</th>
            <th>Last activity</th>
            <th>Watched</th>
            <th>Interview</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-stone-200">
          {users.map((user) => (
            <tr key={user.user_id}>
              <td className="px-3 py-2 font-medium text-stone-950">{user.email}</td>
              <td>{user.onboarding_state}</td>
              <td>{user.session_events}</td>
              <td>{formatDate(user.last_activity_at)}</td>
              <td>{user.confusing_moments.length || user.exciting_moments.length || user.drop_off_points.length ? "Yes" : "No"}</td>
              <td>
                <button type="button" onClick={() => onSelect(user.email)} className="text-sm font-medium text-stone-950 underline-offset-4 hover:underline">
                  {user.interview_completed ? "Update" : "Record"}
                </button>
              </td>
            </tr>
          ))}
          {!users.length ? (
            <tr>
              <td colSpan={6} className="px-3 py-5 text-sm text-stone-500">Create invites and onboard the first 10 users.</td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

function InviteRow({ baseUrl, code, email, used, max }: { baseUrl: string; code: string; email: string | null; used: number; max: number }) {
  const url = `${baseUrl}?invite=${encodeURIComponent(code)}`;
  return (
    <div className="rounded-md bg-white px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-stone-950">{email || "Open invite"}</p>
          <p className="truncate text-xs text-stone-500">{url}</p>
        </div>
        <button type="button" onClick={() => navigator.clipboard?.writeText(url)} className="rounded-md border border-stone-200 p-2 text-stone-600 hover:bg-stone-50" aria-label="Copy invite link">
          <Copy className="h-4 w-4" />
        </button>
      </div>
      <p className="mt-1 text-[11px] text-stone-400">{used}/{max} used</p>
    </div>
  );
}

function InterviewForm({
  interview,
  selectedUser,
  users,
  saving,
  onChange,
  onSave,
}: {
  interview: typeof EMPTY_INTERVIEW;
  selectedUser?: FirstUserSession;
  users: FirstUserSession[];
  saving: boolean;
  onChange: (value: typeof EMPTY_INTERVIEW) => void;
  onSave: () => void;
}) {
  return (
    <div className="rounded-md bg-stone-50 p-3">
      <p className="text-sm font-semibold text-stone-950">Record user interview</p>
      <select
        value={interview.target_user_email}
        onChange={(event) => onChange({ ...interview, target_user_email: event.target.value })}
        className="mt-3 h-10 w-full rounded-md border border-stone-200 bg-white px-3 text-sm"
      >
        <option value="">Choose first user</option>
        {users.map((user) => <option key={user.user_id} value={user.email}>{user.email}</option>)}
      </select>
      {selectedUser ? <p className="mt-2 text-xs text-stone-500">{selectedUser.session_events} events watched, {selectedUser.feedback_items} feedback items</p> : null}
      <InterviewField label="What did you think Synzept does?" value={interview.understood} onChange={(value) => onChange({ ...interview, understood: value })} />
      <InterviewField label="What was useful?" value={interview.useful} onChange={(value) => onChange({ ...interview, useful: value })} />
      <InterviewField label="What was confusing?" value={interview.confusing} onChange={(value) => onChange({ ...interview, confusing: value })} />
      <InterviewField label="Would you come back tomorrow?" value={interview.come_back_tomorrow} onChange={(value) => onChange({ ...interview, come_back_tomorrow: value })} />
      <InterviewField label="Confusing moments" value={interview.confusing_moments} onChange={(value) => onChange({ ...interview, confusing_moments: value })} />
      <InterviewField label="Exciting moments" value={interview.exciting_moments} onChange={(value) => onChange({ ...interview, exciting_moments: value })} />
      <InterviewField label="Drop-off points" value={interview.drop_off_points} onChange={(value) => onChange({ ...interview, drop_off_points: value })} />
      <Button className="mt-3 w-full" onClick={onSave} disabled={saving}>
        {saving ? <RefreshCw className="mr-2 h-4 w-4 animate-spin" /> : <MessageSquareText className="mr-2 h-4 w-4" />}
        Save interview
      </Button>
    </div>
  );
}

function InterviewField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="mt-3 block">
      <span className="mb-1.5 block text-xs font-medium text-stone-500">{label}</span>
      <Textarea rows={2} value={value} onChange={(event) => onChange(event.target.value)} className="min-h-16 bg-white text-sm" />
    </label>
  );
}

function splitLines(value: string) {
  return value
    .split(/\n|;/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 5);
}

function normalizeTomorrow(value: string) {
  const clean = value.trim().toLowerCase();
  if (/^y|yes|would|definitely|sure/.test(clean)) return "yes";
  if (/^n|no|not/.test(clean)) return "no";
  return clean || "unsure";
}

function formatDate(value: string | null) {
  if (!value) return "None";
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(new Date(value));
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
