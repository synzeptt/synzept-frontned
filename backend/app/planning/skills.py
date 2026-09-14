from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class SkillDefinition:
    id: str
    name: str
    description: str
    category: str
    inputs: list[str]
    outputs: list[str]
    required_tools: list[str]
    approval_required: bool
    estimated_execution_time: int
    deliverable: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "required_tools": self.required_tools,
            "approval_required": self.approval_required,
            "estimated_execution_time": self.estimated_execution_time,
            "deliverable": self.deliverable,
        }


class SkillCatalog:
    def __init__(self) -> None:
        self._skills = {
            "travel": SkillDefinition(
                id="travel",
                name="Travel Skill",
                description="Books travel and gathers trip options while respecting approval gates for payments.",
                category="execution",
                inputs=["request", "context", "preferences"],
                outputs=["travel options", "booking confirmation", "calendar event"],
                required_tools=["Connected Apps", "Calendar", "Memory"],
                approval_required=True,
                estimated_execution_time=10,
                deliverable="Travel booking summary",
            ),
            "communication": SkillDefinition(
                id="communication",
                name="Communication Skill",
                description="Drafts and sends messages or emails while pausing for approval on external delivery.",
                category="execution",
                inputs=["request", "context", "recipients"],
                outputs=["draft", "delivery confirmation"],
                required_tools=["Connected Apps", "Files"],
                approval_required=True,
                estimated_execution_time=5,
                deliverable="Communication draft",
            ),
            "calendar": SkillDefinition(
                id="calendar",
                name="Calendar Skill",
                description="Creates schedules, prep blocks, and meeting plans grounded in the user's availability.",
                category="execution",
                inputs=["request", "calendar", "context"],
                outputs=["calendar plan", "event suggestions"],
                required_tools=["Calendar", "Memory"],
                approval_required=False,
                estimated_execution_time=5,
                deliverable="Calendar plan",
            ),
            "research": SkillDefinition(
                id="research",
                name="Research Skill",
                description="Collects evidence, compares options, and returns an evidence-backed summary.",
                category="execution",
                inputs=["request", "context", "sources"],
                outputs=["research report", "sources", "recommendations"],
                required_tools=["Web Search", "Memory", "Files"],
                approval_required=False,
                estimated_execution_time=7,
                deliverable="Research report",
            ),
            "writing": SkillDefinition(
                id="writing",
                name="Writing Skill",
                description="Produces polished drafts, summaries, briefs, and other written deliverables.",
                category="execution",
                inputs=["request", "context", "notes"],
                outputs=["draft", "summary", "document"],
                required_tools=["Files", "Memory"],
                approval_required=False,
                estimated_execution_time=5,
                deliverable="Written deliverable",
            ),
            "file": SkillDefinition(
                id="file",
                name="File Management Skill",
                description="Stores, organizes, and version-controls the artifacts produced by execution.",
                category="execution",
                inputs=["request", "artifacts"],
                outputs=["saved artifact", "organized note"],
                required_tools=["Files", "Memory"],
                approval_required=False,
                estimated_execution_time=3,
                deliverable="Saved artifact",
            ),
            "planning": SkillDefinition(
                id="planning",
                name="Planning Skill",
                description="Breaks a goal into smaller steps and sequences the work needed to complete it.",
                category="execution",
                inputs=["request", "context"],
                outputs=["execution plan", "next steps"],
                required_tools=["Memory", "Files"],
                approval_required=False,
                estimated_execution_time=4,
                deliverable="Execution plan",
            ),
        }

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self._skills.get(skill_id)

    def select(self, skill_ids: list[str]) -> list[dict[str, Any]]:
        return [self.get(skill_id).to_dict() for skill_id in skill_ids if self.get(skill_id)]
