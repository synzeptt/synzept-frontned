"""Default domain skills registered for outcome execution.

These skills own domain vocabulary and artifact contracts. Provider-specific work
is delegated through the connector manager supplied in the skill context.
"""

from __future__ import annotations

from typing import Any

from .base import Skill
from .context import SkillContext
from .registry import default_registry
from .result import PlanningResult, SkillExecutionStatus, SkillResult, VerificationResult
from .email_skill import EmailSkill


class DomainSkill(Skill):
    capabilities: list[str] = []
    default_connector: str | None = None
    default_action = "execute"
    artifact_type = "result"

    def plan(self, context: SkillContext) -> PlanningResult:
        connector = context.planner_output.get("connector") or self.default_connector
        action = context.planner_output.get("action") or self.default_action
        return PlanningResult(planned_steps=[{
            "id": f"{self.identity}-execute",
            "capability": f"{self.identity}.{action}",
            "inputs": {"connector": connector, **context.planner_output.get("inputs", {})},
        }])

    def prepare(self, context: SkillContext) -> None:
        context.runtime_context.setdefault("timeline", []).append({"phase": "understanding", "skill": self.identity})

    def execute(self, context: SkillContext) -> SkillResult:
        artifact = {
            "type": self.artifact_type,
            "title": f"{self.identity.title()} deliverable",
            "content": context.goal,
            "skill": self.identity,
        }
        context.runtime_context["artifacts"] = context.runtime_context.get("artifacts", []) + [artifact]
        context.runtime_context["result"] = {"artifact": artifact, "goal": context.goal}
        return SkillResult(
            status=SkillExecutionStatus.SUCCESS,
            outputs={"artifacts": [artifact], "result": context.runtime_context["result"]},
            message=f"{self.identity.title()} completed",
        )

    def verify(self, context: SkillContext) -> VerificationResult:
        artifacts = context.runtime_context.get("artifacts", [])
        return VerificationResult(
            passed=bool(artifacts),
            evidence={"artifact_count": len(artifacts), "skill": self.identity},
            message=f"{self.identity.title()} artifact verified",
        )

    def cleanup(self, context: SkillContext) -> None:
        return None


def _register(name: str, connector: str, artifact_type: str, action: str = "execute"):
    cls = type(
        f"{name.title().replace('_', '')}Skill",
        (DomainSkill,),
        {"identity": name, "purpose": f"Execute {name} outcomes", "capabilities": [name], "default_connector": connector, "artifact_type": artifact_type, "default_action": action},
    )
    default_registry.register_skill(name, cls)
    return cls


default_registry.register_skill("email", EmailSkill)
MeetingSkill = _register("meeting", "google_calendar", "meeting")
TravelSkill = _register("travel", "google_calendar", "itinerary")
DocumentSkill = _register("document", "google_docs", "document")
PresentationSkill = _register("presentation", "google_slides", "presentation")
SpreadsheetSkill = _register("spreadsheet", "google_sheets", "spreadsheet")
DriveSkill = _register("drive", "google_drive", "drive")
CalendarSkill = _register("calendar", "google_calendar", "calendar")
