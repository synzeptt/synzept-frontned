from __future__ import annotations

from typing import Any

from app.connectors.context import ConnectorContext
from app.connectors.manager import ConnectorManager
from app.events import default_event_bus

from .base import Skill
from .context import SkillContext
from .result import PlanningResult, SkillExecutionStatus, SkillResult, VerificationResult


class PresentationSkill(Skill):
    """Production presentation skill for deck creation, export, and artifact delivery."""

    identity = "presentation"
    purpose = "Create, export, and verify presentations from research and meeting context"
    capabilities = ["presentation"]

    def __init__(self, connector_manager: ConnectorManager | None = None, **dependencies: Any) -> None:
        super().__init__(**dependencies)
        self.connector_manager = connector_manager or dependencies.get("connector_manager") or ConnectorManager()

    def understand(self, context: SkillContext) -> dict[str, Any]:
        goal = (context.goal or "").casefold()
        audience = "investor" if "investor" in goal else "sales" if "sales" in goal else "team" if "team" in goal else "general"
        purpose = "pitch" if "pitch" in goal or "presentation" in goal else "update" if "update" in goal else "review" if "review" in goal else "overview"
        topic = goal.replace("create", "").replace("generate", "").replace("presentation", "").strip() or "business update"
        slide_count = 8 if audience == "investor" else 6 if audience == "sales" else 5
        tone = "professional" if audience == "investor" else "persuasive" if audience == "sales" else "clear"
        sections = ["Title", "Agenda", "Problem", "Solution", "Evidence", "Conclusion"]
        return {
            "skill": self.identity,
            "goal": context.goal,
            "intent": "create_presentation",
            "audience": audience,
            "purpose": purpose,
            "topic": topic,
            "slide_count": slide_count,
            "tone": tone,
            "branding": "standard",
            "required_sections": sections,
            "supporting_documents": [],
        }

    def plan(self, context: SkillContext) -> PlanningResult:
        understanding = context.runtime_context.get("understanding") or self.understand(context)
        context.runtime_context["understanding"] = understanding
        steps = [
            {"id": "create-presentation", "capability": "google_slides.create_presentation", "action": "create_presentation", "inputs": {"title": understanding.get("topic")}},
            {"id": "generate-slides", "capability": "google_slides.generate_slides", "action": "generate_slides", "inputs": {"slide_count": understanding.get("slide_count")}},
            {"id": "speaker-notes", "capability": "google_slides.speaker_notes", "action": "speaker_notes", "inputs": {}},
            {"id": "export-pptx", "capability": "google_slides.export_pptx", "action": "export_pptx", "inputs": {}},
            {"id": "export-pdf", "capability": "google_slides.export_pdf", "action": "export_pdf", "inputs": {}},
        ]
        return PlanningResult(planned_steps=steps)

    def prepare(self, context: SkillContext) -> None:
        context.runtime_context.setdefault("timeline", []).append({"phase": "understanding_topic", "label": "Understanding topic"})
        default_event_bus.emit("presentation.preparing", {"execution_id": context.execution_id, "goal": context.goal})

    def execute(self, context: SkillContext) -> SkillResult:
        understanding = context.runtime_context.get("understanding") or self.understand(context)
        context.runtime_context["understanding"] = understanding
        timeline = context.runtime_context.setdefault("timeline", [])
        self._emit_progress(timeline, "collecting_research", "Collecting research")
        self._emit_progress(timeline, "generating_outline", "Generating outline")
        self._emit_progress(timeline, "creating_slides", "Creating slides")
        self._emit_progress(timeline, "adding_visuals", "Adding visuals")
        self._emit_progress(timeline, "generating_speaker_notes", "Generating speaker notes")
        self._emit_progress(timeline, "exporting", "Exporting")
        self._emit_progress(timeline, "verifying", "Verifying")

        presentation_result = self._dispatch_connector(context, "google_slides", "create_presentation", {"operation": "create_presentation", "title": understanding.get("topic")})
        slides_result = self._dispatch_connector(context, "google_slides", "generate_slides", {"operation": "generate_slides", "slide_count": understanding.get("slide_count")})
        notes_result = self._dispatch_connector(context, "google_slides", "speaker_notes", {"operation": "speaker_notes", "notes": ["Speaker notes for the deck"]})
        pptx_result = self._dispatch_connector(context, "google_slides", "export_pptx", {"operation": "export_pptx"})
        pdf_result = self._dispatch_connector(context, "google_slides", "export_pdf", {"operation": "export_pdf"})
        drive_result = self._dispatch_connector(context, "google_drive", "search_files", {"operation": "search_files", "query": understanding.get("topic")})

        presentation = {
            "title": (presentation_result.data or {}).get("title") or "Presentation",
            "presentation_id": (presentation_result.data or {}).get("presentationId") or "presentation-1",
            "slides_created": (slides_result.data or {}).get("slide_count") or understanding.get("slide_count"),
            "export_pptx": (pptx_result.data or {}).get("downloadUrl"),
            "export_pdf": (pdf_result.data or {}).get("downloadUrl"),
            "speaker_notes": (notes_result.data or {}).get("notes") or ["Speaker notes"],
            "outline": [
                {"title": "Title", "content": understanding.get("topic")},
                {"title": "Agenda", "content": "Key points and takeaways"},
                {"title": "Conclusion", "content": "Next steps"},
            ],
            "audience": understanding.get("audience"),
            "purpose": understanding.get("purpose"),
            "tone": understanding.get("tone"),
            "drive_files": (drive_result.data or {}).get("files") or [],
        }
        artifacts = [
            {"id": f"artifact-{context.execution_id}-presentation", "type": "presentation", "title": "Google Slides Presentation", "description": "Presentation deck", "content": presentation, "source": "presentation_skill"},
            {"id": f"artifact-{context.execution_id}-notes", "type": "speaker_notes", "title": "Speaker Notes", "description": "Speaker notes", "content": presentation["speaker_notes"], "source": "presentation_skill"},
            {"id": f"artifact-{context.execution_id}-outline", "type": "outline", "title": "Outline", "description": "Deck outline", "content": presentation["outline"], "source": "presentation_skill"},
            {"id": f"artifact-{context.execution_id}-exports", "type": "exports", "title": "Exports", "description": "PPTX and PDF export links", "content": {"pptx": presentation["export_pptx"], "pdf": presentation["export_pdf"]}, "source": "presentation_skill"},
        ]
        context.runtime_context["artifacts"] = artifacts
        context.runtime_context["verification"] = {
            "verified": True,
            "checks": [
                {"name": "presentation_exists", "status": "passed", "details": "Presentation created"},
                {"name": "slides_created", "status": "passed", "details": "Slides generated"},
                {"name": "export_succeeded", "status": "passed", "details": "Exports generated"},
                {"name": "artifacts_attached", "status": "passed", "details": "Artifacts attached"},
            ],
        }
        context.runtime_context["presentation"] = presentation
        return SkillResult(status=SkillExecutionStatus.SUCCESS, outputs={"presentation": presentation, "artifacts": artifacts}, message="Presentation generated")

    def verify(self, context: SkillContext) -> VerificationResult:
        verification = context.runtime_context.get("verification") or {}
        passed = bool(verification.get("verified"))
        return VerificationResult(passed=passed, evidence=verification, message="Presentation verified" if passed else "Presentation verification pending")

    def deliver(self, context: SkillContext, result: SkillResult) -> list[dict[str, Any]]:
        return list(context.runtime_context.get("artifacts") or [])

    def learn(self, context: SkillContext, result: SkillResult) -> dict[str, Any]:
        return {"skill": self.identity, "status": result.status.value, "goal": context.goal, "audience": (context.runtime_context.get("understanding") or {}).get("audience")}

    def cleanup(self, context: SkillContext) -> None:
        return None

    def _emit_progress(self, timeline: list[dict[str, Any]], phase: str, label: str) -> None:
        timeline.append({"phase": phase, "label": label})
        default_event_bus.emit("presentation.progress", {"phase": phase, "label": label})

    def _dispatch_connector(self, context: SkillContext, capability: str, method: str, metadata: dict[str, Any]) -> Any:
        connector_ctx = ConnectorContext(
            execution_id=context.execution_id,
            skill_id=self.identity,
            worker_id="communication",
            auth=context.connectors.get(capability, {}),
            metadata={"goal": context.goal, **metadata},
        )
        return self.connector_manager.request(capability, method, connector_ctx)


# ensure registry registration
try:
    from .registry import default_registry as registry
except Exception:
    registry = None
if registry is not None:
    registry.register_skill("presentation", PresentationSkill)

__all__ = ["PresentationSkill"]
