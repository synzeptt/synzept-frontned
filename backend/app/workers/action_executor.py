from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.jobs import JobType
from app.memory.store import MemoryStore
from app.models.action_execution import ActionExecution
from app.models.conversation import Conversation
from app.orchestrator.agent_context_builder import AgentContextBuilder
from app.orchestrator.intent_service import IntentService
from app.services.action_execution_service import ActionExecutionService
from app.services.chat_service import ChatService
from app.services.agent_action_execution_service import AgentActionExecutionService

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Minimal worker that connects the existing understanding/context/planning/execution stack."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.action_service = ActionExecutionService(session)

    async def execute(self, action: ActionExecution) -> ActionExecution:
        """Run the durable lifecycle for a single ActionExecution."""
        if not action:
            raise ValueError("ActionExecution is required")

        metadata = dict(action.metadata_ or {})
        action.status = "planning" if action.status == "planning" else "executing"
        action.progress = max(action.progress or 0, 10)
        action.error = None
        action.started_at = action.started_at or datetime.now(timezone.utc)
        action.started_at = action.started_at
        metadata.setdefault("logs", [])
        metadata["logs"].append({
            "status": "planning",
            "detail": "Understanding request and preparing execution context.",
            "at": datetime.now(timezone.utc).isoformat(),
        })
        action.metadata_ = metadata
        await self.session.flush()

        try:
            if action.status == "planning" and (metadata.get("stale_retry") or metadata.get("phase") == "planning"):
                action.status = "queued"
                action.progress = max(action.progress or 0, 15)
                action.error = None

            
            intent = await IntentService().classify(action.request, has_active_project=bool(action.project_id))
            metadata = dict(action.metadata_ or {})
            metadata["intent_category"] = intent.category.value
            metadata["intent_confidence"] = intent.confidence
            action.metadata_ = metadata
            self._update_progress(action, 20, "understanding", f"Intent classified as {intent.category.value}.")

            conversation = await self._get_conversation(action)
            context_builder = AgentContextBuilder(self.session)
            agent_context = await context_builder.build(
                user_id=action.user_id,
                message=action.request,
                conversation=conversation,
                intent=intent,
                project_id=action.project_id,
                include_connected_sources=True,
            )
            context_bundle = agent_context.prompt_context
            metadata = dict(action.metadata_ or {})
            metadata["agent_context"] = agent_context.for_planner()
            metadata["context_bundle"] = {
                "user_profile": getattr(context_bundle, "user_profile", ""),
                "conversation_summary": getattr(context_bundle, "conversation_summary", ""),
                "memories": list(getattr(context_bundle, "memories", []) or []),
                "project": {
                    "project_id": str(getattr(getattr(context_bundle, "project", None), "project_id", "") or ""),
                    "name": getattr(getattr(context_bundle, "project", None), "name", ""),
                    "summary": getattr(getattr(context_bundle, "project", None), "summary", ""),
                    "active_tasks": list(getattr(getattr(context_bundle, "project", None), "active_tasks", []) or []),
                },
            }
            action.metadata_ = metadata
            self._update_progress(action, 35, "context", "Execution context assembled.")

            # Reuse the existing agent execution service, which already routes through the orchestrator stack.
            await AgentActionExecutionService(self.session).execute_with_orchestrator(action, action.user_id)
            action = await self.session.get(ActionExecution, action.id)
            if action is None:
                raise RuntimeError("ActionExecution disappeared during execution")
            if action.status == "failed":
                self._update_progress(action, max(35, action.progress or 35), "failed", action.error or "Execution failed.")
                await self.session.flush()
                return action
            if action.status == "completed":
                self._update_progress(action, 100, "completed", action.output or "Completed successfully.")
                await self._remember_success(action)
                await self.session.flush()
                return action

            if action.status in {"awaiting_confirmation", "waiting_approval"}:
                self._update_progress(action, max(action.progress or 60, 80), "awaiting_confirmation", "Waiting for user approval before continuing.")
                await self.session.flush()
                return action

            # Fallback verification: never mark success without confirmed result.
            if not action.output and action.status == "executing":
                action.status = "failed"
                action.error = "Execution completed without a verifiable output."
                action.failed_at = datetime.now(timezone.utc)
                action.progress = max(action.progress or 10, 35)
                await self.session.flush()
                return action

            self._update_progress(action, 100, "completed", action.output or "Completed successfully.")
            await self._remember_success(action)
            await self.session.flush()
            return action

        except Exception as exc:
            error_message = str(exc) or "Execution failed"
            logger.exception("Action execution failed for action %s", action.id)
            action.status = "failed"
            action.error = error_message
            action.failed_at = action.failed_at or datetime.now(timezone.utc)
            action.progress = max(action.progress or 0, 35)
            metadata = dict(action.metadata_ or {})
            metadata.setdefault("logs", [])
            metadata["logs"].append({
                "status": "failed",
                "detail": error_message,
                "at": datetime.now(timezone.utc).isoformat(),
            })
            metadata["last_error"] = error_message
            action.metadata_ = metadata
            await self.session.flush()
            return action

    async def _get_conversation(self, action: ActionExecution):
        if action.conversation_id:
            conversation = await self.session.get(Conversation, action.conversation_id)
            if conversation is not None:
                return conversation
        stmt = select(Conversation).where(Conversation.user_id == action.user_id).order_by(Conversation.updated_at.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() or Conversation(user_id=action.user_id, title=action.title)

    def _update_progress(self, action: ActionExecution, progress: int, phase: str, detail: str) -> None:
        action.status = "planning" if phase == "planning" else action.status
        action.progress = max(action.progress or 0, progress)
        metadata = dict(action.metadata_ or {})
        metadata["phase"] = phase
        metadata["current_step"] = detail
        metadata.setdefault("logs", [])
        metadata["logs"].append({
            "status": phase,
            "detail": detail,
            "at": datetime.now(timezone.utc).isoformat(),
        })
        action.metadata_ = metadata

    async def _remember_success(self, action: ActionExecution) -> None:
        if not action.output:
            return
        try:
            memory = MemoryStore(self.session)
            await memory.create(
                user_id=action.user_id,
                content=f"Completed action: {action.title}. Outcome: {action.output[:240]}",
                category="execution",
                memory_type="long_term",
                project_id=action.project_id,
                conversation_id=action.conversation_id,
                importance=0.7,
            )
            metadata = dict(action.metadata_ or {})
            metadata["memory_created"] = True
            metadata["memory_id"] = str(memory.id) if hasattr(memory, "id") else None
            action.metadata_ = metadata
        except Exception:
            logger.exception("Memory creation failed for action %s", action.id)


async def execute_action(job_payload: dict[str, Any], *, session: AsyncSession | None = None) -> ActionExecution | None:
    """Job entry point for ACTION_EXECUTE work."""
    action_id = job_payload.get("action_id")
    if action_id is None:
        raise ValueError("ACTION_EXECUTE job payload missing action_id")

    action_uuid = action_id if isinstance(action_id, UUID) else UUID(str(action_id))
    async_session = session or getattr(__import__("app.database.session", fromlist=["SessionLocal"]).SessionLocal, "__call__", None)
    if session is None:
        from app.database.session import SessionLocal
        async with SessionLocal() as db_session:
            action = await db_session.get(ActionExecution, action_uuid)
            if not action:
                return None
            return await ActionExecutor(db_session).execute(action)

    action = await session.get(ActionExecution, action_uuid)
    if not action:
        return None
    return await ActionExecutor(session).execute(action)


async def run_action_job(payload: dict[str, Any]) -> ActionExecution | None:
    """Compatibility wrapper used by the worker registry."""
    return await execute_action(payload)


async def process_action_job(payload: dict[str, Any]) -> None:
    """Process a queued ACTION_EXECUTE payload and commit the result."""
    action = await execute_action(payload)
    if action is not None:
        from app.database.session import SessionLocal
        async with SessionLocal() as session:
            await session.merge(action)
            await session.commit()
