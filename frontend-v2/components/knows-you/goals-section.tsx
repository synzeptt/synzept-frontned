import { UnderstandingSection } from "./understanding-section";
import type { UserUnderstanding } from "../../types/user-understanding";

const fields = [
  { title: "Short-Term Goals", placeholder: "What would meaningful progress look like soon?", multiline: true },
  { title: "Long-Term Goals", placeholder: "What are you moving toward over time?", multiline: true },
];

export function GoalsSection(props: Pick<React.ComponentProps<typeof UnderstandingSection>, "onSave" | "onDelete" | "saving"> & { items: UserUnderstanding[] }) {
  return <UnderstandingSection {...props} category="goals" title="Goals" description="The outcomes you want Synzept to help you move toward." fields={fields} />;
}
