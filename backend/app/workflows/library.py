from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowStep:
    name: str
    description: str
    worker: str | None = None
    capability: str | None = None
    depends_on: list[str] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    slug: str
    title: str
    description: str
    workers: list[str] = field(default_factory=list)
    steps: list[WorkflowStep] = field(default_factory=list)
    artifact_types: list[str] = field(default_factory=list)


class WorkflowLibrary:
    """Small workflow catalog used to map goals to execution patterns."""

    def __init__(self) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._register_default_definitions()

    def _register_default_definitions(self) -> None:
        self.register(
            WorkflowDefinition(
                slug="travel",
                title="Travel coordination",
                description="Plans and coordinates travel-related work, including research and booking prep.",
                workers=["browser", "research"],
                steps=[
                    WorkflowStep("research_destination", "Research the destination and gather key facts", worker="browser", capability="browser"),
                    WorkflowStep("prepare_itinerary", "Draft an itinerary and capture findings", worker="research", capability="research"),
                ],
                artifact_types=["travel_plan", "research_summary"],
            )
        )
        self.register(
            WorkflowDefinition(
                slug="research",
                title="Research and synthesis",
                description="Collects information from the web into a structured report.",
                workers=["browser", "research"],
                steps=[
                    WorkflowStep("collect_sources", "Collect and inspect candidate sources", worker="browser", capability="browser"),
                    WorkflowStep("synthesize_report", "Synthesize findings into a concise report", worker="research", capability="research"),
                ],
                artifact_types=["research_summary", "source_list"],
            )
        )
        self.register(
            WorkflowDefinition(
                slug="productivity",
                title="Productivity automation",
                description="Automates routine productivity tasks such as email and scheduling.",
                workers=["browser", "calendar"],
                steps=[
                    WorkflowStep("review_context", "Review task context and identify follow-up actions", worker="browser", capability="browser"),
                    WorkflowStep("execute_productivity_action", "Execute the relevant productivity action", worker="calendar", capability="google_calendar"),
                ],
                artifact_types=["task_summary", "calendar_update"],
            )
        )
        self.register(
            WorkflowDefinition(
                slug="document",
                title="Document creation",
                description="Creates structured written deliverables, notes, or reports.",
                workers=["research", "writing", "file"],
                steps=[
                    WorkflowStep("collect_context", "Collect background information and context", worker="research", capability="research"),
                    WorkflowStep("draft_document", "Write the initial document draft", worker="writing", capability="writing"),
                    WorkflowStep("save_document", "Save the document artifact", worker="file", capability="drive"),
                ],
                artifact_types=["document", "draft"],
            )
        )
        self.register(
            WorkflowDefinition(
                slug="presentation",
                title="Presentation preparation",
                description="Drafts slides and visual outlines for stakeholder-facing presentations.",
                workers=["research", "writing", "file"],
                steps=[
                    WorkflowStep("collect_insights", "Gather key points and supporting evidence", worker="research", capability="research"),
                    WorkflowStep("draft_presentation", "Create the presentation narrative and slide outline", worker="writing", capability="presentation"),
                    WorkflowStep("save_presentation", "Store the presentation artefact", worker="file", capability="drive"),
                ],
                artifact_types=["presentation", "slide deck"],
            )
        )
        self.register(
            WorkflowDefinition(
                slug="spreadsheet",
                title="Spreadsheet creation",
                description="Prepares data tables, models, or analysis-ready spreadsheets.",
                workers=["file"],
                steps=[
                    WorkflowStep("design_sheet", "Define the spreadsheet layout and columns", worker="file", capability="spreadsheet"),
                    WorkflowStep("populate_sheet", "Populate the table with structured information", worker="file", capability="spreadsheet"),
                ],
                artifact_types=["spreadsheet", "data table"],
            )
        )
        self.register(
            WorkflowDefinition(
                slug="drive",
                title="Drive artifact organization",
                description="Organizes and saves outputs to Drive for later access.",
                workers=["file"],
                steps=[
                    WorkflowStep("organize_drive", "Organize the output artifacts in Drive", worker="file", capability="drive"),
                ],
                artifact_types=["drive artifact"],
            )
        )

    def register(self, definition: WorkflowDefinition) -> None:
        self._definitions[definition.slug] = definition

    def get(self, slug: str) -> WorkflowDefinition | None:
        return self._definitions.get(slug)

    def list(self) -> list[WorkflowDefinition]:
        return list(self._definitions.values())

    def infer_from_goal(self, goal: str) -> WorkflowDefinition | None:
        lowered = goal.lower()
        if any(keyword in lowered for keyword in ["travel", "trip", "flight", "hotel", "itinerary", "vacation", "destination"]):
            return self.get("travel")
        if any(keyword in lowered for keyword in ["research", "study", "investigate", "compare", "find out", "learn about"]):
            return self.get("research")
        if any(keyword in lowered for keyword in ["email", "schedule", "calendar", "meeting", "productivity", "reminder"]):
            return self.get("productivity")
        if any(keyword in lowered for keyword in ["document", "doc", "report", "proposal", "requirements document", "brief"]):
            return self.get("document")
        if any(keyword in lowered for keyword in ["presentation", "slide", "deck", "ppt", "talk"]):
            return self.get("presentation")
        if any(keyword in lowered for keyword in ["spreadsheet", "sheet", "excel", "csv", "table", "tabular"]):
            return self.get("spreadsheet")
        if any(keyword in lowered for keyword in ["drive", "google drive", "save to drive", "folder", "organize drive"]):
            return self.get("drive")
        return None
