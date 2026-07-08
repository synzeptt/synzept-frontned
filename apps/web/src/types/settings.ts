import type { ToolName } from "./chat";

export type AssistantTone = "balanced" | "precise" | "creative";

export type SettingsState = {
  model: string;
  temperature: number;
  tone: AssistantTone;
  enabledTools: ToolName[];
  memoryEnabled: boolean;
};
