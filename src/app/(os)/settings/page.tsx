"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Loader2, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useConnectedAppsStore } from "@/stores/connected-apps";
import { Page, PageHeader, SettingsRow, SettingsSection } from "@/components/design-system/workspace-primitives";

export default function SettingsPage() {
  const user = useAuthStore((state) => state.user);
  const { apps, refresh: refreshApps, isLoading: appsLoading } = useConnectedAppsStore();
  const [updating, setUpdating] = useState(false);
  const [displayName, setDisplayName] = useState(user?.display_name || "");
  const [saved, setSaved] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);

  useEffect(() => {
    void refreshApps(true);
  }, [refreshApps]);

  const handleSaveName = async () => {
    setUpdating(true);
    try {
      await api.updateProfile({ display_name: displayName });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Profile could not be saved.");
    } finally {
      setUpdating(false);
    }
  };

  const disconnect = async (provider: string) => {
    setMessage(null);
    try {
      if (provider === "google_calendar") await api.disconnectGoogleCalendar();
      else await api.disconnectGoogleWorkspaceService(provider);
      await refreshApps(true);
      setMessage("Connected service disconnected.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "The connected service could not be disconnected.");
    }
  };

  const updateNotifications = async (enabled: boolean) => {
    setNotificationsEnabled(enabled);
    try {
      await api.updateNotificationSettings({ email: enabled });
      setMessage("Notification preferences saved.");
    } catch (err) {
      setNotificationsEnabled(!enabled);
      setMessage(err instanceof Error ? err.message : "Notification preferences could not be saved.");
    }
  };

  const sendPasswordReset = async () => {
    if (!user?.email) return;
    setMessage(null);
    try {
      await api.forgotPassword(user.email);
      setMessage("Password reset instructions were sent to your email.");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Password reset could not be requested.");
    }
  };

  const deleteAccount = async () => {
    if (!window.confirm("Delete your account and all workspace data? This cannot be undone.")) return;
    const confirmation = window.prompt('Type DELETE to confirm account deletion.')?.trim();
    if (confirmation !== "DELETE") return;
    const password = window.prompt("Enter your password, or leave blank for a social-login account.") || undefined;
    setMessage(null);
    try {
      await useAuthStore.getState().deleteAccount(password, confirmation);
      window.location.assign("/login");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Account deletion could not be completed.");
    }
  };

  const connectedCount = Object.values(apps).filter(
    (app) => app?.connected === true
  ).length;

  return (
    <Page>
      <div className="mx-auto max-w-3xl space-y-8 px-5 py-12 sm:px-8 sm:py-16">
        <PageHeader eyebrow="System" title="Settings" description="Account, workspace, and connection preferences." />
        {message && <p role="status" className="border-y border-[var(--border)] py-3 text-sm text-[var(--text-secondary)]">{message}</p>}

        <SettingsSection title="Account" description="Your profile, plan, and account details.">
          <SettingsRow label="Display name" description="This is how Synzept refers to you in the workspace.">
            <div className="flex w-full min-w-[220px] gap-2 sm:w-auto">
              <input
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="h-10 min-w-0 flex-1 rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3.5 text-sm text-[var(--text-primary)] outline-none transition focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/10"
              />
              <Button onClick={handleSaveName} disabled={updating || displayName === user?.display_name} loading={updating} variant="secondary">
                Save
              </Button>
            </div>
          </SettingsRow>
          {saved && <p className="flex items-center gap-2 text-sm text-[var(--success)]"><CheckCircle2 className="h-4 w-4" /> Saved successfully</p>}
          <SettingsRow label="Email" description="Used for login, billing, and important account notices."><span className="text-sm text-[var(--text-primary)]">{user?.email}</span></SettingsRow>
          <SettingsRow label="Plan" description="Your current Synzept plan."><span className="text-sm text-[var(--text-primary)]">{user?.is_pro ? "Pro" : "Free"}</span></SettingsRow>
        </SettingsSection>

        <SettingsSection title="Connected services" description="Infrastructure Synzept can use when relevant.">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium uppercase tracking-[0.16em] text-[var(--text-muted)]">{connectedCount} active</span>
            <Link href="/connected-apps" className="text-sm font-medium text-[var(--text-primary)] underline underline-offset-4">Manage connected apps</Link>
          </div>

          {appsLoading ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="h-5 w-5 animate-spin text-[var(--text-muted)]" /></div>
          ) : (
            <div className="space-y-3">
              {Object.entries(apps).filter(([, app]) => app !== undefined).map(([provider, app]) => (
                <SettingsRow key={provider} label={app?.provider || provider.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())} description={app?.connected ? "Connected and available to Synzept when relevant" : "Not currently connected"}>
                  {app?.connected ? (
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-[var(--success)]" />
                      <Button variant="ghost" size="sm" onClick={() => void disconnect(provider)}>
                        Disconnect
                      </Button>
                    </div>
                  ) : (
                    <span className="text-xs font-medium uppercase tracking-[0.14em] text-[var(--text-muted)]">Connect</span>
                  )}
                </SettingsRow>
              ))}
            </div>
          )}
        </SettingsSection>

        <SettingsSection title="Notifications" description="Updates and reminders from your workflow.">
          <SettingsRow label="Email when tasks complete" description="Get notified when Synzept finishes working on your requests.">
            <label className="inline-flex cursor-pointer items-center gap-3">
              <input type="checkbox" checked={notificationsEnabled} onChange={(event) => void updateNotifications(event.target.checked)} className="h-4 w-4 rounded border-[var(--border)] text-[var(--accent)]" />
            </label>
          </SettingsRow>
        </SettingsSection>

        <SettingsSection title="Security" description="Account and access controls.">
          <SettingsRow label="Change password" description="Update your account password.">
            <Button variant="secondary" onClick={() => void sendPasswordReset()}>Send reset email</Button>
          </SettingsRow>
        </SettingsSection>

        <SettingsSection title="Danger zone" description="Permanent account actions.">
          <SettingsRow label="Delete account" description="Permanently delete your account and all workspace data." className="border-[var(--danger)]/25 bg-[var(--danger-soft)]">
            <Button variant="destructive" onClick={() => void deleteAccount()}>Delete account</Button>
          </SettingsRow>
        </SettingsSection>
      </div>
    </Page>
  );
}

