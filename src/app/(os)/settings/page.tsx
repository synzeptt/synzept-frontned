"use client";

import { useEffect, useState } from "react";
import { Check, Copy, Moon, Sun, Trash2, X } from "lucide-react";
import { PageHeader } from "@/components/layout/page-header";
import { Avatar } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, type Memory, type UsefulnessMetrics } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useSettingsStore } from "@/stores/settings";
import { useRouter } from "next/navigation";

function SettingRow({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-border py-5 last:border-0 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="text-sm font-medium text-stone-950">{label}</p>
        {description && <p className="mt-0.5 text-xs text-muted">{description}</p>}
      </div>
      {children}
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const { user, logout, deleteAccount, updateAvatar } = useAuthStore();
  const {
    appearance,
    memoryEnabled,
    personalizationEnabled,
    analyticsEnabled,
    setAppearance,
    setMemoryEnabled,
    setPersonalizationEnabled,
    setAnalyticsEnabled,
  } = useSettingsStore();
  const [memories, setMemories] = useState<Memory[]>([]);
  const [metrics, setMetrics] = useState<UsefulnessMetrics | null>(null);
  const [inviteCode, setInviteCode] = useState("");
  const [feedback, setFeedback] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const [avatarLoading, setAvatarLoading] = useState(false);

  const handleLogout = async () => {
    await logout();
    router.replace("/login");
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

  useEffect(() => {
    api.listMemories().then(setMemories).catch(() => undefined);
    api.getUsefulnessMetrics().then(setMetrics).catch(() => undefined);
  }, []);

  useEffect(() => {
    const prefs = user?.preferences || {};
    if (typeof prefs.memory_enabled === "boolean") setMemoryEnabled(prefs.memory_enabled);
    if (typeof prefs.personalization_enabled === "boolean") setPersonalizationEnabled(prefs.personalization_enabled);
    if (typeof prefs.analytics_enabled === "boolean") setAnalyticsEnabled(prefs.analytics_enabled);
  }, [setAnalyticsEnabled, setMemoryEnabled, setPersonalizationEnabled, user]);

  const updateTrustPreference = async (
    key: "memory_enabled" | "personalization_enabled" | "analytics_enabled",
    value: boolean,
  ) => {
    if (key === "memory_enabled") setMemoryEnabled(value);
    if (key === "personalization_enabled") setPersonalizationEnabled(value);
    if (key === "analytics_enabled") setAnalyticsEnabled(value);
    await api.updatePreferences({ [key]: value });
  };

  const updateMemory = async (memory: Memory, content: string) => {
    const updated = await api.updateMemory(memory.id, { content });
    setMemories((items) => items.map((item) => (item.id === memory.id ? updated : item)));
  };

  const removeMemory = async (id: string) => {
    await api.deleteMemory(id);
    setMemories((items) => items.filter((item) => item.id !== id));
  };

  const createInvite = async () => {
    const invite = await api.createInvite({ max_uses: 1 });
    setInviteCode(invite.code);
  };

  const sendSupport = async () => {
    if (!feedback.trim()) return;
    await api.sendFeedback({ feedback_type: "support", message: feedback });
    setFeedback("");
  };

  const uploadAvatar = async (file: File | undefined) => {
    if (!file) return;
    setAvatarError(null);
    if (!file.type.startsWith("image/")) {
      setAvatarError("Choose an image file for your profile photo.");
      return;
    }
    if (file.size > 650_000) {
      setAvatarError("Use an image under 650 KB.");
      return;
    }
    setAvatarLoading(true);
    try {
      const dataUrl = await readFileAsDataUrl(file);
      await updateAvatar(dataUrl);
    } catch (err) {
      setAvatarError(err instanceof Error ? err.message : "Synzept could not update your profile photo.");
    } finally {
      setAvatarLoading(false);
    }
  };

  const removeAvatar = async () => {
    setAvatarError(null);
    setAvatarLoading(true);
    try {
      await updateAvatar(null);
    } catch (err) {
      setAvatarError(err instanceof Error ? err.message : "Synzept could not remove your profile photo.");
    } finally {
      setAvatarLoading(false);
    }
  };

  return (
    <div className="h-[100dvh] overflow-y-auto">
      <PageHeader label="Preferences" title="Settings" />

      <div className="mx-auto max-w-3xl px-6 py-2 md:px-8">
        <section className="rounded-2xl border border-border bg-surface-raised/40 px-5">
          <div className="flex flex-col gap-4 border-b border-border py-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-4">
              <Avatar name={user?.display_name} email={user?.email} src={user?.avatar_url} size="lg" />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-stone-950">{user?.display_name || "Workspace"}</p>
                <p className="mt-0.5 truncate text-xs text-muted">{user?.email}</p>
                {user?.auth_provider === "google" && (
                  <p className="mt-1 text-[11px] text-muted">Google profile image syncs automatically.</p>
                )}
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="inline-flex h-8 cursor-pointer items-center justify-center rounded-lg border border-border bg-white px-3 text-xs font-medium text-stone-700 transition hover:bg-stone-50 hover:text-stone-950">
                {avatarLoading ? "Updating..." : user?.avatar_url ? "Replace photo" : "Upload photo"}
                <input
                  type="file"
                  accept="image/*"
                  className="sr-only"
                  disabled={avatarLoading}
                  onChange={(event) => uploadAvatar(event.target.files?.[0])}
                />
              </label>
              {user?.avatar_url && (
                <Button variant="outline" size="sm" onClick={removeAvatar} disabled={avatarLoading}>
                  Remove
                </Button>
              )}
            </div>
          </div>
          {avatarError && (
            <p className="border-b border-border py-3 text-sm text-red-700" role="alert">
              {avatarError}
            </p>
          )}

          <SettingRow label="Appearance" description="Choose the workspace tone that feels easiest to read">
            <div className="grid h-9 grid-cols-2 rounded-lg border border-border bg-surface p-0.5">
              <ThemeOption
                label="Light"
                icon={<Sun className="h-3.5 w-3.5" />}
                active={appearance === "light"}
                onClick={() => setAppearance("light")}
              />
              <ThemeOption
                label="Dark"
                icon={<Moon className="h-3.5 w-3.5" />}
                active={appearance === "dark"}
                onClick={() => setAppearance("dark")}
              />
            </div>
          </SettingRow>

          <SettingRow
            label="Privacy & memory"
            description="Synzept stores meaningful context you share. You can pause learning, disable personalization, edit memories, or delete memories here."
          >
            <span className="text-xs text-muted">You control your data</span>
          </SettingRow>

          <SettingRow label="Memory" description="Allow Synzept to preserve useful context from conversations">
            <button
              type="button"
              role="switch"
              aria-checked={memoryEnabled}
              onClick={() => updateTrustPreference("memory_enabled", !memoryEnabled)}
              className={`relative h-6 w-11 rounded-full transition ${
                memoryEnabled ? "bg-accent" : "bg-stone-200"
              }`}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${
                  memoryEnabled ? "left-[22px]" : "left-0.5"
                }`}
              />
            </button>
          </SettingRow>

          <SettingRow label="Personalization" description="Use profile and memory to keep responses relevant">
            <button
              type="button"
              role="switch"
              aria-checked={personalizationEnabled}
              onClick={() => updateTrustPreference("personalization_enabled", !personalizationEnabled)}
              className={`relative h-6 w-11 rounded-full transition ${
                personalizationEnabled ? "bg-accent" : "bg-stone-200"
              }`}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${
                  personalizationEnabled ? "left-[22px]" : "left-0.5"
                }`}
              />
            </button>
          </SettingRow>

          <SettingRow label="Usefulness analytics" description="Share lightweight product events that improve clarity and retention">
            <button
              type="button"
              role="switch"
              aria-checked={analyticsEnabled}
              onClick={() => updateTrustPreference("analytics_enabled", !analyticsEnabled)}
              className={`relative h-6 w-11 rounded-full transition ${
                analyticsEnabled ? "bg-accent" : "bg-stone-200"
              }`}
            >
              <span
                className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition ${
                  analyticsEnabled ? "left-[22px]" : "left-0.5"
                }`}
              />
            </button>
          </SettingRow>

        </section>

        <section className="mt-6 rounded-2xl border border-border bg-surface-raised/40 px-5">
          <SettingRow label="Launch access" description="Create single-use invites for controlled early usage">
            <Button variant="outline" size="sm" onClick={createInvite}>
              Create invite
            </Button>
          </SettingRow>
          {inviteCode && (
            <div className="flex items-center gap-2 border-b border-border py-4 text-sm">
              <code className="flex-1 rounded-lg bg-surface px-3 py-2 text-accent">{inviteCode}</code>
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(inviteCode)}
                className="rounded-lg p-2 text-muted hover:bg-stone-50 hover:text-stone-950"
                aria-label="Copy invite"
              >
                <Copy className="h-4 w-4" />
              </button>
            </div>
          )}
          <SettingRow label="Usefulness metrics" description="Last 30 days, focused on retention and continuity">
            <span className="text-xs text-muted">
              {metrics ? `${metrics.daily_active_days} active days` : "Loading"}
            </span>
          </SettingRow>
          {metrics && (
            <div className="grid gap-3 py-4 text-sm sm:grid-cols-3">
              <Metric label="Messages" value={metrics.messages_sent} />
              <Metric label="Threads" value={metrics.conversations_started} />
              <Metric label="Memory signals" value={metrics.memory_events} />
              <Metric label="Projects" value={metrics.project_events} />
              <Metric label="Tasks" value={metrics.task_events} />
              <Metric label="Restorations" value={metrics.restoration_actions} />
              <Metric label="Avg response" value={metrics.average_response_rating ?? "n/a"} />
            </div>
          )}
        </section>

        <section className="mt-6 rounded-2xl border border-border bg-surface-raised/40 px-5">
          <SettingRow label="Memory control" description="Edit or remove context that Synzept should not rely on">
            <span className="text-xs text-muted">{memories.length} memories</span>
          </SettingRow>
          <div className="max-h-[26rem] space-y-3 overflow-y-auto py-4">
            {memories.length === 0 && <p className="text-sm text-muted">No stored memories yet.</p>}
            {memories.map((memory) => (
              <MemoryEditor key={memory.id} memory={memory} onSave={updateMemory} onRemove={removeMemory} />
            ))}
          </div>
        </section>

        <section className="mt-6 rounded-2xl border border-border bg-surface-raised/40 px-5">
          <SettingRow label="Support and FAQ" description="Quick recovery guidance for early users">
            <span className="text-xs text-muted">Private feedback group: Discord / early user circle</span>
          </SettingRow>
          <div className="space-y-3 py-4 text-sm leading-6 text-muted">
            <p><span className="text-stone-950">Memory feels wrong:</span> edit or remove the memory above, then flag the issue from feedback.</p>
            <p><span className="text-stone-950">Response failed:</span> retry from chat. Your message stays available.</p>
            <p><span className="text-stone-950">Setup feels incomplete:</span> add a note or memory with the missing context.</p>
            <Textarea
              value={feedback}
              onChange={(event) => setFeedback(event.target.value)}
              placeholder="Ask for help or describe friction"
              className="min-h-24"
            />
            <Button size="sm" onClick={sendSupport} disabled={!feedback.trim()}>
              <Check className="mr-1.5 h-4 w-4" />
              Send to support
            </Button>
          </div>
        </section>

        <div className="mt-8">
          <Button variant="outline" onClick={handleLogout} className="text-red-300 hover:text-red-200">
            Sign out
          </Button>
        </div>

        <section className="mt-6 rounded-2xl border border-border bg-surface-raised/40 px-5">
          <SettingRow
            label="Delete account"
            description="Permanently remove your profile, conversations, projects, tasks, notes, memories, and related workspace data."
          >
            <Button variant="outline" size="sm" onClick={() => setDeleteOpen(true)} className="text-stone-700">
              Delete account
            </Button>
          </SettingRow>
        </section>
      </div>

      {deleteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-stone-950/20 px-4">
          <div className="w-full max-w-lg rounded-xl border border-border bg-white p-6 shadow-panel">
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
                className="rounded-lg p-2 text-muted hover:bg-stone-50 hover:text-stone-950"
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

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl border border-border bg-surface px-3 py-2">
      <p className="text-[11px] text-muted">{label}</p>
      <p className="mt-1 text-base font-semibold text-stone-950">{value}</p>
    </div>
  );
}

function ThemeOption({
  label,
  icon,
  active,
  onClick,
}: {
  label: string;
  icon: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`inline-flex min-w-20 items-center justify-center gap-1.5 rounded-md px-3 text-xs font-medium transition ${
        active ? "bg-white text-stone-950 shadow-soft" : "text-muted hover:text-stone-950"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(new Error("Synzept could not read that image."));
    reader.readAsDataURL(file);
  });
}

function MemoryEditor({
  memory,
  onSave,
  onRemove,
}: {
  memory: Memory;
  onSave: (memory: Memory, content: string) => Promise<void>;
  onRemove: (id: string) => Promise<void>;
}) {
  const [content, setContent] = useState(memory.content);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      await onSave(memory, content);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-3">
      <Textarea value={content} onChange={(event) => setContent(event.target.value)} className="min-h-20 text-sm" />
      <div className="mt-2 flex items-center justify-between gap-2">
        <span className="text-[11px] text-muted">{memory.category}</span>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" onClick={save} disabled={saving || content.trim() === memory.content}>
            Save
          </Button>
          <button
            type="button"
            onClick={() => onRemove(memory.id)}
            className="rounded-lg p-2 text-muted hover:bg-stone-50 hover:text-red-300"
            aria-label="Remove memory"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
