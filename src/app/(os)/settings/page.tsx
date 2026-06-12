"use client";

import { useEffect, useState, type ReactNode } from "react";
import { Bell, Check, CreditCard, LogOut, Mail, ShieldCheck, Sparkles, Smartphone, Trash2, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { PageHeader } from "@/components/layout/page-header";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { UpgradeCta } from "@/components/pro/upgrade-cta";
import { Textarea } from "@/components/ui/textarea";
import { api, type NotificationSettings } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout, deleteAccount } = useAuthStore();
  const {
    memoryEnabled,
    personalizationEnabled,
    analyticsEnabled,
    setMemoryEnabled,
    setPersonalizationEnabled,
    setAnalyticsEnabled,
  } = useSettingsStore();
  const [feedback, setFeedback] = useState("");
  const [supportMessage, setSupportMessage] = useState<string | null>(null);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [savingPreference, setSavingPreference] = useState<string | null>(null);
  const [notificationSettings, setNotificationSettings] = useState<NotificationSettings | null>(null);
  const [savingNotifications, setSavingNotifications] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  useEffect(() => {
    const prefs = user?.preferences || {};
    if (typeof prefs.memory_enabled === "boolean") setMemoryEnabled(prefs.memory_enabled);
    if (typeof prefs.personalization_enabled === "boolean") setPersonalizationEnabled(prefs.personalization_enabled);
    if (typeof prefs.analytics_enabled === "boolean") setAnalyticsEnabled(prefs.analytics_enabled);
  }, [setAnalyticsEnabled, setMemoryEnabled, setPersonalizationEnabled, user]);

  useEffect(() => {
    api.getNotifications().then((data) => setNotificationSettings(data.settings)).catch(() => null);
  }, []);

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
  };

  const updateTrustPreference = async (
    key: "memory_enabled" | "personalization_enabled" | "analytics_enabled",
    value: boolean,
  ) => {
    setSavingPreference(key);
    setSettingsError(null);
    const previous = {
      memory_enabled: memoryEnabled,
      personalization_enabled: personalizationEnabled,
      analytics_enabled: analyticsEnabled,
    }[key];
    if (key === "memory_enabled") setMemoryEnabled(value);
    if (key === "personalization_enabled") setPersonalizationEnabled(value);
    if (key === "analytics_enabled") setAnalyticsEnabled(value);
    try {
      await api.updatePreferences({ [key]: value });
      void api.trackEvent("trust_preference_changed", "settings", { key, value });
    } catch {
      if (key === "memory_enabled") setMemoryEnabled(previous);
      if (key === "personalization_enabled") setPersonalizationEnabled(previous);
      if (key === "analytics_enabled") setAnalyticsEnabled(previous);
      setSettingsError("Preference could not be saved. Nothing was changed on the server.");
    } finally {
      setSavingPreference(null);
    }
  };

  const sendSupport = async () => {
    if (!feedback.trim()) return;
    setSettingsError(null);
    setSupportMessage(null);
    try {
      await api.sendFeedback({ feedback_type: "support", message: feedback.trim() });
      setFeedback("");
      setSupportMessage("Sent. Thank you for helping make Synzept clearer.");
    } catch {
      setSettingsError("Support message could not be sent. Your text is still here.");
    }
  };

  const updateNotificationSetting = async (patch: Partial<NotificationSettings>) => {
    if (!notificationSettings) return;
    const previous = notificationSettings;
    const next = { ...notificationSettings, ...patch };
    setNotificationSettings(next);
    setSavingNotifications(true);
    setSettingsError(null);
    try {
      setNotificationSettings(await api.updateNotificationSettings(patch));
    } catch {
      setNotificationSettings(previous);
      setSettingsError("Notification settings could not be saved.");
    } finally {
      setSavingNotifications(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleteLoading(true);
    setDeleteError(null);
    try {
      await deleteAccount(deletePassword || undefined, deleteConfirmation);
      router.replace("/login?accountDeleted=1");
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Synzept could not delete the account. Please try again.");
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader label="Account" title="Settings" />

      <div className="mx-auto max-w-3xl space-y-5 px-4 py-5 md:px-8">
        {settingsError && (
          <p className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {settingsError}
          </p>
        )}
        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <div className="flex min-w-0 items-center gap-4">
            <Avatar name={user?.display_name} email={user?.email} src={user?.avatar_url} size="lg" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-stone-950">{user?.display_name || "Workspace"}</p>
              <p className="mt-0.5 truncate text-xs text-muted">{user?.email}</p>
            </div>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <SectionTitle title="Plan" description="Manage Synzept Pro access, billing status, and renewal." />
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="flex items-center gap-2 text-lg font-semibold text-stone-950">
                {user?.is_pro ? <Sparkles className="h-5 w-5 text-accent" /> : <CreditCard className="h-5 w-5 text-muted" />}
                Current Plan: {user?.is_pro ? "Pro" : "Free"}
              </p>
              <p className="mt-1 text-sm text-muted">{user?.is_pro ? "Pro features are unlocked." : "Upgrade to Synzept Pro for ₹399/month."}</p>
            </div>
            {user?.is_pro ? (
              <Link href="/billing" className="inline-flex h-10 items-center justify-center rounded-lg border border-border px-4 text-sm font-medium text-stone-700 hover:bg-stone-50">
                Manage Billing
              </Link>
            ) : (
              <UpgradeCta />
            )}
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <SectionTitle title="Trust Preferences" description="Only controls that affect continuity, memory, and product telemetry are shown here." />
          <div className="mt-3 divide-y divide-border">
            <ToggleRow
              label="Memory"
              description="Preserve useful context so Synzept can restore where you left off."
              checked={memoryEnabled}
              disabled={savingPreference === "memory_enabled"}
              onChange={() => updateTrustPreference("memory_enabled", !memoryEnabled)}
            />
            <ToggleRow
              label="Personalization"
              description="Use profile and memory to keep recommendations relevant."
              checked={personalizationEnabled}
              disabled={savingPreference === "personalization_enabled"}
              onChange={() => updateTrustPreference("personalization_enabled", !personalizationEnabled)}
            />
            <ToggleRow
              label="Usefulness analytics"
              description="Share lightweight events that help improve clarity and retention."
              checked={analyticsEnabled}
              disabled={savingPreference === "analytics_enabled"}
              onChange={() => updateTrustPreference("analytics_enabled", !analyticsEnabled)}
            />
          </div>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <SectionTitle title="Habit Notifications" description="Let Synzept bring you back to unfinished work at the right time." />
          {notificationSettings ? (
            <div className="mt-3 divide-y divide-border">
              <ToggleRow
                label="Enable notifications"
                description="Receive daily habit prompts and important continuity reminders."
                checked={notificationSettings.enabled}
                disabled={savingNotifications}
                onChange={() => updateNotificationSetting({ enabled: !notificationSettings.enabled })}
              />
              <div className="grid gap-3 py-4 sm:grid-cols-2">
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-muted">Frequency</span>
                  <select
                    value={notificationSettings.frequency}
                    onChange={(event) => updateNotificationSetting({ frequency: event.target.value as NotificationSettings["frequency"] })}
                    disabled={savingNotifications}
                    className="h-10 w-full rounded-lg border border-border bg-white px-3 text-sm text-stone-800 outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
                  >
                    <option value="daily">Daily</option>
                    <option value="weekdays">Weekdays</option>
                    <option value="important_only">Important only</option>
                    <option value="off">Off</option>
                  </select>
                </label>
                <label className="block">
                  <span className="mb-1.5 block text-xs font-medium text-muted">Morning brief time</span>
                  <input
                    type="time"
                    value={notificationSettings.morningTime}
                    onChange={(event) => updateNotificationSetting({ morningTime: event.target.value })}
                    disabled={savingNotifications}
                    className="h-10 w-full rounded-lg border border-border bg-white px-3 text-sm text-stone-800 outline-none focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
                  />
                </label>
              </div>
              <ToggleRow
                label="Daily Brief"
                description="Your Daily Brief is ready every morning."
                checked={notificationSettings.dailyBrief}
                disabled={savingNotifications}
                onChange={() => updateNotificationSetting({ dailyBrief: !notificationSettings.dailyBrief })}
              />
              <ToggleRow
                label="Open Loops"
                description="Important unfinished work, pending decisions, and overdue follow-ups."
                checked={notificationSettings.openLoops}
                disabled={savingNotifications}
                onChange={() => updateNotificationSetting({ openLoops: !notificationSettings.openLoops })}
              />
              <ToggleRow
                label="Project Attention"
                description="Inactive projects, blocked projects, and approaching milestones."
                checked={notificationSettings.projectAttention}
                disabled={savingNotifications}
                onChange={() => updateNotificationSetting({ projectAttention: !notificationSettings.projectAttention })}
              />
              <ToggleRow
                label="Return to Work"
                description="Come back after 3, 7, or 14 days away when unfinished work is waiting."
                checked={notificationSettings.returnToWork}
                disabled={savingNotifications}
                onChange={() => updateNotificationSetting({ returnToWork: !notificationSettings.returnToWork })}
              />
              <div className="grid gap-3 py-4 sm:grid-cols-2">
                <ChannelButton
                  icon={<Mail className="h-4 w-4" />}
                  label="Email notifications"
                  active={notificationSettings.email}
                  disabled={savingNotifications}
                  onClick={() => updateNotificationSetting({ email: !notificationSettings.email })}
                />
                <ChannelButton
                  icon={<Smartphone className="h-4 w-4" />}
                  label="Push notifications"
                  active={notificationSettings.push}
                  disabled={savingNotifications}
                  onClick={() => updateNotificationSetting({ push: !notificationSettings.push })}
                />
              </div>
            </div>
          ) : (
            <p className="mt-3 text-sm text-muted">Loading notification controls...</p>
          )}
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <SectionTitle title="Support" description="Send friction, missing context, or broken-action reports." />
          <Textarea
            value={feedback}
            onChange={(event) => setFeedback(event.target.value)}
            placeholder="What felt unclear or did not work?"
            className="mt-3 min-h-24"
          />
          {supportMessage && <p className="mt-3 rounded-md bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{supportMessage}</p>}
          <Button size="sm" onClick={sendSupport} disabled={!feedback.trim()} className="mt-3">
            <Check className="mr-1.5 h-4 w-4" />
            Send
          </Button>
        </section>

        <section className="rounded-lg border border-border bg-white p-5 shadow-soft">
          <SectionTitle title="Account Actions" />
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="outline" onClick={handleLogout}>
              <LogOut className="mr-1.5 h-4 w-4" />
              Sign out
            </Button>
            <Button variant="outline" onClick={() => setDeleteOpen(true)} className="text-stone-700">
              <Trash2 className="mr-1.5 h-4 w-4" />
              Delete account
            </Button>
          </div>
        </section>
      </div>

      {deleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/20 px-4">
          <div className="w-full max-w-lg rounded-lg border border-border bg-white p-6 shadow-panel">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-stone-950">Delete account</h2>
                <p className="mt-2 text-sm leading-6 text-muted">
                  This permanently removes your Synzept account and workspace data. This cannot be undone.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setDeleteOpen(false)}
                className="rounded-md p-2 text-muted hover:bg-stone-50 hover:text-stone-950"
                aria-label="Close delete account dialog"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-5 space-y-4">
              {user?.auth_provider !== "google" && (
                <div>
                  <label className="mb-1.5 block text-xs text-muted">Password</label>
                  <input
                    type="password"
                    value={deletePassword}
                    onChange={(event) => setDeletePassword(event.target.value)}
                    className="h-10 w-full rounded-lg border border-border bg-white px-3.5 text-sm text-stone-900 outline-none transition placeholder:text-muted focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
                    placeholder="Confirm your password"
                  />
                </div>
              )}
              <div>
                <label className="mb-1.5 block text-xs text-muted">Type DELETE to confirm</label>
                <input
                  value={deleteConfirmation}
                  onChange={(event) => setDeleteConfirmation(event.target.value)}
                  className="h-10 w-full rounded-lg border border-border bg-white px-3.5 text-sm text-stone-900 outline-none transition placeholder:text-muted focus:border-accent/40 focus:ring-2 focus:ring-accent/10"
                  placeholder="DELETE"
                />
              </div>
              {deleteError && (
                <p className="rounded-md border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
                  {deleteError}
                </p>
              )}
            </div>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={deleteLoading}>
                Keep account
              </Button>
              <Button
                onClick={handleDeleteAccount}
                disabled={deleteLoading || deleteConfirmation !== "DELETE" || (user?.auth_provider !== "google" && !deletePassword)}
                className="bg-stone-800 hover:bg-stone-900"
              >
                {deleteLoading ? "Deleting..." : "Delete account"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SectionTitle({ title, description }: { title: string; description?: string }) {
  return (
    <div>
      <p className="flex items-center gap-2 text-sm font-semibold text-stone-950">
        {title === "Habit Notifications" ? <Bell className="h-4 w-4 text-muted" /> : <ShieldCheck className="h-4 w-4 text-muted" />}
        {title}
      </p>
      {description && <p className="mt-1 text-sm leading-6 text-muted">{description}</p>}
    </div>
  );
}

function ChannelButton({
  icon,
  label,
  active,
  disabled,
  onClick,
}: {
  icon: ReactNode;
  label: string;
  active: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`flex h-11 items-center justify-center gap-2 rounded-lg border px-3 text-sm font-medium transition disabled:opacity-60 ${
        active ? "border-stone-900 bg-stone-950 text-white" : "border-border bg-white text-stone-700 hover:bg-stone-50"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  disabled: boolean;
  onChange: () => void;
}) {
  return (
    <div className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-medium text-stone-950">{label}</p>
        <p className="mt-0.5 text-xs leading-5 text-muted">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        disabled={disabled}
        onClick={onChange}
        className={`relative h-6 w-11 rounded-full transition disabled:opacity-60 ${checked ? "bg-accent" : "bg-stone-200"}`}
      >
        <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${checked ? "left-[22px]" : "left-0.5"}`} />
      </button>
    </div>
  );
}
