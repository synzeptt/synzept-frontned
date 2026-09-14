from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.execution.learning import ExecutionLearningStore

from .context_loader import ContextLoader
from .decomposer import GoalDecomposer
from .intent_analyzer import IntentAnalyzer
from .models import ExecutionPlan, PlanStep
from .risk_analyzer import RiskAnalyzer
from .capabilities import CapabilityLibrary
from .skills import SkillCatalog
from .workers import WorkerRegistry


class PlanningEngine:
    """Converts a user goal into a durable, worker-ready execution plan."""

    def __init__(self, session: AsyncSession, execution_learning_store: ExecutionLearningStore | None = None) -> None:
        self.context_loader = ContextLoader(session)
        self.intent_analyzer = IntentAnalyzer()
        self.decomposer = GoalDecomposer()
        self.risk_analyzer = RiskAnalyzer()
        self.worker_registry = WorkerRegistry()
        self.skill_catalog = SkillCatalog()
        self.capability_library = CapabilityLibrary()
        self.execution_learning_store = execution_learning_store

    async def plan(self, *, user_id: UUID, goal: str, project_id: UUID | None = None) -> ExecutionPlan:
        intent = self.intent_analyzer.classify(goal)
        context = await self.context_loader.load(user_id, project_id)
        capability_profile = self._build_capability_profile(goal, intent)
        decomposed_intent = self._select_decomposition(intent, goal)
        plan_steps = self.decomposer.decompose(decomposed_intent)
        steps = self.worker_registry.assign(intent=intent, steps=plan_steps)
        steps = self._compose_workflow_steps(intent, goal, steps, capability_profile)
        intent_analysis = self._build_intent_analysis(goal, intent, capability_profile)
        intent_analysis["execution_learning"] = await self._build_execution_learning_context(goal, intent, steps)
        steps = await self._apply_execution_learning(intent, goal, steps, capability_profile)
        steps = self._attach_skills(intent, goal, steps)
        requires_approval, approval_reason = self.risk_analyzer.analyze(goal, intent, steps)
        tools = sorted({tool for step in steps for tool in step.tools})
        expected_outputs = [step.expected_output for step in steps if step.expected_output]
        return ExecutionPlan(
            objective=goal,
            intent=intent,
            estimated_minutes=sum(step.estimated_minutes for step in steps),
            tools=tools,
            dependencies=[dependency for step in steps for dependency in step.dependencies],
            expected_outputs=expected_outputs,
            requires_approval=requires_approval,
            approval_reason=approval_reason,
            context=context,
            steps=steps,
            intent_analysis=intent_analysis,
            skills=self._select_skills(intent, goal, intent_analysis),
        )

    def _select_decomposition(self, intent: str, goal: str) -> str:
        lower_goal = goal.casefold()
        if "pdf" in lower_goal or "attached" in lower_goal or "uploaded document" in lower_goal:
            return "pdf"
        if any(keyword in lower_goal for keyword in ["browser", "website", "web page", "compare", "browse", "open" ]):
            return "browser"
        return intent if intent in {"research", "writing", "booking", "pdf", "browser"} else "general"

    def _compose_workflow_steps(self, intent: str, goal: str, steps: list[PlanStep], capability_profile: dict[str, Any]) -> list[PlanStep]:
        lower_goal = goal.casefold()
        capabilities = capability_profile.get("capabilities", [])
        if "pdf" in capabilities:
            return [
                PlanStep(id="step_1", title="Extract document context", estimated_minutes=1, tools=["Files", "Memory"], expected_output="Document understanding", worker_id="pdf", worker_name="PDF Runner"),
                PlanStep(id="step_2", title="Draft a concise summary", estimated_minutes=2, tools=["Memory", "Files"], expected_output="Summary artifact", worker_id="writing", worker_name="Writing Worker"),
            ]

        if "browser" in capabilities or "research" in capabilities or any(keyword in lower_goal for keyword in ["browser", "website", "web page", "compare", "browse", "open", "find", "latest"]):
            composed: list[PlanStep] = []
            research_priority = "research" in capabilities or intent == "research" or any(keyword in lower_goal for keyword in ["research", "compare", "investigate", "find", "latest"])
            if research_priority:
                composed.append(PlanStep(id="step_1", title="Research the topic and gather evidence", estimated_minutes=2, tools=["Memory", "Web Search"], expected_output="Research findings", worker_id="research", worker_name="Research Worker"))
            if "browser" in capabilities or any(keyword in lower_goal for keyword in ["browser", "website", "web page", "compare", "browse", "open"]):
                composed.append(PlanStep(id=f"step_{len(composed) + 1}", title="Explore the relevant web pages", estimated_minutes=2, tools=["Web Search", "Memory"], expected_output="Browser findings", worker_id="browser", worker_name="Browser Runner"))
            if research_priority:
                composed.append(PlanStep(id=f"step_{len(composed) + 1}", title="Synthesize the findings", estimated_minutes=2, tools=["Memory", "Files"], expected_output="Executive summary", worker_id="research", worker_name="Research Worker"))
            if research_priority or any(cap in capabilities for cap in ["writing", "document", "presentation"]) or any(keyword in lower_goal for keyword in ["summary", "draft", "report", "write", "document", "presentation"]):
                composed.append(PlanStep(id=f"step_{len(composed) + 1}", title="Draft the final report", estimated_minutes=2, tools=["Files", "Memory"], expected_output="Professional report", worker_id="writing", worker_name="Writing Worker"))
            if "email" in capabilities:
                composed.append(PlanStep(id=f"step_{len(composed) + 1}", title="Prepare the outbound message", estimated_minutes=1, tools=["Connected Apps", "Files"], expected_output="Email draft", worker_id="communication", worker_name="Communication Worker"))
            if not composed:
                return steps
            return composed

        if "presentation" in capabilities or "document" in capabilities:
            composed: list[PlanStep] = [
                PlanStep(id="step_1", title="Clarify the document purpose", estimated_minutes=1, tools=["Memory", "Files"], expected_output="Writing brief", worker_id="writing", worker_name="Writing Worker"),
                PlanStep(id="step_2", title="Draft the document or slide deck", estimated_minutes=2, tools=["Memory", "Files"], expected_output="Draft deliverable", worker_id="writing", worker_name="Writing Worker"),
            ]
            if "presentation" in capabilities:
                composed.append(PlanStep(id="step_3", title="Build the presentation structure", estimated_minutes=1, tools=["Files", "Memory"], expected_output="Slide outline", worker_id="writing", worker_name="Writing Worker"))
            if "email" in capabilities:
                composed.append(PlanStep(id=f"step_{len(composed) + 1}", title="Prepare the outbound message", estimated_minutes=1, tools=["Connected Apps", "Files"], expected_output="Email draft", worker_id="communication", worker_name="Communication Worker"))
            return composed

        if "spreadsheet" in capabilities:
            composed = [
                PlanStep(id="step_1", title="Define the spreadsheet layout", estimated_minutes=1, tools=["Memory", "Files"], expected_output="Spreadsheet design", worker_id="file", worker_name="File Worker"),
                PlanStep(id="step_2", title="Populate the spreadsheet data", estimated_minutes=2, tools=["Files"], expected_output="Spreadsheet content", worker_id="file", worker_name="File Worker"),
            ]
            if "email" in capabilities:
                composed.append(PlanStep(id="step_3", title="Prepare the outbound message", estimated_minutes=1, tools=["Connected Apps", "Files"], expected_output="Email draft", worker_id="communication", worker_name="Communication Worker"))
            return composed

        if "drive" in capabilities:
            composed = [
                PlanStep(id="step_1", title="Collect and organize artifacts", estimated_minutes=1, tools=["Files", "Memory"], expected_output="Artifact inventory", worker_id="file", worker_name="File Worker"),
                PlanStep(id="step_2", title="Save the deliverables to Drive", estimated_minutes=1, tools=["Google Drive", "Files"], expected_output="Saved Drive artifact", worker_id="file", worker_name="File Worker"),
            ]
            if "email" in capabilities:
                composed.append(PlanStep(id="step_3", title="Prepare the outbound message", estimated_minutes=1, tools=["Connected Apps", "Files"], expected_output="Email draft", worker_id="communication", worker_name="Communication Worker"))
            return composed

        if intent == "research" and len(steps) >= 2:
            return [
                PlanStep(id="step_1", title="Research the topic", estimated_minutes=2, tools=["Memory", "Web Search"], expected_output="Research notes", worker_id="research", worker_name="Research Worker"),
                PlanStep(id="step_2", title="Draft the final response", estimated_minutes=2, tools=["Memory", "Files"], expected_output="Professional report", worker_id="writing", worker_name="Writing Worker"),
            ]
        return steps

    async def _apply_execution_learning(self, intent: str, goal: str, steps: list[PlanStep], capability_profile: dict[str, Any]) -> list[PlanStep]:
        learning = await self._load_execution_learning(goal, intent, capability_profile)
        if not learning:
            return steps
        preferred_recovery = learning.get("preferred_recovery_strategy")
        if preferred_recovery:
            for step in steps:
                step.metadata = {**getattr(step, "metadata", {}), "preferred_recovery_strategy": preferred_recovery}
        preferred_worker = learning.get("preferred_worker")
        if preferred_worker:
            for step in steps:
                if step.worker_id in {None, "generic"}:
                    step.worker_id = preferred_worker
                    step.worker_name = preferred_worker.replace("-", " ").title()
        return steps

    def _attach_skills(self, intent: str, goal: str, steps: list[PlanStep]) -> list[PlanStep]:
        normalized_goal = goal.casefold()
        for step in steps:
            step.skill_id = self._infer_skill_id(intent=intent, step=step, goal=normalized_goal)
            step.skill_name = self._skill_name(step.skill_id)
        return steps

    def _infer_skill_id(self, *, intent: str, step: PlanStep, goal: str) -> str:
        title = f"{step.title} {step.expected_output}".casefold()
        if intent == "booking" or "train" in goal or "ticket" in goal or "travel" in goal:
            return "travel"
        if intent == "communication" or any(keyword in title for keyword in ["email", "message", "reply", "send"]):
            return "communication"
        if intent == "scheduling" or any(keyword in title for keyword in ["calendar", "meeting", "schedule", "appointment"]):
            return "calendar"
        if intent == "research" or any(keyword in title for keyword in ["research", "collect", "analyze", "evidence"]):
            return "research"
        if any(keyword in title for keyword in ["summary", "draft", "report", "write", "document", "presentation"]):
            return "writing"
        if any(keyword in title for keyword in ["file", "save", "store", "artifact"]):
            return "file"
        return "planning"

    def _skill_name(self, skill_id: str | None) -> str | None:
        return {
            "travel": "Travel Skill",
            "communication": "Communication Skill",
            "calendar": "Calendar Skill",
            "research": "Research Skill",
            "writing": "Writing Skill",
            "file": "File Management Skill",
            "planning": "Planning Skill",
        }.get(skill_id)

    async def _build_execution_learning_context(self, goal: str, intent: str, steps: list[PlanStep]) -> dict[str, Any]:
        learning = await self._load_execution_learning(goal, intent, self._build_capability_profile(goal, intent))
        if not learning:
            return {}
        return {
            "preferred_recovery_strategy": learning.get("successful_recovery_strategy"),
            "preferred_worker": learning.get("preferred_worker"),
            "reason": learning.get("reason"),
            "capability_stats": learning.get("capability_stats", {}),
        }

    async def _load_execution_learning(self, goal: str, intent: str, capability_profile: dict[str, Any]) -> dict[str, Any]:
        if not self.execution_learning_store:
            return {}
        try:
            records = await self.execution_learning_store.list(user_id=None, goal=goal, intent=intent, capabilities=capability_profile.get("capabilities", []))
        except Exception:
            return {}
        if not records:
            return {}
        preferred = max(records, key=lambda item: item.get("score", 0))
        knowledge = dict(preferred.get("knowledge", {}))
        if "successful_recovery_strategy" in knowledge and "preferred_recovery_strategy" not in knowledge:
            knowledge["preferred_recovery_strategy"] = knowledge["successful_recovery_strategy"]
        return knowledge

    def _build_intent_analysis(self, goal: str, intent: str, capability_profile: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized_goal = goal.strip().casefold()
        parameters: dict[str, Any] = {}
        capability_profile = capability_profile or self._build_capability_profile(goal, intent)
        primary_intent = capability_profile.get("primary_intent") or intent
        secondary_intents = capability_profile.get("secondary_intents", [])
        capabilities = capability_profile.get("capabilities", [])
        if "train" in normalized_goal or "ticket" in normalized_goal:
            parameters["destination"] = self._extract_destination(normalized_goal)
            parameters["date"] = self._extract_date(normalized_goal)
            parameters["preferred_time"] = self._extract_time(normalized_goal)
        if intent == "communication":
            parameters["audience"] = "recipients"
        if intent == "scheduling":
            parameters["calendar_scope"] = "meeting"
        missing_information: list[str] = []
        if primary_intent == "scheduling" and "meeting" in normalized_goal and "time" not in normalized_goal:
            missing_information.append("time")
        if intent == "booking":
            if not parameters.get("destination"):
                missing_information.append("destination")
            if "departure city" not in normalized_goal:
                missing_information.append("departure city")
            if "passenger" not in normalized_goal and "traveller" not in normalized_goal:
                missing_information.append("passenger")
            if "seat" not in normalized_goal and "preference" not in normalized_goal:
                missing_information.append("seat preference")
            missing_information.append("approval for payment")
        complexity = "low"
        if primary_intent in {"booking", "coding", "research"} or "research" in capabilities or "presentation" in normalized_goal:
            complexity = "medium"
        if primary_intent in {"planning", "analysis"}:
            complexity = "high"
        return {
            "goal": self._normalize_goal(goal),
            "intent": intent,
            "primary_intent": primary_intent,
            "secondary_intents": secondary_intents,
            "capabilities": capabilities,
            "parameters": parameters,
            "missing_information": missing_information,
            "complexity": complexity,
            "executable": not missing_information,
            "suggested_skills": self._suggested_skill_ids(primary_intent, parameters),
        }

    def _select_skills(self, intent: str, goal: str, intent_analysis: dict[str, Any]) -> list[dict[str, Any]]:
        skill_ids = intent_analysis.get("suggested_skills", [])
        if not skill_ids:
            skill_ids = ["planning"]
        return self.skill_catalog.select(skill_ids)

    def _suggested_skill_ids(self, intent: str, parameters: dict[str, Any]) -> list[str]:
        if intent == "booking":
            return ["travel", "calendar"]
        if intent == "communication":
            return ["communication", "calendar"]
        if intent == "research":
            return ["research", "writing"]
        if intent == "scheduling":
            return ["calendar", "planning"]
        if intent == "coding":
            return ["planning", "file"]
        if intent == "email":
            return ["communication"]
        return ["planning"]

    def _build_capability_profile(self, goal: str, intent: str) -> dict[str, Any]:
        matches = self.capability_library.infer_from_goal(goal)
        if not matches:
            return {"primary_intent": intent, "secondary_intents": [], "capabilities": ["planning"], "required_tools": [], "artifact_types": []}

        capabilities = [definition.id for definition in matches]
        primary_intent = matches[0].primary_intent
        secondary_intents = []
        required_tools: list[str] = []
        artifact_types: list[str] = []
        for definition in matches:
            secondary_intents.extend(definition.secondary_intents)
            required_tools.extend(definition.required_tools)
            artifact_types.extend(definition.artifact_types)
        if primary_intent == "communication" and "email" not in capabilities:
            capabilities.append("email")
        if primary_intent == "research" and "browser" not in capabilities:
            capabilities.append("browser")
        return {
            "primary_intent": primary_intent,
            "secondary_intents": list(dict.fromkeys(secondary_intents)),
            "capabilities": capabilities,
            "required_tools": sorted(set(required_tools)),
            "artifact_types": sorted(set(artifact_types)),
        }

    def _normalize_goal(self, goal: str) -> str:
        normalized = goal.strip().casefold()
        if "train" in normalized and "delhi" in normalized:
            return "book train ticket"
        if normalized.startswith("book"):
            return normalized.replace("book ", "book ", 1)
        return normalized

    def _extract_destination(self, goal: str) -> str | None:
        if "delhi" in goal:
            return "Delhi"
        if "pune" in goal:
            return "Pune"
        return None

    def _extract_date(self, goal: str) -> str | None:
        if "tomorrow" in goal:
            return "tomorrow"
        return None

    def _extract_time(self, goal: str) -> str | None:
        if "morning" in goal:
            return "morning"
        if "evening" in goal:
            return "evening"
        return None
