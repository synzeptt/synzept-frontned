export type SettingsSectionId = "profile" | "account" | "appearance" | "billing" | "security" | "connected-apps" | "danger-zone";

export type SettingsSection = {
  id: SettingsSectionId;
  label: string;
  description: string;
};

export function getSettingsSections(): SettingsSection[] {
  return [
    { id: "profile", label: "Profile", description: "Your identity, plan, and workspace summary." },
    { id: "account", label: "Account", description: "Email, name, and account controls." },
    { id: "appearance", label: "Appearance", description: "Theme and workspace presentation." },
    { id: "billing", label: "Billing", description: "Pro plan, invoices, and renewal details." },
    { id: "security", label: "Security", description: "Password updates and account safety." },
    { id: "connected-apps", label: "Connected apps", description: "Integrations that enrich your context." },
    { id: "danger-zone", label: "Danger zone", description: "Account deletion and irreversible actions." },
  ];
}
