from __future__ import annotations

from typing import Any

from app.planning.capabilities import CapabilityLibrary
from app.workflows.library import WorkflowLibrary
from app.skills.registry import default_registry


class WorkerOrchestrator:
    """Builds a lightweight orchestration plan for workers and shared context."""

    def __init__(self, workflow_library: WorkflowLibrary | None = None, capability_library: CapabilityLibrary | None = None) -> None:
        self.workflow_library = workflow_library or WorkflowLibrary()
        self.capability_library = capability_library or CapabilityLibrary()

    def build_plan(self, *, goal: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized_goal = (goal or "").casefold()
        workflow = self.workflow_library.infer_from_goal(goal)
        capability_profile = self._build_capability_profile(goal)

        workers: list[dict[str, Any]] = []
        if self._is_unread_email_reply(normalized_goal):
            workers.extend([
                {"id": "communication", "name": "Email Worker", "step": "list_unread"},
                {"id": "communication", "name": "Email Worker", "step": "read_email"},
                {"id": "communication", "name": "Email Worker", "step": "draft_email"},
                {"id": "communication", "name": "Email Worker", "step": "send_email"},
                {"id": "communication", "name": "Email Worker", "step": "verify_sent"},
            ])
        elif self._is_presentation_goal(normalized_goal):
            if self._is_research_goal(normalized_goal):
                workers.extend([
                    {"id": "browser", "name": "Browser Worker", "step": "research"},
                    {"id": "research", "name": "Research Worker", "step": "synthesize"},
                ])
            workers.extend([
                {"id": "writing", "name": "Writing Worker", "step": "create"},
                {"id": "file", "name": "File Worker", "step": "save"},
            ])
        elif self._is_spreadsheet_goal(normalized_goal):
            workers.append({"id": "file", "name": "File Worker", "step": "create"})
        elif any(term in normalized_goal for term in ("draft proposal", "create document", "prepare document", "write report")):
            workers.append({"id": "writing", "name": "Writing Worker", "step": "create"})
        elif self._is_research_goal(normalized_goal):
            workers.extend([
                {"id": "browser", "name": "Browser Worker", "step": "research"},
                {"id": "research", "name": "Research Worker", "step": "synthesize"},
                {"id": "writing", "name": "Writing Worker", "step": "report"},
            ])
            if "email" in capability_profile["capabilities"]:
                workers.append({"id": "communication", "name": "Communication Worker", "step": "email"})
            if "presentation" in capability_profile["capabilities"]:
                workers.append({"id": "writing", "name": "Writing Worker", "step": "presentation"})
        elif workflow is not None and not (workflow.slug == "research" and self._is_research_goal(normalized_goal)):
            for worker_id in workflow.workers:
                workers.append({"id": worker_id, "name": worker_id.replace("_", " ").title(), "step": worker_id})
            existing_worker_ids = {worker["id"] for worker in workers}
            if ("browser" in capability_profile["capabilities"] or self._is_research_goal(normalized_goal)) and "browser" not in existing_worker_ids:
                workers.insert(0, {"id": "browser", "name": "Browser Worker", "step": "research"})
            if "email" in capability_profile["capabilities"] and "communication" not in existing_worker_ids:
                workers.append({"id": "communication", "name": "Communication Worker", "step": "email"})
            if any(cap in capability_profile["capabilities"] for cap in ["file", "drive", "spreadsheet"]) and "file" not in existing_worker_ids:
                workers.append({"id": "file", "name": "File Worker", "step": "organize"})
            if any(cap in capability_profile["capabilities"] for cap in ["document", "presentation"]) and "writing" not in existing_worker_ids:
                workers.append({"id": "writing", "name": "Writing Worker", "step": "create"})
        elif self._is_research_goal(normalized_goal):
            workers.extend([
                {"id": "browser", "name": "Browser Worker", "step": "research"},
                {"id": "research", "name": "Research Worker", "step": "synthesize"},
                {"id": "writing", "name": "Writing Worker", "step": "report"},
            ])
            if "email" in capability_profile["capabilities"]:
                workers.append({"id": "communication", "name": "Communication Worker", "step": "email"})
            if "presentation" in capability_profile["capabilities"]:
                workers.append({"id": "writing", "name": "Writing Worker", "step": "presentation"})
        elif "train" in normalized_goal or "ticket" in normalized_goal:
            workers.append({"id": "browser", "name": "Browser Worker", "step": "search"})
            workers.append({"id": "calendar", "name": "Calendar Worker", "step": "record"})
        else:
            workers.append({"id": "browser", "name": "Browser Worker", "step": "execute"})
            if "email" in capability_profile["capabilities"]:
                workers.append({"id": "communication", "name": "Communication Worker", "step": "email"})
            if "calendar" in capability_profile["capabilities"]:
                workers.append({"id": "calendar", "name": "Calendar Worker", "step": "schedule"})
            if any(cap in capability_profile["capabilities"] for cap in ["file", "drive", "spreadsheet"]):
                workers.append({"id": "file", "name": "File Worker", "step": "organize"})
            if any(cap in capability_profile["capabilities"] for cap in ["document", "presentation"]):
                workers.append({"id": "writing", "name": "Writing Worker", "step": "create"})

        steps: list[dict[str, Any]] = []
        for index, worker in enumerate(workers, start=1):
            skill = self._resolve_skill(goal, worker["id"])
            depends_on: list[str] = []
            if self._is_unread_email_reply(normalized_goal) and worker["id"] == "communication":
                if index > 1:
                    depends_on = [f"communication-{index - 1}"]
            if worker["id"] == "research":
                depends_on = [f"browser-{index - 1}"]
            elif worker["id"] == "writing":
                depends_on = [f"research-{index - 1}"]
            elif worker["id"] == "workflow":
                depends_on = [f"writing-{index - 1}"]

            step_id = f"{worker['id']}-{index}"
            steps.append(
                {
                    "id": step_id,
                    "runner": worker["id"],
                    "action": worker.get("step") or worker["id"],
                    "metadata": {
                        "worker_id": worker["id"],
                        "skill": skill,
                        "operation": worker.get("step") if self._is_unread_email_reply(normalized_goal) else None,
                        "action_type": worker.get("step") if self._is_unread_email_reply(normalized_goal) else None,
                        "requires_approval": worker.get("step") == "send_email" if self._is_unread_email_reply(normalized_goal) else False,
                        "title": worker["name"],
                        "goal": goal,
                        "depends_on": depends_on,
                        "requires_approval": False,
                        "research_context": self._research_context(goal),
                    },
                    "depends_on": depends_on,
                    "skill": skill,
                    "requires_approval": worker.get("step") == "send_email" if self._is_unread_email_reply(normalized_goal) else False,
                }
            )

        shared_context = {
            "goal": goal,
            "execution_id": context.get("execution_id") if isinstance(context, dict) else None,
            "execution_memory": {},
            "clarification_answers": {},
            "progress": [],
            "artifacts": [],
            "approval_status": "not_required",
            "current_worker": workers[0]["id"] if workers else None,
            "current_step": workers[0]["step"] if workers else None,
            "workflow": workflow.slug if workflow else None,
            "workflow_title": workflow.title if workflow else None,
            "worker_plan": steps,
        }
        return {"workers": workers, "steps": steps, "shared_context": shared_context}

    def _resolve_skill(self, goal: str, worker_id: str) -> str | None:
        """Resolve domain behavior through the registry, keeping worker names implementation-free."""
        lowered = (goal or "").casefold()
        candidates = {
            "research": ("research",),
            "communication": ("email",),
            "calendar": ("meeting", "calendar"),
            "file": ("drive",),
            "writing": ("document",),
        }.get(worker_id, ())
        if worker_id == "calendar" and any(term in lowered for term in ("travel", "train", "flight", "hotel", "trip")):
            candidates = ("travel",)
        elif worker_id in {"writing", "file"} and any(term in lowered for term in ("presentation", "deck", "slides", "pitch")):
            candidates = ("presentation",)
        elif worker_id in {"writing", "file"} and any(term in lowered for term in ("spreadsheet", "xlsx", "chart", "sales data")):
            candidates = ("spreadsheet",)
        for candidate in candidates:
            if default_registry.get_skill_class(candidate) is not None:
                return candidate
        return None

    def _is_research_goal(self, normalized_goal: str) -> bool:
        research_keywords = [
            "research", "study", "investigate", "compare", "market", "competitor", "adoption", "developments",
            "quantum", "electric vehicle", "crm", "startup", "latest", "analysis", "industry",
        ]
        return any(keyword in normalized_goal for keyword in research_keywords)

    def _is_presentation_goal(self, normalized_goal: str) -> bool:
        return any(term in normalized_goal for term in ("presentation", "deck", "slides", "pitch"))

    def _is_unread_email_reply(self, normalized_goal: str) -> bool:
        return "unread" in normalized_goal and any(term in normalized_goal for term in ("reply", "respond")) and any(term in normalized_goal for term in ("email", "mail", "message"))

    def _is_spreadsheet_goal(self, normalized_goal: str) -> bool:
        return any(term in normalized_goal for term in ("spreadsheet", "xlsx", "sales data", "chart"))

    def _research_context(self, goal: str) -> dict[str, Any]:
        lowered = (goal or "").casefold()
        return {
            "topic": goal,
            "region": "india" if "india" in lowered else None,
            "time_period": "recent" if any(term in lowered for term in ["latest", "recent", "today", "now"]) else None,
            "depth": "deep" if any(term in lowered for term in ["compare", "market", "competitor", "analysis", "adoption"]) else "standard",
            "output_format": "report" if "report" in lowered or "summary" in lowered else "markdown",
        }

    def _build_capability_profile(self, goal: str) -> dict[str, Any]:
        matches = self.capability_library.infer_from_goal(goal)
        if not matches:
            return {"primary_intent": "planning", "secondary_intents": [], "capabilities": ["planning"], "required_tools": [], "artifact_types": []}

        capabilities = [definition.id for definition in matches]
        secondary_intents: list[str] = []
        required_tools: list[str] = []
        artifact_types: list[str] = []
        for definition in matches:
            secondary_intents.extend(definition.secondary_intents)
            required_tools.extend(definition.required_tools)
            artifact_types.extend(definition.artifact_types)
        return {
            "primary_intent": matches[0].primary_intent,
            "secondary_intents": list(dict.fromkeys(secondary_intents)),
            "capabilities": capabilities,
            "required_tools": sorted(set(required_tools)),
            "artifact_types": sorted(set(artifact_types)),
        }
