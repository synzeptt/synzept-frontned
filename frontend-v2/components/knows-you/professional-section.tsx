import { UnderstandingSection } from "./understanding-section";
import type { UserUnderstanding } from "../../types/user-understanding";

const fields = [
  { title: "Active Projects", placeholder: "What are you building or working through?", multiline: true },
  { title: "Current Priorities", placeholder: "What deserves attention right now?", multiline: true },
  { title: "Current Challenges", placeholder: "What feels blocked, unclear, or difficult?", multiline: true },
  { title: "Current Learning Areas", placeholder: "What are you actively learning or exploring?", multiline: true },
];

export function ProfessionalSection(props: Pick<React.ComponentProps<typeof UnderstandingSection>, "onSave" | "onDelete" | "saving"> & { items: UserUnderstanding[] }) {
  return <UnderstandingSection {...props} category="professional" title="Current Focus" description="The work and priorities Synzept should keep in view." fields={fields} />;
}
