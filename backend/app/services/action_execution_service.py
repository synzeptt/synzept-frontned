from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.action_execution import ActionExecution
from app.models.notification import Notification
from app.schemas.task import TaskCreate
from app.tasks.service import TaskService
from app.services.workspace_activity_service import WorkspaceActivityService
from app.services.work_context_service import WorkContextService


class ActionExecutionService:
    """Creates and runs AI work without coupling it to the chat request lifetime."""

    _patterns = {
        "gmail_unread": r"\b(unread|check my gmail|check gmail|check my email|check email)\b",
        "email_work": r"\b(find.*important emails.*respond.*today|important emails.*respond.*today|draft replies)\b",
        "pdf_generation": r"\b(create.*pdf|generate.*pdf|create.*document|make.*pdf|produce.*pdf)\b",
        "external_action": r"\b(send|email|book|purchase|buy|delete|cancel|post|publish|submit|forward|mail)\b",
        "research": r"\b(research|investigate|look into|find out about|pricing|price|priced|pricing model|business model|market research)\b",
        "browser": r"\b(browser|browse|visit|open website|open url|compare pricing|pricing of|search web|website|web page|checkout)\b",
        "meeting_preparation": r"\b((prepare|help me prepare|what should i know|give me a briefing|briefing).*meeting|meeting.*(brief|prep|prepare|agenda|talking points)|prepare me for my (meeting|meetings).*|(prepare|help me prepare).*for .*meeting.*(tomorrow|today|with)|what should i know before my meeting|briefing for tomorrow's meeting|what meetings do i have (tomorrow|today))\b",
        "writing": r"\b(write|draft|prepare|generate|create notes|meeting brief|proposal|report|presentation|document|article|blog|sop|prd|product requirements)\b",
        "pdf": r"\b(pdf|attached pdf|attachment|uploaded document|summarize the attached|read the attached|review the attached)\b",
        "summarize": r"\b(summarize|summary|condense)\b",
        "analyze": r"\b(analyze|analysis|evaluate|assess)\b",
        "plan": r"\b(plan|roadmap|break down|study plan|checklist|project plan)\b",
    }
    
    # Pre-compile regex patterns for performance
    _compiled_patterns = {kind: re.compile(pattern, re.IGNORECASE) for kind, pattern in _patterns.items()}
    _approval_terms = re.compile(r"\b(send|book|purchase|buy|delete|cancel|publish|post|submit|transfer|email)\b", re.IGNORECASE)

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @classmethod
    def classify(cls, message: str) -> str | None:
        lower = message.casefold()
        return next((kind for kind, compiled_pattern in cls._compiled_patterns.items() if compiled_pattern.search(lower)), None)

    async def create_for_request(self, *, user_id: UUID, conversation_id: UUID | None, project_id: UUID | None, message: str, action_type: str | None = None, metadata: dict | None = None, context: dict | None = None) -> ActionExecution | None:
        if action_type:
            action_type = action_type.casefold()
        else:
            action_type = self.classify(message)
        if not action_type:
            action_type = "execute"
        normalized = " ".join(message.casefold().split())
        fingerprint = self._build_dedupe_key(action_type, normalized, project_id)
        existing = await self._scalar_one_or_none(select(ActionExecution).where(ActionExecution.user_id == user_id, ActionExecution.dedupe_key == fingerprint))
        retryable_meeting_result = (
            action_type == "meeting_preparation"
            and existing is not None
            and existing.status == "completed"
            and "couldn't find a meeting" in (existing.output or "").casefold()
        )
        retryable_pdf_result = (
            action_type == "pdf_generation"
            and existing is not None
            and existing.status == "completed"
            and not (existing.metadata_ or {}).get("artifacts")
        )
        if existing and existing.status not in {"failed", "cancelled"} and not retryable_meeting_result and not retryable_pdf_result:
            return existing
        if existing:
            fingerprint = f"{fingerprint}:{uuid4().hex[:12]}"
        title = self._title(action_type, message)
        request_metadata = {
            key: value
            for key, value in (metadata or {}).items()
            if key not in {"approved_at", "rejected_at", "email_work"}
        }
        task = await TaskService(self.session).create(
            user_id,
            TaskCreate(title=title, description=message, project_id=project_id),
        )
        requires_approval = action_type != "email_work" and bool(self._approval_terms.search(message))
        initial_status = "awaiting_confirmation" if requires_approval else "queued"
        task.status = "awaiting_confirmation" if requires_approval else "planning"
        work_context = (context or {}).get("relevant_connected_sources") if context else None
        if work_context is None:
            work_context = await WorkContextService(self.session).build_context(user_id=user_id, request=message)
        execution_plan = {
            "objective": message,
            "execution_steps": ["Understand the request", "Prepare the work", "Deliver the result"],
            "steps": [
                {"id": "planning", "title": "Understand the request", "status": "pending", "progress": 0},
                {"id": "execution", "title": "Prepare the work", "status": "pending", "progress": 0},
                {"id": "delivery", "title": "Deliver the result", "status": "pending", "progress": 0},
            ],
            "expected_deliverables": ["A completed response or deliverable for the request"],
            "estimated_completion": "~10 minutes",
            "requires_approval": requires_approval,
            "approval_reason": "This request may create an external side effect. Approval is required before continuing." if requires_approval else None,
            "activity": "Synzept queued the request and will prepare the execution plan.",
            "status": initial_status,
            "current_step": "Understand the request",
            "next_step": "Prepare the work",
        }
        action = ActionExecution(
            user_id=user_id,
            conversation_id=conversation_id,
            project_id=project_id,
            action_type=action_type,
            title=title,
            request=message,
            status=initial_status,
            progress=15,
            dedupe_key=fingerprint,
            metadata_={
                **request_metadata,
                "task_id": str(task.id),
                "requires_approval": requires_approval,
                "plan": None,
                "execution_plan": execution_plan,
                "work_context": work_context,
                "agent_context": context or {},
                "logs": [
                    {"status": "planning", "detail": "Synzept created a plan and is preparing the first steps."},
                    {"status": "executing", "detail": "The workflow is now being advanced step by step."},
                    {"status": initial_status, "detail": "Task is planning for execution." if not requires_approval else "Approval is required before this action can run."},
                ],
            },
        )
        if hasattr(self.session, "add"):
            self.session.add(action)
        if hasattr(self.session, "flush"):
            await self.session.flush()
        await WorkspaceActivityService(self.session).record(
            user_id=user_id,
            action="ai_action_created",
            title=title,
            detail="Goal understood and execution plan created." if not requires_approval else "Goal understood; execution is paused for approval.",
            project_id=project_id,
            task_id=task.id,
            metadata={"action_id": str(action.id), "status": action.status},
        )
        return action

    async def list(self, user_id: UUID) -> list[ActionExecution]:
        return list((await self._scalars(select(ActionExecution).where(ActionExecution.user_id == user_id).order_by(ActionExecution.updated_at.desc()).limit(100))))

    async def get(self, user_id: UUID, action_id: UUID) -> ActionExecution | None:
        return await self._owned(user_id, action_id)

    async def retry(self, user_id: UUID, action_id: UUID) -> ActionExecution | None:
        action = await self._owned(user_id, action_id)
        if not action or action.status not in {"failed", "cancelled"}:
            return action
        action.status, action.progress, action.error, action.output = "planning", 15, None, None
        action.started_at = None
        action.completed_at = None
        action.failed_at = None
        action.cancelled_at = None
        await self.session.flush()
        return action

    async def approve(self, user_id: UUID, action_id: UUID, draft_indices: list[int] | None = None) -> ActionExecution | None:
        action = await self._owned(user_id, action_id)
        if not action or action.status != "awaiting_confirmation":
            return action
        action.status = "executing"
        action.started_at = action.started_at or datetime.now(timezone.utc)
        action.progress = max(action.progress or 0, 70)
        metadata = {**action.metadata_, "approved_at": datetime.now(timezone.utc).isoformat()}
        if draft_indices is not None and action.action_type == "email_work":
            metadata["email_work"] = {**(metadata.get("email_work") or {}), "approved_draft_indices": sorted(set(draft_indices))}
        action.metadata_ = metadata
        await WorkspaceActivityService(self.session).record(
            user_id=user_id,
            action="ai_action_approved",
            title=action.title,
            detail="Approval granted; Synzept can continue the execution.",
            project_id=action.project_id,
            task_id=(action.metadata_ or {}).get("task_id"),
            execution_id=action.id,
            metadata={"action_id": str(action.id), "status": action.status},
        )
        await self.session.flush()
        return action

    async def update_email_draft(self, user_id: UUID, action_id: UUID, draft_index: int, changes: dict) -> ActionExecution | None:
        action = await self._owned(user_id, action_id)
        if not action or action.action_type != "email_work" or action.status != "awaiting_confirmation":
            return action
        metadata = dict(action.metadata_ or {})
        email_work = dict(metadata.get("email_work") or {})
        drafts = list(email_work.get("drafts") or [])
        if draft_index < 0 or draft_index >= len(drafts):
            raise ValueError("Email draft was not found.")
        draft = dict(drafts[draft_index])
        for field in ("to", "subject", "suggested_reply"):
            if field in changes and isinstance(changes[field], str) and changes[field].strip():
                draft[field] = changes[field].strip()
        drafts[draft_index] = draft
        metadata["email_work"] = {**email_work, "drafts": drafts}
        action.metadata_ = metadata
        lines = ["EMAILS NEEDING YOUR RESPONSE", "", "I reviewed your inbox and prepared replies for these messages. Nothing has been sent.", ""]
        for index, item in enumerate(drafts, start=1):
            lines.extend([
                f"{index}. {item.get('from', 'Email')} - {item.get('subject', '(no subject)')}",
                f"   Context: {item.get('context', 'No preview available.')}",
                f"   Why it needs attention: {item.get('reason', 'Needs your response')}",
                f"   Suggested reply: {item.get('suggested_reply', '')}",
                "",
            ])
        lines.append("Review the drafts below, then approve the replies you want sent.")
        action.output = "\n".join(lines)
        await self.session.flush()
        return action

    async def reject(self, user_id: UUID, action_id: UUID) -> ActionExecution | None:
        action = await self._owned(user_id, action_id)
        if not action or action.status != "awaiting_confirmation":
            return action
        action.status = "failed"
        action.failed_at = datetime.now(timezone.utc)
        action.error = "Action rejected by user."
        action.metadata_ = {**action.metadata_, "rejected_at": datetime.now(timezone.utc).isoformat()}
        await WorkspaceActivityService(self.session).record(
            user_id=user_id,
            action="ai_action_rejected",
            title=action.title,
            detail="The user rejected this work before execution began.",
            project_id=action.project_id,
            task_id=(action.metadata_ or {}).get("task_id"),
            execution_id=action.id,
            metadata={"action_id": str(action.id), "status": action.status, "reason": action.error},
        )
        await self.session.flush()
        return action

    async def cancel(self, user_id: UUID, action_id: UUID) -> ActionExecution | None:
        action = await self._owned(user_id, action_id)
        if not action or action.status in {"completed", "failed"}:
            return action
        action.status, action.progress = "cancelled", 0
        action.cancelled_at = datetime.now(timezone.utc)
        await WorkspaceActivityService(self.session).record(
            user_id=user_id,
            action="ai_action_cancelled",
            title=action.title,
            detail="Execution was cancelled before completion.",
            project_id=action.project_id,
            task_id=(action.metadata_ or {}).get("task_id"),
            execution_id=action.id,
            metadata={"action_id": str(action.id), "status": action.status},
        )
        await self.session.flush()
        return action

    async def mark_completed(self, action: ActionExecution, *, output: str | dict | None = None, error: str | None = None) -> ActionExecution:
        action.status = "completed"
        action.completed_at = action.completed_at or datetime.now(timezone.utc)
        action.started_at = action.started_at or action.completed_at
        action.failed_at = None
        if output is not None:
            if isinstance(output, dict):
                for candidate in ("result", "message", "output", "status"):
                    value = output.get(candidate)
                    if isinstance(value, str):
                        action.output = value
                        break
                else:
                    action.output = json.dumps(output, ensure_ascii=False)
            else:
                action.output = str(output)
        if error is not None:
            action.error = str(error)
        action.progress = 100
        await WorkspaceActivityService(self.session).record(
            user_id=action.user_id,
            action="ai_action_completed",
            title=action.title,
            detail="Work completed successfully.",
            project_id=action.project_id,
            task_id=(action.metadata_ or {}).get("task_id"),
            execution_id=action.id,
            metadata={"action_id": str(action.id), "status": action.status},
        )
        await self.session.flush()
        return action

    async def mark_failed(self, action: ActionExecution, *, error: str) -> ActionExecution:
        action.status = "failed"
        action.failed_at = action.failed_at or datetime.now(timezone.utc)
        action.error = error
        action.progress = max(action.progress or 0, 35)
        await WorkspaceActivityService(self.session).record(
            user_id=action.user_id,
            action="ai_action_failed",
            title=action.title,
            detail=str(error),
            project_id=action.project_id,
            task_id=(action.metadata_ or {}).get("task_id"),
            execution_id=action.id,
            metadata={"action_id": str(action.id), "status": action.status, "error": error},
        )
        await self.session.flush()
        return action

    async def _owned(self, user_id: UUID, action_id: UUID) -> ActionExecution | None:
        return await self._scalar_one_or_none(select(ActionExecution).where(ActionExecution.id == action_id, ActionExecution.user_id == user_id))

    async def _scalar_one_or_none(self, statement):
        if not hasattr(self.session, "execute"):
            return None
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def _scalars(self, statement):
        if not hasattr(self.session, "execute"):
            return []
        return (await self.session.execute(statement)).scalars()

    @staticmethod
    def _build_dedupe_key(action_type: str, normalized_request: str, project_id: UUID | None) -> str:
        project_part = str(project_id) if project_id else ""
        return hashlib.sha256(f"{action_type}:{project_part}:{normalized_request}".encode()).hexdigest()[:40]

    @staticmethod
    def _title(action_type: str, message: str) -> str:
        subject = re.sub(r"\s+", " ", message.strip().rstrip(".?!"))
        return f"{action_type.capitalize()}: {subject[:240]}"

    @staticmethod
    def _build_execution_plan(plan, message: str, action_type: str) -> dict:
        steps = plan.steps or []
        step_titles = [step.title for step in steps if getattr(step, "title", None)]
        deliverables = list(plan.expected_outputs or [])
        if not deliverables:
            deliverables = ["A completed response or deliverable for the request"]
        step_metadata = []
        for step in steps:
            step_metadata.append({
                "id": getattr(step, "id", ""),
                "title": getattr(step, "title", ""),
                "status": getattr(step, "status", "pending"),
                "estimated_minutes": getattr(step, "estimated_minutes", 1),
                "tools": getattr(step, "tools", []) or [],
                "expected_output": getattr(step, "expected_output", ""),
                "requires_approval": bool(getattr(step, "worker_requires_approval", False) or getattr(step, "requires_approval", False)),
                "worker_id": getattr(step, "worker_id", None),
                "worker_name": getattr(step, "worker_name", None),
                "worker_capabilities": getattr(step, "worker_capabilities", []) or [],
                "worker_requires_approval": bool(getattr(step, "worker_requires_approval", False)),
            })
        return {
            "objective": message,
            "execution_steps": step_titles or ["Review the request", "Prepare the work", "Deliver the result"],
            "steps": step_metadata,
            "expected_deliverables": deliverables,
            "estimated_completion": f"~{max(1, plan.estimated_minutes or 10)} minutes",
            "requires_approval": bool(plan.requires_approval),
            "approval_reason": plan.approval_reason,
            "activity": f"Synzept is preparing the first step for {action_type or 'this work'}.",
            "status": "awaiting_confirmation" if plan.requires_approval else "planning",
            "current_step": step_metadata[0]["title"] if step_metadata else None,
            "next_step": step_metadata[1]["title"] if len(step_metadata) > 1 else None,
        }

    @staticmethod
    def _enrich_execution_plan_steps(steps: list[dict], plan, message: str, action_type: str) -> list[dict]:
        if not steps:
            return steps
        enriched = []
        for index, step in enumerate(steps):
            updated = dict(step)
            updated["status"] = "pending"
            updated["progress"] = int((index / max(1, len(steps))) * 100)
            updated["detail"] = updated.get("expected_output") or f"Advance {action_type or 'execution'}"
            updated["tool_hint"] = ", ".join(updated.get("tools", [])[:3]) if updated.get("tools") else None
            enriched.append(updated)
        return enriched


async def mark_action_notification(session: AsyncSession, action: ActionExecution, *, failed: bool = False) -> None:
    key = f"action:{action.id}:{'failed' if failed else 'completed'}"
    if not hasattr(session, "execute"):
        return
    exists = (await session.execute(select(Notification.id).where(Notification.user_id == action.user_id, Notification.dedupe_key == key))).scalar_one_or_none()
    if exists:
        return
    session.add(Notification(user_id=action.user_id, notification_type="action_failed" if failed else "action_completed", title="AI execution failed" if failed else "AI work completed", message=(action.error or "Synzept could not complete this work.") if failed else f"{action.title} is ready.", priority="high" if failed else "medium", dedupe_key=key, metadata_={"href": "/actions", "actionId": str(action.id)}))
    await session.flush()
