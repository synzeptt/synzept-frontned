from .models import PlanStep


class GoalDecomposer:
    _templates = {
        "research": [
            ("Understand the research goal", "Clarify scope and success criteria.", ["Memory", "Files"]),
            ("Collect relevant information", "Evidence and source notes.", ["Web Search", "Connected Apps"]),
            ("Analyze findings", "Comparison and decision signals.", ["Memory"]),
            ("Generate report", "A structured research report ready for review.", ["Files"]),
            ("Store and notify", "Saved output and completion event.", ["Files", "Activity"]),
        ],
        "writing": [
            ("Understand the requested outcome", "A clear writing brief.", ["Memory", "Files"]),
            ("Gather supporting context", "Relevant notes and previous work.", ["Files", "Connected Apps"]),
            ("Draft the output", "A complete first draft.", ["Memory"]),
            ("Review and save", "A saved, review-ready document.", ["Files", "Activity"]),
        ],
        "pdf": [
            ("Review the uploaded document", "A concise understanding of the uploaded document.", ["Memory", "Files"]),
            ("Extract the key points", "Structured notes from the document.", ["Files"]),
            ("Draft a summary", "A polished summary report.", ["Memory"]),
            ("Save the artifacts", "Artifacts saved for reuse.", ["Files", "Activity"]),
        ],
        "browser": [
            ("Open the relevant sources", "The primary pages are identified.", ["Web Search"]),
            ("Collect evidence from the pages", "Comparable evidence and notes.", ["Connected Apps", "Memory"]),
            ("Synthesize the findings", "A concise summary of the evidence.", ["Memory"]),
            ("Save the report", "Browser findings saved as artifacts.", ["Files", "Activity"]),
        ],
        "booking": [
            ("Understand travel requirements", "Dates, destination, and constraints.", ["Memory", "Calendar"]),
            ("Find suitable options", "Options matching the user's preferences.", ["Web Search", "Connected Apps"]),
            ("Request approval", "User confirmation before booking.", ["Approval"]),
            ("Complete the booking", "Confirmed reservation or a clear failure.", ["Connected Apps"]),
            ("Save confirmation", "Booking details saved for later.", ["Files", "Activity"]),
        ],
        "general": [
            ("Understand the goal", "A clear objective and success criteria.", ["Memory"]),
            ("Plan the work", "A concrete sequence of actions.", ["Tasks"]),
            ("Complete the work", "The requested result.", ["Connected Apps", "Files"]),
            ("Save and report back", "Output saved and activity recorded.", ["Files", "Activity"]),
        ],
    }

    def decompose(self, intent: str) -> list[PlanStep]:
        template = self._templates.get(intent, self._templates["general"])
        steps: list[PlanStep] = []
        for index, (title, output, tools) in enumerate(template, start=1):
            steps.append(
                PlanStep(
                    id=f"step_{index}",
                    title=title,
                    estimated_minutes=1 if index == 1 else 2,
                    tools=tools,
                    dependencies=[f"step_{index - 1}"] if index > 1 else [],
                    expected_output=output,
                )
            )
        return steps
