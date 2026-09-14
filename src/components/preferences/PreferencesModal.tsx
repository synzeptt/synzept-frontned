"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { AlertCircle, CheckCircle2, Link as LinkIcon, Loader2, RefreshCw, User, X } from "lucide-react";
import { Avatar } from "@/components/ui/avatar";
import { UpgradePlanExperience } from "@/components/pro/pro-upgrade-modal";
import { api } from "@/lib/api";
import { useAuthStore } from "@/stores/auth";
import { useConnectedAppsStore } from "@/stores/connected-apps";

export const PREFERENCES_OPEN_EVENT = "synzept:open-preferences";

export type PreferencesOpenOptions = {
  returnToPrevious?: boolean;
};

type ToastTone = "success" | "error" | "info";

type ToastState = {
  message: string;
  tone: ToastTone;
} | null;

type ConnectedProviderDefinition = {
  id: string;
  label: string;
  provider: string;
  logo: string;
  description: string;
  available: boolean;
  fallbackProviders?: string[];
};

type ConnectedProviderGroup = {
  title: string;
  providers: ConnectedProviderDefinition[];
};

const connectedAppGroups: ConnectedProviderGroup[] = [
  {
    title: "Google",
    providers: [
      { id: "gmail", label: "Gmail", provider: "google_gmail", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M10 14h28v20H10z" fill="#ea4335"/><path d="M10 14l14 12 14-12" fill="#34a853"/><path d="M38 34l-10-8-4 3-4-3-10 8" fill="#4285f4"/><path d="M10 14v20l10-8" fill="#fbbc04"/><path d="M38 14v20L28 26" fill="#1a73e8"/></svg>`, description: "Email and inbox context", available: true },
      { id: "google-calendar", label: "Google Calendar", provider: "google_calendar", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="9" y="11" width="30" height="28" rx="4" fill="#4285f4"/><rect x="9" y="11" width="30" height="8" rx="4" fill="#1a73e8"/><rect x="15" y="21" width="4" height="4" rx="1" fill="#fff"/><rect x="22" y="21" width="4" height="4" rx="1" fill="#fff"/><rect x="29" y="21" width="4" height="4" rx="1" fill="#fff"/><rect x="15" y="28" width="4" height="4" rx="1" fill="#fff"/><rect x="22" y="28" width="4" height="4" rx="1" fill="#fff"/></svg>`, description: "Schedule and availability", available: true },
      { id: "google-drive", label: "Google Drive", provider: "google_drive", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M16 8h8l8 14H24z" fill="#fbbc04"/><path d="M8 30l8-14h16l-8 14z" fill="#4285f4"/><path d="M24 30l8 14H8l8-14z" fill="#34a853"/></svg>`, description: "Files and project context", available: true },
      { id: "google-docs", label: "Google Docs", provider: "google_docs", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="12" y="8" width="24" height="32" rx="4" fill="#4285f4"/><rect x="16" y="14" width="16" height="2.5" rx="1" fill="#fff"/><rect x="16" y="20" width="12" height="2.5" rx="1" fill="#fff"/><rect x="16" y="26" width="10" height="2.5" rx="1" fill="#fff"/></svg>`, description: "Docs and collaborative writing", available: false },
      { id: "google-sheets", label: "Google Sheets", provider: "google_sheets", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="12" y="8" width="24" height="32" rx="4" fill="#34a853"/><rect x="16" y="14" width="16" height="2.5" rx="1" fill="#fff"/><rect x="16" y="20" width="16" height="2.5" rx="1" fill="#fff"/><rect x="16" y="26" width="10" height="2.5" rx="1" fill="#fff"/></svg>`, description: "Spreadsheet planning and metrics", available: false },
      { id: "google-meet", label: "Google Meet", provider: "google_meet", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="10" y="14" width="20" height="20" rx="4" fill="#ea4335"/><path d="M32 18l6-4v16l-6-4" fill="#4285f4"/><circle cx="18" cy="24" r="4" fill="#fff"/></svg>`, description: "Video meetings and calls", available: false },
      { id: "google-tasks", label: "Google Tasks", provider: "google_tasks", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="12" y="10" width="24" height="28" rx="4" fill="#fbbc04"/><path d="M18 24l4 4 8-8" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>`, description: "Priority lists and task capture", available: false },
    ],
  },
  {
    title: "Microsoft",
    providers: [
      { id: "outlook", label: "Outlook", provider: "microsoft_outlook_mail", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M10 12h20l8 4v20l-8 4H10z" fill="#0078d4"/><path d="M10 12l14 12 14-12-14 12-14-12z" fill="#ffffff" opacity="0.95"/><path d="M10 32l14-8 14 8" fill="#50e6ff"/></svg>`, description: "Microsoft email and follow-ups", available: true, fallbackProviders: ["microsoft_outlook_mail"] },
      { id: "microsoft-calendar", label: "Microsoft Calendar", provider: "microsoft_outlook_calendar", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="9" y="11" width="30" height="28" rx="4" fill="#0078d4"/><rect x="9" y="11" width="30" height="8" rx="4" fill="#005a9c"/><rect x="15" y="21" width="4" height="4" rx="1" fill="#fff"/><rect x="22" y="21" width="4" height="4" rx="1" fill="#fff"/><rect x="29" y="21" width="4" height="4" rx="1" fill="#fff"/></svg>`, description: "Calendar and meeting context", available: true, fallbackProviders: ["microsoft_outlook_calendar"] },
      { id: "onedrive", label: "OneDrive", provider: "microsoft_onedrive", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M16 16c-2.2 0-4 1.8-4 4l1 6h22l1-6c0-2.2-1.8-4-4-4H16z" fill="#0078d4"/><path d="M14 28h20l2 6H12z" fill="#50e6ff"/></svg>`, description: "Storage and document context", available: true, fallbackProviders: ["microsoft_onedrive"] },
      { id: "teams", label: "Microsoft Teams", provider: "microsoft_teams", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="11" y="12" width="14" height="18" rx="3" fill="#6264a7"/><path d="M27 18h7a3 3 0 013 3v8a3 3 0 01-3 3h-4" stroke="#6264a7" stroke-width="3" stroke-linecap="round" fill="none"/><circle cx="18" cy="24" r="4" fill="#fff"/></svg>`, description: "Teams chat and meetings", available: true, fallbackProviders: ["microsoft_teams"] },
    ],
  },
  {
    title: "Communication",
    providers: [
      { id: "slack", label: "Slack", provider: "slack", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="17" y="8" width="6" height="14" rx="3" fill="#4a154b"/><rect x="25" y="8" width="6" height="14" rx="3" fill="#4a154b"/><rect x="17" y="26" width="6" height="14" rx="3" fill="#4a154b"/><rect x="25" y="26" width="6" height="14" rx="3" fill="#4a154b"/><path d="M11 17c0-2.2 1.8-4 4-4h2v4h-2a4 4 0 00-4 4v2h-4v-2a4 4 0 014-4z" fill="#4a154b"/><path d="M31 17c0-2.2 1.8-4 4-4h2v4h-2a4 4 0 00-4 4v2h-4v-2a4 4 0 014-4z" fill="#4a154b"/></svg>`, description: "Team conversations and blockers", available: true },
      { id: "discord", label: "Discord", provider: "discord", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#5865f2"/><circle cx="18" cy="22" r="4" fill="#fff"/><circle cx="30" cy="22" r="4" fill="#fff"/><path d="M16 32c3-2 5-2 6-2s3 0 6 2" stroke="#fff" stroke-width="3" stroke-linecap="round"/></svg>`, description: "Community and collaboration context", available: false },
    ],
  },
  {
    title: "Productivity",
    providers: [
      { id: "notion", label: "Notion", provider: "notion", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M14 10h20l-3 3H14z" fill="#000"/><path d="M14 16h16l-2 2H14z" fill="#000"/><rect x="14" y="20" width="16" height="18" rx="3" fill="#000"/></svg>`, description: "Docs, planning, and knowledge", available: true },
      { id: "trello", label: "Trello", provider: "trello", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="13" y="10" width="8" height="20" rx="2" fill="#0079bf"/><rect x="27" y="10" width="8" height="12" rx="2" fill="#0079bf"/></svg>`, description: "Kanban boards and workstreams", available: false },
      { id: "asana", label: "Asana", provider: "asana", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><circle cx="18" cy="24" r="6" fill="#f06a6a"/><circle cx="30" cy="18" r="5" fill="#f06a6a"/><circle cx="30" cy="30" r="5" fill="#f06a6a"/></svg>`, description: "Work tracking and delivery", available: false },
      { id: "clickup", label: "ClickUp", provider: "clickup", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M24 12l10 10-4 4-6-6-6 6-4-4z" fill="#7b68ee"/><path d="M24 30l-10-10 4-4 6 6 6-6 4 4z" fill="#7b68ee"/></svg>`, description: "Task management and planning", available: false },
      { id: "linear", label: "Linear", provider: "linear", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M14 18h20v12H14z" fill="#5e6ad2"/><path d="M18 12h12v24H18z" fill="#5e6ad2"/></svg>`, description: "Issue tracking and product work", available: false },
      { id: "jira", label: "Jira", provider: "jira", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M14 12h20v24H14z" fill="#2684ff"/><path d="M18 16l8 8-8 8" stroke="#fff" stroke-width="3" stroke-linecap="round" fill="none"/></svg>`, description: "Engineering and project tracking", available: false },
    ],
  },
  {
    title: "Development",
    providers: [
      { id: "github", label: "GitHub", provider: "github", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M24 10c-7.7 0-14 6.3-14 14 0 6.2 4 11.5 9.6 13.4.7.1 1-.3 1-.7v-2.3c-3.9.8-4.7-1.7-4.7-1.7-.6-1.6-1.5-2-1.5-2-1.3-.9.1-.9.1-.9 1.4.1 2.2 1.5 2.2 1.5 1.3 2.2 3.4 1.6 4.2 1.2.1-.9.5-1.6 1-2-3.1-.4-6.4-1.6-6.4-7 0-1.6.5-2.8 1.5-3.8-.1-.4-.7-1.8.1-3.7 0 0 1.2-.4 4 1.5 1.2-.3 2.5-.5 3.8-.5 1.3 0 2.6.2 3.8.5 2.8-1.9 4-1.5 4-1.5.8 2 .2 3.3.1 3.7.9 1 1.5 2.2 1.5 3.8 0 5.4-3.3 6.6-6.5 7 .5.4 1 1.2 1 2.4v3.6c0 .4.3.8 1 .7A14.01 14.01 0 0038 24c0-7.7-6.3-14-14-14z" fill="#171515"/></svg>`, description: "Code, PRs, and engineering context", available: true },
      { id: "gitlab", label: "GitLab", provider: "gitlab", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M24 12l6 14h-12z" fill="#fc6d26"/><path d="M24 12l-6 14h12z" fill="#e24329"/><path d="M14 26l10 10 10-10" fill="#fca326"/></svg>`, description: "Repository and delivery insights", available: false },
    ],
  },
  {
    title: "Storage",
    providers: [
      { id: "dropbox", label: "Dropbox", provider: "dropbox", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M16 12l8 5-8 5-8-5 8-5z" fill="#0061ff"/><path d="M32 12l8 5-8 5-8-5 8-5z" fill="#0061ff"/><path d="M16 22l8 5 8-5" fill="#0061ff"/><path d="M16 32l8-5 8 5-8 5-8-5z" fill="#0061ff"/></svg>`, description: "File storage and document trails", available: false },
    ],
  },
  {
    title: "Meetings",
    providers: [
      { id: "zoom", label: "Zoom", provider: "zoom", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M14 16h12c2.2 0 4 1.8 4 4v8c0 2.2-1.8 4-4 4H14z" fill="#0b5cff"/><path d="M30 20l8-4v16l-8-4" fill="#0b5cff"/></svg>`, description: "Video meetings and agendas", available: false },
    ],
  },
  {
    title: "Automation",
    providers: [
      { id: "zapier", label: "Zapier", provider: "zapier", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M15 15h18v18H15z" fill="#ff4f00"/><path d="M20 20h8v8h-8z" fill="#fff"/></svg>`, description: "Workflow automation and triggers", available: false },
      { id: "make", label: "Make (Integromat)", provider: "make", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><rect x="12" y="12" width="24" height="24" rx="6" fill="#ff5a5f"/><circle cx="24" cy="24" r="6" fill="#fff"/></svg>`, description: "Scenario-based automations", available: false },
    ],
  },
  {
    title: "AI",
    providers: [
      { id: "openai", label: "OpenAI", provider: "openai", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M24 10a10 10 0 00-9.8 12h4.2a5.8 5.8 0 0111.2 0h4.2A10 10 0 0024 10z" fill="#10a37f"/><path d="M18 22h12v6H18z" fill="#10a37f"/></svg>`, description: "AI model and prompt context", available: false },
      { id: "anthropic", label: "Anthropic", provider: "anthropic", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M16 14h16v20H16z" fill="#7f5af0"/><path d="M18 18h12v4H18z" fill="#fff"/><path d="M18 24h8v4h-8z" fill="#fff"/></svg>`, description: "Claude and AI workflow context", available: false },
    ],
  },
  {
    title: "CRM",
    providers: [
      { id: "hubspot", label: "HubSpot", provider: "hubspot", logo: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="12" fill="#fff"/><path d="M16 16c0-2.2 1.8-4 4-4h8c2.2 0 4 1.8 4 4v2h-16v-2z" fill="#ff5a5f"/><circle cx="18" cy="28" r="4" fill="#ff5a5f"/><circle cx="30" cy="28" r="4" fill="#ff5a5f"/></svg>`, description: "Customer relationship context", available: false },
    ],
  },
];

export function openPreferencesModal(options?: PreferencesOpenOptions) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent(PREFERENCES_OPEN_EVENT, { detail: options ?? {} }));
}

function NavItem({ active, onClick, icon, children }: { active?: boolean; onClick?: () => void; icon: ReactNode; children: ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full cursor-pointer items-center gap-3 rounded-2xl px-3 py-2.5 text-[13px] font-medium leading-5 transition-all duration-200 ${
        active ? "bg-stone-900 text-white shadow-[0_8px_20px_rgba(15,23,42,0.10)]" : "text-stone-600 hover:bg-stone-100 hover:text-stone-900"
      }`}
    >
      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl ${active ? "bg-white/10 text-white" : "bg-stone-100 text-stone-500"}`}>{icon}</span>
      <span className="truncate">{children}</span>
    </button>
  );
}

function Row({ label, value, action }: { label: string; value: string | ReactNode; action?: { label: string; onClick?: () => void; variant?: "primary" | "outline"; disabled?: boolean; comingSoon?: boolean } }) {
  return (
    <div className="flex min-h-[68px] items-center justify-between gap-4 rounded-[18px] border border-stone-200/80 bg-[#fcfbf8] px-5 py-4 shadow-[0_1px_0_rgba(15,23,42,0.02)] transition-all duration-200 hover:-translate-y-0.5 hover:bg-white">
      <div className="min-w-0">
        <div className="text-[13px] font-semibold tracking-[-0.01em] text-stone-900">{label}</div>
        <div className="mt-1 text-sm text-stone-500">{value}</div>
      </div>
      <div>
        {action ? (
          <button
            type="button"
            onClick={action.onClick}
            disabled={action.disabled}
            className={`inline-flex h-9 cursor-pointer items-center justify-center rounded-full px-3.5 text-[13px] font-medium transition-all duration-200 disabled:cursor-not-allowed ${
              action.variant === "primary" ? "bg-stone-900 text-white hover:bg-stone-800" : "border border-stone-200 bg-white text-stone-700 hover:border-stone-300 hover:bg-stone-50"
            } ${action.comingSoon ? "opacity-80" : ""}`}
          >
            {action.comingSoon ? "Coming Soon" : action.label}
          </button>
        ) : null}
      </div>
    </div>
  );
}

function Toast({ toast, onDismiss }: { toast: ToastState; onDismiss: () => void }) {
  if (!toast) return null;

  const toneClass = toast.tone === "success" ? "border-emerald-200 bg-emerald-50 text-emerald-800" : toast.tone === "error" ? "border-rose-200 bg-rose-50 text-rose-800" : "border-stone-200 bg-white text-stone-700";
  const Icon = toast.tone === "success" ? CheckCircle2 : AlertCircle;

  return (
    <div className={`fixed bottom-4 right-4 z-[60] flex max-w-sm items-start gap-3 rounded-2xl border px-4 py-3 shadow-[0_16px_40px_rgba(15,23,42,0.14)] ${toneClass}`} role="status">
      <Icon className="mt-0.5 h-4 w-4 shrink-0" />
      <p className="text-sm font-medium">{toast.message}</p>
      <button type="button" onClick={onDismiss} className="ml-2 rounded-full p-1 text-current transition hover:bg-black/5" aria-label="Dismiss notification">
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}

export function PreferencesModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const { apps, refresh, isLoading: appsLoading } = useConnectedAppsStore();
  const [active, setActive] = useState<string>("profile");
  const [toast, setToast] = useState<ToastState>(null);
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isChangingPhoto, setIsChangingPhoto] = useState(false);
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const [isRefreshingApps, setIsRefreshingApps] = useState(false);
  const [busyProvider, setBusyProvider] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"connect" | "disconnect" | null>(null);
  const [comingSoonFeature, setComingSoonFeature] = useState<string | null>(null);
  const [comingSoonMessage, setComingSoonMessage] = useState<string | null>(null);
  const [draftName, setDraftName] = useState(user?.display_name || "");
  const [isEditingName, setIsEditingName] = useState(false);
  const [showPasswordEditor, setShowPasswordEditor] = useState(false);
  const [showEmailEditor, setShowEmailEditor] = useState(false);
  const [emailPreferences, setEmailPreferences] = useState({ product: true, security: true, billing: true });
  const [passwordDraft, setPasswordDraft] = useState("");
  const [confirmPasswordDraft, setConfirmPasswordDraft] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;

    previouslyFocusedRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;

    const previousBodyOverflow = document.body.style.overflow;
    const previousHtmlOverflow = document.documentElement.style.overflow;
    document.body.style.overflow = "hidden";
    document.documentElement.style.overflow = "hidden";

    const focusTarget = dialogRef.current?.querySelector<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
    requestAnimationFrame(() => {
      (focusTarget ?? dialogRef.current)?.focus();
    });

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab" || !dialogRef.current) return;

      const focusable = dialogRef.current.querySelectorAll<HTMLElement>("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
      if (!focusable.length) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousBodyOverflow;
      document.documentElement.style.overflow = previousHtmlOverflow;
      previouslyFocusedRef.current?.focus();
    };
  }, [open, onClose]);

  useEffect(() => {
    setDraftName(user?.display_name || "");
  }, [user?.display_name]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 3200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const connectedProviders = useMemo<ConnectedProviderDefinition[]>(() => [
    { id: "google", label: "Google", provider: "google", logo: "/brands/google.svg", description: "Google Workspace services", available: false },
    { id: "gmail", label: "Gmail", provider: "google_gmail", logo: "/brands/gmail.svg", description: "Email and inbox context", available: true },
    { id: "google-calendar", label: "Google Calendar", provider: "google_calendar", logo: "/brands/google-calendar.svg", description: "Schedule and availability", available: true },
    { id: "google-drive", label: "Google Drive", provider: "google_drive", logo: "/brands/google-drive.svg", description: "Project and file context", available: true },
    { id: "github", label: "GitHub", provider: "github", logo: "/brands/github.svg", description: "Development and review context", available: true },
    { id: "slack", label: "Slack", provider: "slack", logo: "/brands/slack.svg", description: "Team communication context", available: true },
    { id: "notion", label: "Notion", provider: "notion", logo: "/brands/notion.svg", description: "Docs and planning context", available: true },
    { id: "outlook", label: "Outlook", provider: "microsoft_outlook_mail", logo: "/brands/outlook-mail.svg", description: "Microsoft email context", available: true, fallbackProviders: ["microsoft_outlook_mail", "microsoft_outlook_calendar"] },
  ], []);

  const providerState = useMemo(() => connectedProviders.map((provider) => {
    const app = provider.fallbackProviders?.map((item) => apps[item]).find(Boolean) ?? apps[provider.provider] ?? null;
    const status = busyProvider === provider.provider ? "connecting" : app?.status || "not_connected";
    const connected = Boolean(app?.connected) && status !== "permission_revoked" && status !== "error";
    const isBusy = busyProvider === provider.provider;
    const actionLabel = isBusy ? "Working…" : connected ? "Manage" : status === "error" || status === "permission_revoked" ? "Retry" : provider.available ? "Connect" : "Coming Soon";
    return { ...provider, app, status, connected, isBusy, actionLabel };
  }), [apps, busyProvider, connectedProviders]);

  const showToast = (message: string, tone: ToastTone = "success") => setToast({ message, tone });
  const openComingSoonDialog = (feature: string) => {
    setComingSoonFeature(feature);
    setComingSoonMessage(`The ${feature.toLowerCase()} feature is under development and will arrive soon.`);
    showToast(`${feature} is coming soon.`, "info");
  };
  const closeComingSoonDialog = () => {
    setComingSoonFeature(null);
    setComingSoonMessage(null);
  };

  const handleComingSoon = (feature: string) => {
    openComingSoonDialog(feature);
  };

  const handleSaveName = async () => {
    const trimmed = draftName.trim();
    if (!trimmed) {
      showToast("Please enter a name before saving.", "error");
      return;
    }

    setIsSavingProfile(true);
    try {
      await api.updateProfile({ display_name: trimmed });
      await useAuthStore.getState().refreshUser();
      setIsEditingName(false);
      showToast("Your profile name was updated.", "success");
    } catch {
      showToast("We couldn’t update your profile right now.", "error");
    } finally {
      setIsSavingProfile(false);
    }
  };

  const handleChangePhoto = async () => {
    setIsChangingPhoto(true);
    try {
      const initials = (user?.display_name || user?.email || "SU").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "SU";
      const palette = ["#1c1917", "#58705f", "#8c6f3d", "#4f46e5"];
      const color = palette[(initials.charCodeAt(0) + initials.length) % palette.length];
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256" viewBox="0 0 256 256"><rect width="256" height="256" rx="48" fill="${color}" /><circle cx="128" cy="104" r="44" fill="rgba(255,255,255,0.86)" /><path d="M64 220c12-34 42-52 64-52s52 18 64 52" fill="rgba(255,255,255,0.78)" /><text x="128" y="232" text-anchor="middle" font-size="44" font-family="Inter, Arial, sans-serif" fill="white">${initials}</text></svg>`;
      const avatarUrl = `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
      await useAuthStore.getState().updateAvatar(avatarUrl);
      showToast("Your profile photo was updated.", "success");
    } catch {
      showToast("We couldn’t update your profile photo right now.", "error");
    } finally {
      setIsChangingPhoto(false);
    }
  };

  const handleSaveEmailPreferences = () => {
    showToast("Email preferences updated locally for this session.", "success");
    setShowEmailEditor(false);
  };

  const handleSavePassword = () => {
    if (!passwordDraft || passwordDraft.length < 8) {
      showToast("Use at least 8 characters for the new password.", "error");
      return;
    }
    if (passwordDraft !== confirmPasswordDraft) {
      showToast("Passwords do not match.", "error");
      return;
    }
    showToast("Password changes are being prepared and will be available soon.", "info");
    setShowPasswordEditor(false);
    setPasswordDraft("");
    setConfirmPasswordDraft("");
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation.toLowerCase() !== "delete my account") {
      showToast("Type 'delete my account' to confirm account deletion.", "error");
      return;
    }

    setIsDeletingAccount(true);
    try {
      await useAuthStore.getState().deleteAccount(deletePassword || undefined, deleteConfirmation);
      onClose();
    } catch {
      showToast("We couldn’t delete your account right now.", "error");
    } finally {
      setIsDeletingAccount(false);
    }
  };

  const handleRefreshApps = async () => {
    setIsRefreshingApps(true);
    try {
      await refresh(true);
      showToast("Connected app status refreshed.", "success");
    } catch {
      showToast("We couldn’t refresh connected apps right now.", "error");
    } finally {
      setIsRefreshingApps(false);
    }
  };

  const handleConnectedProviderAction = async (provider: ConnectedProviderDefinition, connected: boolean) => {
    if (!provider.available) {
      openComingSoonDialog(provider.label);
      return;
    }

    if (busyProvider) return;
    setBusyProvider(provider.provider);
    setBusyAction(connected ? "disconnect" : "connect");

    try {
      if (connected) {
        await api.disconnectGoogleWorkspaceService(provider.provider);
        await refresh(true);
        showToast(`${provider.label} disconnected.`, "success");
      } else {
        const response = await api.connectGoogleWorkspaceService(provider.provider);
        if (response.authorizationUrl) {
          if (typeof window !== "undefined") {
            window.open(response.authorizationUrl, "_blank", "noopener,noreferrer");
          }
          showToast(`Connecting ${provider.label}. Finish the sign-in in the new tab.`, "info");
        } else {
          throw new Error("Missing authorization URL");
        }
      }
    } catch {
      showToast(`We couldn’t update ${provider.label} right now.`, "error");
    } finally {
      setBusyProvider(null);
      setBusyAction(null);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-0 sm:p-4">
      <div className="absolute inset-0 bg-stone-950/50 backdrop-blur-[3px]" onClick={onClose} />

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="preferences-title"
        aria-describedby="preferences-description"
        tabIndex={-1}
        className="relative z-10 flex h-[100dvh] w-full flex-col overflow-hidden border border-stone-200/80 bg-[#fcfbf8] shadow-[0_24px_80px_rgba(15,23,42,0.24)] sm:h-[min(90dvh,780px)] sm:w-[min(96vw,1240px)] sm:rounded-[28px]"
      >
        <div className="flex h-full flex-col sm:flex-row">
          <aside className="w-full border-b border-stone-200/80 bg-white/70 p-5 sm:w-[260px] sm:shrink-0 sm:border-b-0 sm:border-r sm:p-6">
            <div className="mb-7">
              <h3 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-stone-400">Settings</h3>
              <div className="mt-3 space-y-1.5">
                <NavItem active={active === "profile"} onClick={() => setActive("profile")} icon={<User className="h-4 w-4" />}>Profile</NavItem>
                <NavItem active={active === "connected"} onClick={() => setActive("connected")} icon={<LinkIcon className="h-4 w-4" />}>Connected accounts</NavItem>
              </div>
            </div>
          </aside>

          <main className="flex-1 p-4 sm:p-6">
            <div className="sticky top-0 z-20 flex items-start justify-between gap-4 border-b border-stone-200/80 bg-[#fcfbf8] pb-5">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-stone-400">Settings</p>
                <h2 id="preferences-title" className="mt-2 text-2xl font-semibold tracking-[-0.02em] text-stone-900">{active === "profile" ? "Profile" : "Connected accounts"}</h2>
                <p id="preferences-description" className="mt-1 text-sm text-stone-500">{active === "profile" ? "Keep your identity and workspace profile aligned with how you work." : "Review the accounts that currently power your context."}</p>
              </div>
              <div className="flex items-center gap-3">
                <button type="button" onClick={onClose} aria-label="Close settings" className="inline-flex h-9 w-9 cursor-pointer items-center justify-center rounded-full border border-stone-200 bg-white text-stone-700 transition hover:bg-stone-50"> <X className="h-4 w-4" /> </button>
              </div>
            </div>

            <div className="mt-6 h-[calc(100%-96px)] space-y-6 overflow-y-auto pr-1 sm:pr-3">
              {active === "profile" && (
                <section className="space-y-4">
                  <div className="flex items-center gap-4 rounded-[24px] border border-stone-200/80 bg-white p-5 shadow-[0_8px_24px_rgba(15,23,42,0.04)]">
                    <Avatar name={user?.display_name || user?.email} email={user?.email} size="lg" />
                    <div className="min-w-0">
                      <div className="text-lg font-semibold tracking-[-0.01em] text-stone-900">{user?.display_name || "Synzept User"}</div>
                      <div className="mt-1 text-sm text-stone-500">{user?.email || "you@domain.com"}</div>
                      <div className="mt-2 text-sm text-stone-500">{user?.plan_type === "pro" || user?.is_pro ? "Pro workspace" : "Free workspace"}</div>
                    </div>
                    <button type="button" onClick={handleChangePhoto} disabled={isChangingPhoto} className="ml-auto inline-flex h-9 cursor-pointer items-center justify-center rounded-full border border-stone-200 bg-stone-50 px-3 text-[13px] font-medium text-stone-700 transition hover:bg-stone-100 disabled:cursor-not-allowed disabled:opacity-60">
                      {isChangingPhoto ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Change photo
                    </button>
                  </div>

                  <div className="rounded-[18px] border border-stone-200/80 bg-[#fcfbf8] px-5 py-4 shadow-[0_1px_0_rgba(15,23,42,0.02)]">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="text-[13px] font-semibold tracking-[-0.01em] text-stone-900">Display name</div>
                        <div className="mt-1 text-sm text-stone-500">{user?.display_name || "—"}</div>
                      </div>
                      <button type="button" onClick={() => setIsEditingName((value) => !value)} className="inline-flex h-9 cursor-pointer items-center justify-center rounded-full border border-stone-200 bg-white px-3.5 text-[13px] font-medium text-stone-700 transition hover:border-stone-300 hover:bg-stone-50">
                        {isEditingName ? "Cancel" : "Edit"}
                      </button>
                    </div>
                    {isEditingName ? (
                      <div className="mt-4 space-y-3 rounded-2xl border border-stone-200 bg-white p-4">
                        <input value={draftName} onChange={(event) => setDraftName(event.target.value)} className="w-full rounded-xl border border-stone-200 px-3 py-2 text-sm outline-none focus:border-stone-400" placeholder="Enter your full name" />
                        <div className="flex items-center gap-2">
                          <button type="button" onClick={handleSaveName} disabled={isSavingProfile} className="inline-flex h-9 cursor-pointer items-center justify-center rounded-full bg-stone-900 px-3.5 text-[13px] font-medium text-white transition hover:bg-stone-800 disabled:cursor-not-allowed disabled:opacity-60">
                            {isSavingProfile ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                            Save changes
                          </button>
                          <button type="button" onClick={() => { setIsEditingName(false); setDraftName(user?.display_name || ""); }} className="inline-flex h-9 cursor-pointer items-center justify-center rounded-full border border-stone-200 bg-white px-3.5 text-[13px] font-medium text-stone-700 transition hover:border-stone-300 hover:bg-stone-50">
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <Row label="Email" value={user?.email || "—"} action={{ label: "Manage", variant: "outline", onClick: () => openComingSoonDialog("email preferences") }} />
                  <Row label="Workspace plan" value={user?.plan_type === "pro" || user?.is_pro ? "Pro" : "Free"} action={{ label: user?.plan_type === "pro" || user?.is_pro ? "Manage" : "Upgrade", variant: "outline", onClick: () => openComingSoonDialog("subscription management") }} />
                </section>
              )}

              {active === "connected" && (
                <section className="space-y-4">
                  <div className="flex items-center justify-between rounded-[20px] border border-stone-200/80 bg-white px-4 py-3 shadow-[0_6px_18px_rgba(15,23,42,0.04)]">
                    <div>
                      <div className="text-sm font-semibold text-stone-900">Connected services</div>
                      <div className="mt-1 text-sm text-stone-500">{appsLoading ? "Refreshing your connected apps…" : "Review your current integrations and what is planned next."}</div>
                    </div>
                    <button type="button" onClick={handleRefreshApps} disabled={isRefreshingApps} className="inline-flex h-9 cursor-pointer items-center justify-center rounded-full border border-stone-200 bg-stone-50 px-3.5 text-[13px] font-medium text-stone-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-60">
                      {isRefreshingApps ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
                      Refresh
                    </button>
                  </div>

                  {connectedAppGroups.map((group) => (
                    <div key={group.title} className="space-y-2">
                      <div className="px-1 pt-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-stone-400">{group.title}</div>
                      <div className="space-y-2">
                        {group.providers.map((provider) => {
                          const app = provider.fallbackProviders?.map((item) => apps[item]).find(Boolean) ?? apps[provider.provider] ?? null;
                          const status = busyProvider === provider.provider ? "connecting" : app?.status || "not_connected";
                          const connected = Boolean(app?.connected) && status !== "permission_revoked" && status !== "error";
                          const isBusy = busyProvider === provider.provider;
                          const statusLabel = connected ? "Connected" : status === "error" || status === "permission_revoked" ? "Needs attention" : status === "connecting" ? "Connecting" : status === "syncing" ? "Syncing" : provider.available ? "Not connected" : "Coming Soon";
                          const actionLabel = isBusy ? "Working…" : connected ? "Manage" : status === "error" || status === "permission_revoked" ? "Retry" : provider.available ? "Connect" : "Coming Soon";
                          return (
                            <div key={provider.id} className="flex items-center justify-between gap-4 rounded-[18px] border border-stone-200/80 bg-[#fcfbf8] px-4 py-3.5 shadow-[0_1px_0_rgba(15,23,42,0.02)] transition-all duration-200 hover:-translate-y-0.5 hover:border-stone-300 hover:bg-white">
                              <div className="flex min-w-0 items-center gap-3">
                                <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl border border-stone-200 bg-white p-2 shadow-sm">
                                  <Image src={`data:image/svg+xml;utf8,${encodeURIComponent(provider.logo)}`} alt={`${provider.label} logo`} width={24} height={24} className="h-6 w-6 object-contain" />
                                </div>
                                <div className="min-w-0">
                                  <div className="text-sm font-medium text-stone-900">{provider.label}</div>
                                  <div className="mt-1 text-sm text-stone-500">{provider.description}</div>
                                  <div className="mt-1 flex items-center gap-2 text-xs font-medium text-stone-500">
                                    <span className={`rounded-full px-2 py-1 ${connected ? "bg-emerald-50 text-emerald-700" : status === "error" || status === "permission_revoked" ? "bg-rose-50 text-rose-700" : status === "connecting" ? "bg-amber-50 text-amber-700" : provider.available ? "bg-stone-100 text-stone-600" : "bg-stone-100 text-stone-500"}`}>
                                      {statusLabel}
                                    </span>
                                    {app?.lastSyncedAt ? <span>Synced {new Date(app.lastSyncedAt).toLocaleDateString()}</span> : null}
                                  </div>
                                </div>
                              </div>
                              <button type="button" onClick={() => void handleConnectedProviderAction(provider, connected)} disabled={isBusy} className={`inline-flex h-9 cursor-pointer items-center justify-center rounded-full px-3 text-[13px] font-medium transition ${connected ? "border border-stone-200 bg-white text-stone-700 hover:border-stone-300 hover:bg-stone-50" : status === "error" || status === "permission_revoked" ? "bg-amber-600 text-white hover:bg-amber-700" : provider.available ? "bg-stone-900 text-white hover:bg-stone-800" : "border border-stone-200 bg-white text-stone-700 hover:border-stone-300 hover:bg-stone-50"}`}>
                                {isBusy ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                                {actionLabel}
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </section>
              )}


            </div>
          </main>
        </div>
      </div>

      <Toast toast={toast} onDismiss={() => setToast(null)} />
      {comingSoonFeature ? (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-stone-950/30 px-4 py-6 backdrop-blur-sm">
          <div className="relative max-h-[min(720px,calc(100vh-3rem))] w-full max-w-lg overflow-y-auto rounded-[28px] border border-stone-200/80 bg-white px-6 py-6 shadow-[0_32px_90px_rgba(15,23,42,0.25)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-stone-900">Coming soon</p>
                <h3 className="mt-2 text-xl font-semibold tracking-[-0.02em] text-stone-950">{comingSoonFeature}</h3>
              </div>
              <button type="button" onClick={closeComingSoonDialog} aria-label="Close coming soon dialog" className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-stone-200 bg-stone-50 text-stone-700 transition hover:bg-stone-100">
                <X className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-4 text-sm leading-6 text-stone-600">{comingSoonMessage}</p>
            <div className="mt-6 flex justify-end">
              <button type="button" onClick={closeComingSoonDialog} className="inline-flex h-10 items-center justify-center rounded-full border border-stone-200 bg-white px-4 text-sm font-medium text-stone-700 transition hover:border-stone-300 hover:bg-stone-50">
                Got it
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default PreferencesModal;
