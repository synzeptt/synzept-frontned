"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2 } from "lucide-react";
import { useConnectedAppsStore } from "@/stores/connected-apps";
import { Page, PageHeader, SettingsRow, SettingsSection } from "@/components/design-system/workspace-primitives";

const serviceMapping: Record<string, string> = {
  google_calendar: "Google Calendar",
  google_gmail: "Gmail",
  google_drive: "Google Drive",
  google_tasks: "Google Tasks",
  microsoft_outlook: "Microsoft Outlook",
  microsoft_teams: "Microsoft Teams",
  microsoft_365: "Microsoft 365",
  slack: "Slack",
  notion: "Notion",
  github: "GitHub",
};

const serviceCategories = [
  {
    category: "Communication",
    services: ["google_gmail", "slack", "microsoft_outlook", "microsoft_teams"],
  },
  {
    category: "Productivity",
    services: ["google_calendar", "google_drive", "google_tasks", "microsoft_365", "notion"],
  },
  {
    category: "Development",
    services: ["github"],
  },
];

export default function ConnectedPage() {
  const { apps, refresh, isLoading } = useConnectedAppsStore();
  const [initialLoad, setInitialLoad] = useState(true);

  useEffect(() => {
    const loadApps = async () => {
      await refresh();
      setInitialLoad(false);
    };
    void loadApps();
  }, [refresh]);

  const getConnectionStatus = (provider: string): boolean => {
    const app = apps[provider];
    return app?.connected === true;
  };

  return (
    <Page>
      <div className="mx-auto max-w-3xl space-y-8 px-5 py-12 sm:px-8 sm:py-16">
        <PageHeader eyebrow="Sources" title="Connected Apps" description="Infrastructure Synzept can use when it is relevant to your request." />

        {initialLoad || isLoading ? (
          <div className="border-y border-[var(--border)] py-12 text-center">
            <Loader2 className="mx-auto mb-4 h-8 w-8 animate-spin text-[var(--text-muted)]" />
            <p className="text-[var(--text-secondary)]">Loading connections...</p>
          </div>
        ) : (
          <div className="space-y-6">
            {serviceCategories.map((category) => (
              <SettingsSection key={category.category} title={category.category} description="Connected integrations in this category.">
                {category.services.map((provider) => {
                  const isConnected = getConnectionStatus(provider);
                  const serviceLabel = serviceMapping[provider] || provider;
                  return (
                    <SettingsRow key={provider} label={serviceLabel} description={isConnected ? "Available to Synzept when relevant" : "Not currently available"}>
                      {isConnected ? <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-[var(--success)]" /><span className="text-sm font-medium text-[var(--text-primary)]">Connected</span></div> : <span className="text-sm font-medium text-[var(--text-muted)]">Connect</span>}
                    </SettingsRow>
                  );
                })}
              </SettingsSection>
            ))}
          </div>
        )}
      </div>
    </Page>
  );
}
