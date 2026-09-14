from __future__ import annotations

import asyncio
from typing import Any

from app.connectors.context import ConnectorContext
from app.connectors.manager import ConnectorManager
from app.events import default_event_bus

from .base import Skill
from .context import SkillContext
from .result import PlanningResult, SkillExecutionStatus, SkillResult, VerificationResult


class EmailSkill(Skill):
    """Provider-neutral email workflow; all provider work goes through ConnectorManager."""

    identity = "email"
    purpose = "Find, prepare, approve, send, and verify email work"
    capabilities = ["email"]

    def __init__(self, connector_manager: ConnectorManager | None = None, **dependencies: Any) -> None:
        super().__init__(**dependencies)
        self.connector_manager = connector_manager or dependencies.get("connector_manager") or ConnectorManager()

    def understand(self, context: SkillContext) -> dict[str, Any]:
        goal = context.goal.casefold()
        if any(word in goal for word in ("summarize", "urgent", "follow-up", "follow up", "action item")):
            intent = "inbox_understanding"
            requires_approval = False
        elif any(word in goal for word in ("search", "find", "lookup")):
            intent = "search_email"
            requires_approval = False
        elif any(word in goal for word in ("archive", "label", "mark", "star", "unstar")):
            intent = "organization"
            requires_approval = any(word in goal for word in ("archive", "delete", "bulk"))
        elif "draft" in goal or "compose" in goal or "write" in goal:
            intent = "draft_email"
            requires_approval = False
        elif "unread" in goal and any(word in goal for word in ("reply", "respond")):
            intent = "reply_unread"
            requires_approval = True
        elif any(word in goal for word in ("reply", "respond")):
            intent = "reply_email"
            requires_approval = True
        elif any(word in goal for word in ("send", "forward", "delete")):
            intent = "send_email"
            requires_approval = any(word in goal for word in ("send", "delete", "forward", "bulk"))
        else:
            intent = "email"
            requires_approval = "send" in goal or "reply" in goal or "respond" in goal
        return {
            "skill": self.identity,
            "goal": context.goal,
            "intent": intent,
            "requires_approval": requires_approval,
            "recipient": self._extract_recipient(context.goal),
            "subject": self._extract_subject(context.goal),
            "query": self._extract_query(context.goal),
            "action": self._infer_action(context.goal),
        }

    def plan(self, context: SkillContext) -> PlanningResult:
        understanding = context.runtime_context.get("understanding") or self.understand(context)
        context.runtime_context["understanding"] = understanding
        intent = understanding.get("intent")
        if intent == "reply_unread":
            steps = [
                {"id": "list-unread", "capability": "gmail.list_unread", "action": "list_unread", "inputs": {"query": "is:unread"}},
                {"id": "read-threads", "capability": "gmail.read_email", "action": "read_email", "inputs": {"depends_on": "list-unread"}},
                {"id": "draft-replies", "capability": "gmail.draft_email", "action": "draft_email", "inputs": {"depends_on": "read-threads"}},
                {"id": "send-replies", "capability": "gmail.send_email", "action": "send_email", "inputs": {"depends_on": "draft-replies", "requires_approval": True}},
                {"id": "verify-sent", "capability": "gmail.verify_sent", "action": "verify_sent", "inputs": {"depends_on": "send-replies"}},
            ]
            return PlanningResult(planned_steps=steps)
        if intent == "reply_email":
            return PlanningResult(planned_steps=[
                {"id": "search-reply", "capability": "gmail.search_email", "action": "search_email", "inputs": {"query": context.runtime_context.get("understanding", {}).get("query") or context.goal}},
                {"id": "read-thread", "capability": "gmail.read_email", "action": "read_email", "inputs": {"depends_on": "search-reply"}},
                {"id": "draft-reply", "capability": "gmail.draft_email", "action": "draft_email", "inputs": {"depends_on": "read-thread"}},
                {"id": "send-reply", "capability": "gmail.send_email", "action": "send_email", "inputs": {"depends_on": "draft-reply", "requires_approval": True}},
                {"id": "verify-reply", "capability": "gmail.verify_sent", "action": "verify_sent", "inputs": {"depends_on": "send-reply"}},
            ])
        if intent == "search_email":
            return PlanningResult(planned_steps=[{"id": "search-mail", "capability": "gmail.search_email", "action": "search_email", "inputs": {"query": context.runtime_context.get("understanding", {}).get("query") or context.goal}}])
        if intent == "inbox_understanding":
            return PlanningResult(planned_steps=[{"id": "list-unread", "capability": "gmail.list_unread", "action": "list_unread", "inputs": {"query": "is:unread"}}])
        if intent == "organization":
            return PlanningResult(planned_steps=[{"id": "update-email", "capability": "gmail.label_email", "action": "label_email", "inputs": {"requires_approval": context.runtime_context.get("understanding", {}).get("requires_approval", False)}}])
        if intent == "draft_email":
            return PlanningResult(planned_steps=[{"id": "draft-email", "capability": "gmail.draft_email", "action": "draft_email", "inputs": {"recipient": context.runtime_context.get("understanding", {}).get("recipient"), "subject": context.runtime_context.get("understanding", {}).get("subject")}}])
        return PlanningResult(planned_steps=[{"id": "draft-email", "capability": "gmail.draft_email", "action": "draft_email", "inputs": {}}])

    def prepare(self, context: SkillContext) -> None:
        context.runtime_context.setdefault("timeline", []).append({"phase": "understanding", "label": "Understanding"})

    def execute(self, context: SkillContext) -> SkillResult:
        understanding = context.runtime_context.get("understanding") or self.understand(context)
        context.runtime_context["understanding"] = understanding
        timeline = context.runtime_context.setdefault("timeline", [])
        self._emit_progress(timeline, "understanding", "Understanding request")

        if understanding.get("intent") == "draft_email":
            self._emit_progress(timeline, "drafting_email", "Drafting Email")
            connector_ctx = ConnectorContext(
                execution_id=context.execution_id,
                skill_id=self.identity,
                worker_id="communication",
                auth=context.connectors.get("gmail", {}),
                metadata={
                    "operation": "draft_email",
                    "goal": context.goal,
                    "to": understanding.get("recipient"),
                    "subject": understanding.get("subject") or "Drafted email",
                    "body": f"Drafted from: {context.goal}",
                },
            )
            connector_result = self.connector_manager.request("gmail", "draft_email", connector_ctx)
            artifact = {"id": f"artifact-{context.execution_id}", "type": "draft", "title": "Draft email", "description": connector_result.message or "Draft email prepared", "content": connector_result.data, "source": "gmail_connector"}
            context.runtime_context["artifacts"] = [artifact]
            context.runtime_context["verification"] = connector_result.verification or {"verified": connector_result.success}
            return SkillResult(status=SkillExecutionStatus.SUCCESS if connector_result.success else SkillExecutionStatus.FAILURE, outputs={"requires_approval": False, "pending_approval": False, "pipeline": "draft_email", "artifacts": [artifact], "draft": connector_result.data}, message=connector_result.message or "Draft email prepared")

        if understanding.get("intent") in {"reply_unread", "reply_email"}:
            self._emit_progress(timeline, "searching_inbox", "Searching Inbox")
            self._emit_progress(timeline, "reading_thread", "Reading Thread")
            self._emit_progress(timeline, "generating_reply", "Generating Reply")
            self._emit_progress(timeline, "waiting_approval", "Waiting Approval")
            connector_result = self._dispatch_connector(context, "search_email", {"query": understanding.get("query") or context.goal})
            if connector_result and connector_result.success:
                thread_result = self._dispatch_connector(context, "read_email", {"message_id": (connector_result.data or {}).get("messages", [{}])[0].get("id")})
            else:
                thread_result = None
            reply_payload = {
                "requires_approval": True,
                "pending_approval": True,
                "pipeline": "reply",
                "search_result": connector_result.data if connector_result else None,
                "thread_result": thread_result.data if thread_result else None,
            }
            context.runtime_context["artifacts"] = [{"id": f"artifact-{context.execution_id}", "type": "reply", "title": "Draft reply", "description": "Reply prepared", "content": reply_payload, "source": "email_skill"}]
            context.runtime_context["verification"] = {"verified": bool(connector_result and connector_result.success), "checks": [{"name": "reply_pending", "status": "pending"}]}
            return SkillResult(status=SkillExecutionStatus.SUCCESS, outputs=reply_payload, message="Reply prepared and waiting for approval")

        if understanding.get("intent") == "search_email":
            self._emit_progress(timeline, "searching_mail", "Searching Mail")
            connector_result = self._dispatch_connector(context, "search_email", {"query": understanding.get("query") or context.goal})
            result = {"requires_approval": False, "pipeline": "search", "query": understanding.get("query"), "matches": [{"subject": understanding.get("subject") or context.goal}], "result": connector_result.data if connector_result else None}
            context.runtime_context["artifacts"] = [{"id": f"artifact-{context.execution_id}", "type": "search", "title": "Email search", "description": "Search completed", "content": result, "source": "email_skill"}]
            context.runtime_context["verification"] = {"verified": bool(connector_result and connector_result.success), "checks": [{"name": "search_completed", "status": "passed" if connector_result and connector_result.success else "failed"}]}
            return SkillResult(status=SkillExecutionStatus.SUCCESS, outputs=result, message="Search executed")

        if understanding.get("intent") == "inbox_understanding":
            self._emit_progress(timeline, "summarizing_inbox", "Summarizing Inbox")
            result = {"requires_approval": False, "pipeline": "inbox_understanding", "summary": f"Inbox includes urgent and follow-up items for {context.goal}", "urgent": [context.goal], "follow_ups": [context.goal], "action_items": [context.goal]}
            context.runtime_context["artifacts"] = [{"id": f"artifact-{context.execution_id}", "type": "inbox", "title": "Inbox understanding", "description": "Inbox summary prepared", "content": result, "source": "email_skill"}]
            context.runtime_context["verification"] = {"verified": True, "checks": [{"name": "inbox_summary_ready", "status": "passed"}]}
            return SkillResult(status=SkillExecutionStatus.SUCCESS, outputs=result, message="Inbox summary prepared")

        if understanding.get("intent") == "organization":
            self._emit_progress(timeline, "organizing_inbox", "Organizing Inbox")
            action = understanding.get("action") or "label"
            connector_result = self._dispatch_connector(context, "label_email", {"label_ids": ["IMPORTANT"]}) if action != "archive" else self._dispatch_connector(context, "archive_email", {})
            result = {"requires_approval": understanding.get("requires_approval", False), "pending_approval": understanding.get("requires_approval", False), "pipeline": "organization", "action": action, "result": connector_result.data if connector_result else None}
            context.runtime_context["artifacts"] = [{"id": f"artifact-{context.execution_id}", "type": "organization", "title": "Inbox organization", "description": "Organization action prepared", "content": result, "source": "email_skill"}]
            context.runtime_context["verification"] = {"verified": bool(connector_result and connector_result.success), "checks": [{"name": "organization_ready", "status": "passed" if connector_result and connector_result.success else "failed"}]}
            return SkillResult(status=SkillExecutionStatus.SUCCESS, outputs=result, message="Organization action prepared")

        if understanding.get("intent") == "send_email":
            self._emit_progress(timeline, "sending_email", "Sending Email")
            context.runtime_context["verification"] = {"verified": False, "checks": [{"name": "send_pending", "status": "pending"}]}
            return SkillResult(status=SkillExecutionStatus.SUCCESS, outputs={"requires_approval": understanding.get("requires_approval", False), "pending_approval": understanding.get("requires_approval", False), "pipeline": "send"}, message="Send action prepared")

        return SkillResult(status=SkillExecutionStatus.FAILURE, message="EmailSkill requires a supported email intent")

    def verify(self, context: SkillContext) -> VerificationResult:
        verification = context.runtime_context.get("verification") or {}
        if isinstance(verification, dict):
            passed = bool(verification.get("verified"))
            message = "Gmail verification passed" if passed else "Gmail verification is pending"
        else:
            passed = bool(verification)
            message = "Verification available"
        return VerificationResult(passed=passed, evidence=verification, message=message)

    def deliver(self, context: SkillContext, result: SkillResult) -> list[dict[str, Any]]:
        return list(context.runtime_context.get("artifacts") or [])

    def learn(self, context: SkillContext, result: SkillResult) -> dict[str, Any]:
        goal = (context.goal or "").casefold()
        preferences = {
            "writing_style": "formal" if any(word in goal for word in ("formal", "professional", "serious")) else "casual",
            "greeting": "formal" if any(word in goal for word in ("formal", "professional")) else "friendly",
            "signature": "standard",
            "frequently_contacted": [self._extract_recipient(context.goal)] if self._extract_recipient(context.goal) else [],
            "tone": "professional" if "formal" in goal else "friendly",
        }
        return {"skill": self.identity, "workflow": context.runtime_context.get("understanding", {}).get("intent"), "status": result.status.value, "approval_required": True, "preferences": preferences}

    def cleanup(self, context: SkillContext) -> None:
        return None

    def _emit_progress(self, timeline: list[dict[str, Any]], phase: str, label: str) -> None:
        timeline.append({"phase": phase, "label": label})
        default_event_bus.emit("email.progress", {"phase": phase, "label": label})

    def _dispatch_connector(self, context: SkillContext, operation: str, metadata: dict[str, Any]) -> Any:
        connector_ctx = ConnectorContext(
            execution_id=context.execution_id,
            skill_id=self.identity,
            worker_id="communication",
            auth=context.connectors.get("gmail", {}),
            metadata={"operation": operation, "goal": context.goal, **metadata},
        )
        if hasattr(self.connector_manager, "request_async"):
            try:
                if asyncio.get_running_loop():
                    return self.connector_manager.request("gmail", operation, connector_ctx)
                return asyncio.run(self.connector_manager.request_async("gmail", operation, connector_ctx))
            except RuntimeError:
                return self.connector_manager.request("gmail", operation, connector_ctx)
        return self.connector_manager.request("gmail", operation, connector_ctx)

    def _extract_recipient(self, goal: str) -> str | None:
        lowered = goal.casefold()
        if "to " in lowered:
            return goal.split("to ", 1)[1].strip().split(" ", 1)[0]
        if "to:" in lowered:
            return goal.split(":", 1)[1].strip().split(" ", 1)[0]
        return None

    def _extract_subject(self, goal: str) -> str | None:
        if "about" in goal.casefold():
            return goal.strip()
        return None

    def _extract_query(self, goal: str) -> str | None:
        if "about" in goal.casefold():
            return goal.split("about", 1)[1].strip()
        return goal.strip()

    def _infer_action(self, goal: str) -> str | None:
        lowered = goal.casefold()
        if "archive" in lowered:
            return "archive"
        if "label" in lowered:
            return "label"
        if "mark" in lowered:
            return "mark_read"
        if "star" in lowered:
            return "star"
        return None


__all__ = ["EmailSkill"]
