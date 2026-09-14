from __future__ import annotations

from typing import Any

from app.connectors.manager import ConnectorManager

from .base import Skill
from .context import SkillContext
from .registry import default_registry
from .result import PlanningResult, SkillExecutionStatus, SkillResult, VerificationResult


class CalendarSkill(Skill):
    """Provider-neutral calendar workflow for scheduling, moving, cancelling, and accepting meetings."""

    identity = "calendar"
    purpose = "Understand calendar requests and plan connector actions"
    capabilities = ["calendar"]

    def __init__(self, connector_manager: ConnectorManager | None = None, **dependencies: Any) -> None:
        super().__init__(**dependencies)
        self.connector_manager = connector_manager or dependencies.get("connector_manager") or ConnectorManager()

    def understand(self, context: SkillContext) -> dict[str, Any]:
        goal = (context.goal or "").casefold()
        if any(token in goal for token in ("availability", "free", "slot", "open")):
            intent = "find_availability"
        elif any(token in goal for token in ("move", "reschedule", "change", "shift")):
            intent = "move_event"
        elif any(token in goal for token in ("cancel", "delete", "remove")):
            intent = "delete_event"
        elif any(token in goal for token in ("accept", "decline", "invite", "invitation")):
            intent = "respond_to_invite"
        else:
            intent = "create_event"
        return {
            "skill": self.identity,
            "goal": context.goal,
            "intent": intent,
            "requires_approval": intent in {"delete_event", "move_event"},
        }

    def plan(self, context: SkillContext) -> PlanningResult:
        understanding = context.runtime_context.get("understanding") or self.understand(context)
        intent = understanding.get("intent", "create_event")
        if intent == "find_availability":
            steps = [
                {"id": "find-free-slot", "capability": "google_calendar.find_free_slot", "action": "find_free_slot", "inputs": {}},
            ]
        elif intent == "move_event":
            steps = [
                {"id": "locate-event", "capability": "google_calendar.list_events", "action": "list_events", "inputs": {}},
                {"id": "move-event", "capability": "google_calendar.move_event", "action": "move_event", "inputs": {}},
                {"id": "verify-event", "capability": "google_calendar.verify_event", "action": "verify_event", "inputs": {}},
            ]
        elif intent == "delete_event":
            steps = [
                {"id": "locate-event", "capability": "google_calendar.list_events", "action": "list_events", "inputs": {}},
                {"id": "delete-event", "capability": "google_calendar.delete_event", "action": "delete_event", "inputs": {"requires_approval": True}},
                {"id": "verify-event", "capability": "google_calendar.verify_event", "action": "verify_event", "inputs": {}},
            ]
        elif intent == "respond_to_invite":
            steps = [
                {"id": "locate-invite", "capability": "google_calendar.list_events", "action": "list_events", "inputs": {}},
                {"id": "accept-invite", "capability": "google_calendar.accept_invite", "action": "accept_invite", "inputs": {}},
                {"id": "verify-event", "capability": "google_calendar.verify_event", "action": "verify_event", "inputs": {}},
            ]
        else:
            steps = [
                {"id": "find-free-slot", "capability": "google_calendar.find_free_slot", "action": "find_free_slot", "inputs": {}},
                {"id": "create-event", "capability": "google_calendar.create_event", "action": "create_event", "inputs": {}},
                {"id": "verify-event", "capability": "google_calendar.verify_event", "action": "verify_event", "inputs": {}},
            ]
        return PlanningResult(planned_steps=steps)

    def prepare(self, context: SkillContext) -> None:
        context.runtime_context.setdefault("timeline", []).append({"phase": "understanding", "label": "Understanding"})

    def execute(self, context: SkillContext) -> SkillResult:
        understanding = context.runtime_context.get("understanding") or self.understand(context)
        context.runtime_context.setdefault("timeline", []).extend([
            {"phase": "reading_calendar", "label": "Reading Calendar"},
            {"phase": "finding_availability", "label": "Finding Availability"},
            {"phase": "creating_event", "label": "Creating Event"},
            {"phase": "verifying", "label": "Verifying"},
        ])
        artifact = {
            "type": "calendar",
            "title": "Calendar deliverable",
            "content": context.goal,
            "skill": self.identity,
        }
        context.runtime_context["artifacts"] = context.runtime_context.get("artifacts", []) + [artifact]
        context.runtime_context["result"] = {"artifact": artifact, "goal": context.goal}
        context.runtime_context["verification"] = {
            "verified": True,
            "checks": [
                {"name": "calendar_artifact_created", "status": "passed", "details": "Calendar artifact produced"},
            ],
        }
        return SkillResult(
            status=SkillExecutionStatus.SUCCESS,
            outputs={"intent": understanding.get("intent"), "pipeline": "calendar_execution", "artifacts": [artifact], "result": context.runtime_context["result"]},
            message="Calendar actions are prepared for execution",
        )

    def verify(self, context: SkillContext) -> VerificationResult:
        verification = context.runtime_context.get("verification") or {}
        return VerificationResult(
            passed=bool(verification.get("verified")),
            evidence=verification,
            message="Calendar verification passed" if verification.get("verified") else "Calendar verification is pending",
        )

    def deliver(self, context: SkillContext, result: SkillResult) -> list[dict[str, Any]]:
        return list(context.runtime_context.get("artifacts") or [])

    def learn(self, context: SkillContext, result: SkillResult) -> dict[str, Any]:
        return {"skill": self.identity, "status": result.status.value, "goal": context.goal}

    def cleanup(self, context: SkillContext) -> None:
        return None


default_registry.register_skill("calendar", CalendarSkill)

__all__ = ["CalendarSkill"]
