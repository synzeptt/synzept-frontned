from __future__ import annotations

import uuid
from typing import Any

from .context import SkillContext
from .registry import default_registry


class SkillRouter:
    """Resolve a planner output into a registered skill and ready-to-run context."""

    def __init__(self, registry=default_registry):
        self.registry = registry

    def resolve(self, planner_output: dict[str, Any]) -> tuple[type, SkillContext]:
        planner_output = dict(planner_output or {})
        capability_candidates = self._collect_capability_candidates(planner_output)
        for capability in capability_candidates:
            skill_cls = self.registry.get_skill_class(capability)
            if skill_cls is not None:
                context = self._build_context(planner_output, capability)
                return skill_cls, context

        fallback_capability = planner_output.get("selected_skill") or planner_output.get("skill") or planner_output.get("capability")
        if fallback_capability:
            skill_cls = self.registry.get_skill_class(str(fallback_capability))
            if skill_cls is not None:
                context = self._build_context(planner_output, str(fallback_capability))
                return skill_cls, context

        raise KeyError(f"No registered skill could be resolved from planner output: {planner_output}")

    def _collect_capability_candidates(self, planner_output: dict[str, Any]) -> list[str]:
        candidates: list[str] = []
        for key in ("selected_skill", "skill", "capability", "skill_name"):
            value = planner_output.get(key)
            if value:
                candidates.append(str(value))

        action = planner_output.get("action") or planner_output.get("operation") or ""
        action_key = str(action).casefold()
        action_aliases = {
            "create_event": "calendar",
            "schedule_event": "calendar",
            "find_free_slot": "calendar",
            "reply_email": "email",
            "send_email": "email",
            "draft_email": "email",
            "create_document": "document",
            "create_spreadsheet": "spreadsheet",
            "create_presentation": "presentation",
            "book_train": "browser",
            "book_ticket": "browser",
            "search_linkedin": "browser",
            "search": "research",
            "research": "research",
            "browse": "browser",
            "travel": "travel",
            "book_hotel": "travel",
            "find_availability": "browser",
            "check_availability": "browser",
        }
        if action_key in action_aliases:
            candidates.append(action_aliases[action_key])

        connectors = planner_output.get("required_connectors") or []
        connector_aliases = {
            "google_calendar": "calendar",
            "gmail": "email",
            "google_docs": "document",
            "google_sheets": "spreadsheet",
            "google_slides": "presentation",
            "browser": "browser",
            "google_drive": "document",
            "google_gmail": "email",
            "google_docs": "document",
        }
        for connector in connectors:
            if connector in connector_aliases:
                candidates.append(connector_aliases[connector])

        for candidate in list(self.registry.list_skills().keys()):
            if candidate not in candidates:
                candidates.append(candidate)

        return list(dict.fromkeys(candidates))

    def _build_context(self, planner_output: dict[str, Any], capability: str) -> SkillContext:
        exec_id = planner_output.get("execution_id") or str(uuid.uuid4())
        return SkillContext(
            execution_id=exec_id,
            intent=str(planner_output.get("action") or planner_output.get("intent") or capability),
            goal=str(planner_output.get("goal") or planner_output.get("objective") or ""),
            planner_output={**planner_output, "capability": capability},
            runtime_context={
                "goal": planner_output.get("goal") or planner_output.get("objective") or "",
                "timeline": [],
                "artifacts": [],
                "progress": [],
            },
            connectors=planner_output.get("connectors") or {},
        )
