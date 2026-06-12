import { UnderstandingSection } from "./understanding-section";
import type { UserUnderstanding } from "../../types/user-understanding";

const fields = [
  { title: "Communication Style", placeholder: "For example: concise, direct, exploratory" },
  { title: "Decision Style", placeholder: "How do you prefer to weigh options?" },
  { title: "Productivity Style", placeholder: "How do you prefer to organize and make progress?" },
  { title: "AI Preference", placeholder: "How should Synzept respond and collaborate?" },
];

export function PreferencesSection(props: Pick<React.ComponentProps<typeof UnderstandingSection>, "onSave" | "onDelete" | "saving"> & { items: UserUnderstanding[] }) {
  return <UnderstandingSection {...props} category="preferences" title="Work Style" description="The ways you prefer to think, decide, and communicate." fields={fields} />;
}
