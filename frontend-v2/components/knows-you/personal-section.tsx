import { UnderstandingSection } from "./understanding-section";
import type { UserUnderstanding } from "../../types/user-understanding";

const fields = [
  { title: "Name", placeholder: "How should Synzept refer to you?" },
  { title: "Background", placeholder: "Context you want Synzept to understand", multiline: true },
  { title: "Industry", placeholder: "The field you work in" },
  { title: "Role", placeholder: "Your role or the work you do" },
  { title: "Interests", placeholder: "Topics and interests that matter to you", multiline: true },
];

export function PersonalSection(props: Pick<React.ComponentProps<typeof UnderstandingSection>, "onSave" | "onDelete" | "saving"> & { items: UserUnderstanding[] }) {
  return <UnderstandingSection {...props} category="personal" title="Who You Are" description="The personal context you have chosen to share." fields={fields} />;
}
