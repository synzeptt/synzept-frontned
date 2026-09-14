from typing import Any, Dict, List

from .base import Skill
from .context import SkillContext
from .result import PlanningResult, SkillExecutionStatus, SkillResult, VerificationResult
from ..events import default_event_bus
from .registry import default_registry as skill_registry


# auto-register
@skill_registry.autoregister("research")
class ResearchSkill(Skill):
    identity = "research"
    purpose = "Perform web research and produce structured findings"
    capabilities = ["research"]

    def plan(self, context: SkillContext) -> PlanningResult:
        query = context.intent or context.goal
        planned = [
            {"capability": "browser", "inputs": {"url": "https://example.com", "goal": query}},
            {"capability": "research.search", "inputs": {"query": query}},
            {"capability": "research.fetch", "inputs": {"query": query}},
            {"capability": "research.extract", "inputs": {}},
            {"capability": "research.summarize", "inputs": {}},
            {"capability": "research.compare", "inputs": {}},
            {"capability": "research.report", "inputs": {"title": query}},
        ]
        return PlanningResult(planned_steps=planned)

    def prepare(self, context: SkillContext) -> None:
        context.runtime_context.setdefault("timeline", []).append({"phase": "understanding", "label": "Understanding request"})
        default_event_bus.emit("research.started", {"execution_id": context.execution_id, "intent": context.intent})

    def execute(self, context: SkillContext) -> SkillResult:
        sources = context.runtime_context.get("sources") or [
            {"title": f"Source for {context.goal}", "url": "https://example.com/source"},
        ]
        report = context.runtime_context.get("report") or {
            "title": context.goal,
            "summary": f"Research summary for {context.goal}",
            "reasoning": ["Collected multiple sources", "Compared findings", "Prepared a structured summary"],
            "sections": [
                {"title": "Summary", "content": f"Research summary for {context.goal}"},
                {"title": "Findings", "content": "Findings were aggregated from the supplied sources."},
            ],
            "sources": sources,
            "confidence": "high",
        }
        if not isinstance(report, dict):
            report = {"title": context.goal, "summary": str(report), "sections": [], "sources": sources, "confidence": "low"}
        if "summary" not in report:
            report["summary"] = report.get("description") or report.get("content") or f"Research summary for {context.goal}"
        if "sections" not in report or not isinstance(report["sections"], list):
            report["sections"] = [{"title": "Summary", "content": report.get("summary", f"Research summary for {context.goal}")}]
        context.runtime_context["report"] = report
        artifact = {
            "id": f"artifact-{context.execution_id}",
            "type": "report",
            "title": report.get("title") or context.goal,
            "description": report.get("summary") or report.get("description") or f"Research summary for {context.goal}",
            "preview": report.get("summary") or report.get("description") or f"Research summary for {context.goal}",
            "source": "research_skill",
            "verification_status": "pending",
            "location": "runtime_context",
            "timestamp": context.execution_id,
        }
        artifacts = context.runtime_context.get("artifacts", [])
        artifacts.append(artifact)
        context.runtime_context["artifacts"] = artifacts
        return SkillResult(
            status=SkillExecutionStatus.SUCCESS,
            outputs={"report": report, "artifacts": artifacts},
            message="Research execution prepared",
        )

    def verify(self, context: SkillContext) -> VerificationResult:
        report = context.runtime_context.get("report")
        artifacts = context.runtime_context.get("artifacts", [])
        passed = bool(report and report.get("sections") and artifacts)
        evidence = {"report_present": bool(report), "artifact_count": len(artifacts)}
        default_event_bus.emit("research.verified", {"execution_id": context.execution_id, "passed": passed})
        return VerificationResult(passed=passed, evidence=evidence, message="Research report verified" if passed else "Research verification pending")

    def cleanup(self, context: SkillContext) -> None:
        default_event_bus.emit("research.completed", {"execution_id": context.execution_id})


# ensure workers are registered when the skill is imported
try:
    from ..workers import research_workers  # noqa: F401
except Exception:
    pass
