from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CapabilityDefinition:
    id: str
    title: str
    description: str
    primary_intent: str
    secondary_intents: list[str] = field(default_factory=list)
    keywords: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    default_workers: tuple[str, ...] = ()
    artifact_types: tuple[str, ...] = ()
    approval_required: bool = False

    def matches(self, goal: str) -> bool:
        normalized = (goal or "").casefold()
        return any(keyword in normalized for keyword in self.keywords)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "primary_intent": self.primary_intent,
            "secondary_intents": list(self.secondary_intents),
            "keywords": list(self.keywords),
            "required_tools": list(self.required_tools),
            "default_workers": list(self.default_workers),
            "artifact_types": list(self.artifact_types),
            "approval_required": self.approval_required,
        }


class CapabilityLibrary:
    def __init__(self) -> None:
        self._definitions: dict[str, CapabilityDefinition] = {}
        self._register_default_definitions()

    def _register_default_definitions(self) -> None:
        self.register(
            CapabilityDefinition(
                id="planning",
                title="Planning",
                description="Infers the work sequence and identifies the capabilities required to complete a request.",
                primary_intent="planning",
                keywords=("plan", "roadmap", "checklist", "task", "sequence", "execute"),
                required_tools=("Memory", "Files"),
                default_workers=("planning",),
                artifact_types=("execution plan",),
            )
        )
        self.register(
            CapabilityDefinition(
                id="research",
                title="Research",
                description="Collects evidence and synthesizes findings to inform execution or deliverables.",
                primary_intent="research",
                secondary_intents=["research"],
                keywords=("research", "investigate", "compare", "analyze", "study", "market", "competitor", "find out", "evidence", "latest"),
                required_tools=("Web Search", "Memory", "Files"),
                default_workers=("research",),
                artifact_types=("research summary", "evidence report"),
            )
        )
        self.register(
            CapabilityDefinition(
                id="browser",
                title="Browser", 
                description="Uses web search and browser-based signals to gather context and evidence.",
                primary_intent="research",
                secondary_intents=["browser"],
                keywords=("browser", "browse", "website", "web page", "open url", "visit", "search web"),
                required_tools=("Web Search",),
                default_workers=("browser",),
                artifact_types=("browser evidence",),
            )
        )
        self.register(
            CapabilityDefinition(
                id="email",
                title="Email",
                description="Drafts or responds to email and messaging tasks, while gating delivery for human approval.",
                primary_intent="communication",
                secondary_intents=["email"],
                keywords=("email", "message", "reply", "send", "inbox", "draft message", "mail"),
                required_tools=("Gmail", "Files", "Connected Apps"),
                default_workers=("communication",),
                artifact_types=("email draft", "message"),
                approval_required=True,
            )
        )
        self.register(
            CapabilityDefinition(
                id="calendar",
                title="Calendar",
                description="Proposes and schedules meetings, appointments, and time blocks with approval-ready dates.",
                primary_intent="scheduling",
                secondary_intents=["calendar"],
                keywords=("calendar", "meeting", "schedule", "appointment", "event", "time block", "availability"),
                required_tools=("Google Calendar", "Memory", "Connected Apps"),
                default_workers=("calendar",),
                artifact_types=("calendar plan", "meeting proposal"),
                approval_required=True,
            )
        )
        self.register(
            CapabilityDefinition(
                id="drive",
                title="Drive",
                description="Stores artifacts and manages files in Drive so execution outputs are persisted and accessible.",
                primary_intent="planning",
                secondary_intents=["drive", "file"],
                keywords=("drive", "google drive", "save to drive", "folder", "organize drive", "sync"),
                required_tools=("Google Drive", "Files"),
                default_workers=("file",),
                artifact_types=("drive artifact",),
            )
        )
        self.register(
            CapabilityDefinition(
                id="document",
                title="Document",
                description="Creates or revises professional documents, reports, and structured written deliverables.",
                primary_intent="writing",
                secondary_intents=["document"],
                keywords=("document", "doc", "proposal", "report", "brief", "documentation", "write up", "requirements document"),
                required_tools=("Files", "Memory", "Google Drive"),
                default_workers=("writing",),
                artifact_types=("document", "report"),
            )
        )
        self.register(
            CapabilityDefinition(
                id="presentation",
                title="Presentation",
                description="Prepares slides, decks, and visual summaries for stakeholder communication.",
                primary_intent="writing",
                secondary_intents=["presentation"],
                keywords=("presentation", "slide", "deck", "ppt", "slides", "talk"),
                required_tools=("Files", "Memory", "Google Drive"),
                default_workers=("writing",),
                artifact_types=("presentation", "slide deck"),
            )
        )
        self.register(
            CapabilityDefinition(
                id="spreadsheet",
                title="Spreadsheet",
                description="Prepares tabular, numerical, and data-oriented outputs suitable for spreadsheets.",
                primary_intent="planning",
                secondary_intents=["spreadsheet"],
                keywords=("spreadsheet", "sheet", "excel", "csv", "table", "tabular", "data grid"),
                required_tools=("Google Drive", "Files"),
                default_workers=("file",),
                artifact_types=("spreadsheet", "data table"),
            )
        )
        self.register(
            CapabilityDefinition(
                id="file",
                title="File Management",
                description="Organizes and saves execution outputs as artifacts, notes, or files.",
                primary_intent="planning",
                secondary_intents=["file"],
                keywords=("file", "save", "organize", "rename", "upload", "artifact", "folder"),
                required_tools=("Files",),
                default_workers=("file",),
                artifact_types=("saved file", "artifact"),
            )
        )

    def register(self, definition: CapabilityDefinition) -> None:
        self._definitions[definition.id] = definition

    def get(self, capability_id: str) -> CapabilityDefinition | None:
        return self._definitions.get(capability_id)

    def list(self) -> list[CapabilityDefinition]:
        return list(self._definitions.values())

    def infer_from_goal(self, goal: str) -> list[CapabilityDefinition]:
        matched = [definition for definition in self._definitions.values() if definition.matches(goal)]
        if not matched:
            return [self._definitions["planning"]]
        return matched

    def infer_ids(self, goal: str) -> list[str]:
        return [definition.id for definition in self.infer_from_goal(goal)]
