"use client";

import { Button } from "@/components/ui/button";
import { useSettingsStore } from "@/stores/settings-store";

const TONES = [
  { value: "balanced" as const, label: "Balanced", detail: "Clear and neutral" },
  { value: "precise" as const, label: "Precise", detail: "Technical and detailed" },
  { value: "creative" as const, label: "Creative", detail: "Exploratory and imaginative" }
];

const TOOLS = [
  { value: "calculator" as const, label: "Calculator" },
  { value: "web_search" as const, label: "Web search" },
  { value: "file_reader" as const, label: "File reader" }
];

export default function SettingsPage() {
  const settings = useSettingsStore();

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-4 md:p-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-1 text-sm text-muted-foreground">Configure your AI assistant and workspace preferences.</p>
      </div>

      <section className="surface space-y-4 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Assistant tone</h2>
        <div className="space-y-2">
          {TONES.map((tone) => (
            <button
              key={tone.value}
              type="button"
              onClick={() => settings.setTone(tone.value)}
              className={`w-full rounded-lg border p-3 text-left transition ${
                settings.tone === tone.value ? "border-primary bg-primary/10" : "border-border hover:bg-secondary"
              }`}
            >
              <div className="font-medium">{tone.label}</div>
              <div className="text-xs text-muted-foreground">{tone.detail}</div>
            </button>
          ))}
        </div>
      </section>

      <section className="surface space-y-4 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Tools</h2>
        <div className="flex flex-wrap gap-2">
          {TOOLS.map((tool) => (
            <Button
              key={tool.value}
              variant={settings.enabledTools.includes(tool.value) ? "primary" : "outline"}
              size="sm"
              onClick={() => settings.toggleTool(tool.value)}
            >
              {tool.label}
            </Button>
          ))}
        </div>
      </section>

      <section className="surface space-y-4 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">Memory</h2>
        <label className="flex items-center justify-between gap-4">
          <span className="text-sm">Enable memory injection in chat</span>
          <input
            type="checkbox"
            checked={settings.memoryEnabled}
            onChange={(e) => settings.setMemoryEnabled(e.target.checked)}
            className="size-4 rounded border-border accent-primary"
          />
        </label>
      </section>
    </div>
  );
}
