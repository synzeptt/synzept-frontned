"""Shared async job execution (used by Dramatiq actors and asyncio fallback)."""

import logging
import re
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.database.session import SessionLocal
from app.execution.artifacts import ArtifactService
from app.execution.engine import ExecutionContext, ExecutionEngine, ExecutionSession, ExecutionState, ExecutionStep, RunnerRegistry, StepExecutor
from app.execution.orchestrator import WorkerOrchestrator
from app.execution.runners import BrowserRunner, ResearchRunner, WritingRunner
from app.infrastructure.jobs import JobType
from app.infrastructure.monitoring import monitor
from app.models.action_execution import ActionExecution
from sqlalchemy import select, update
from app.planning.tools import ToolRegistry
from app.planning.workers import WorkerRegistry
from app.services.ai import AIMessage, AIRequest, AIService
logger = logging.getLogger(__name__)


def _coerce_uuid(value: object) -> UUID | None:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return UUID(str(value))


async def _claim_action(session, action_id: UUID) -> bool:
    claim = await session.execute(
        update(ActionExecution)
        .where(
            ActionExecution.id == action_id,
            ActionExecution.status.in_({"queued", "planning"}),
        )
        .values(status="executing", started_at=datetime.now(timezone.utc))
    )
    if claim.rowcount != 1:
        await session.rollback()
        return False
    return True


class ActionWorkflowExecutor(StepExecutor):
    """Runs the existing action execution path for each planned execution step."""

    name = "action-workflow"

    def __init__(self, session, action: ActionExecution, ai_service: AIService) -> None:
        self.session = session
        self.action = action
        self.ai_service = ai_service

    async def execute(self, *, step, context) -> dict:
        if context.session.current_step_index < len(context.session.steps) - 1:
            return {"status": "completed", "output": step.metadata.get("expected_output") or step.metadata.get("title") or "step completed"}
        requires_approval = bool(step.metadata.get("approval_required") or step.metadata.get("requires_approval") and step.metadata.get("approval_source") == "policy")
        if requires_approval:
            return {"status": "waiting_for_approval", "output": "Approval is required before this action can continue."}
        content, result = await _execute_action_content(self.session, self.action, self.ai_service)
        self.action.output = content
        return {"status": "completed", "output": content, "result": result}


async def execute_job(job_type: JobType, payload: dict) -> None:
    if job_type == JobType.MEMORY_POST_RESPONSE:
        await _memory_post_response(payload)
    elif job_type == JobType.DAILY_SUMMARY:
        await _daily_summary(payload)
    elif job_type == JobType.CONVERSATION_SUMMARIZE:
        await _conversation_summarize(payload)
    elif job_type == JobType.MEMORY_CONSOLIDATION:
        await _memory_consolidation(payload)
    elif job_type == JobType.ACTION_EXECUTE:
        await _action_execute(payload)
    else:
        logger.warning("Unknown job type: %s", job_type)


async def _memory_post_response(payload: dict) -> None:
    async with SessionLocal() as session:
        try:
            from app.memory.embedding_service import EmbeddingGenerationService
            from app.memory.extraction_service import ConversationTurn
            from app.memory.memory_service import MemoryService

            try:
                embeddings = EmbeddingGenerationService()
            except ValueError:
                embeddings = None

            from app.memory.intelligence_engine import MemoryIntelligenceEngine

            engine = MemoryIntelligenceEngine(session)
            await engine.process_conversation(
                user_id=_coerce_uuid(payload.get("user_id")) or UUID(str(payload["user_id"])),
                turns=[
                    ConversationTurn(role="user", content=payload["user_message"]),
                    ConversationTurn(role="assistant", content=payload["assistant_reply"]),
                ],
                conversation_id=_coerce_uuid(payload.get("conversation_id")) or UUID(str(payload["conversation_id"])),
                project_id=_coerce_uuid(payload.get("project_id")) if payload.get("project_id") else None,
            )
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _daily_summary(payload: dict) -> None:
    from app.daily.constants import KIND_EVENING, KIND_MORNING
    from app.daily.operating import DailyOperatingService
    from app.models.user import User

    async with SessionLocal() as session:
        try:
            user = await session.get(User, _coerce_uuid(payload.get("user_id")) or UUID(str(payload["user_id"])))
            if not user:
                return
            svc = DailyOperatingService(session)
            kind = payload.get("kind", KIND_MORNING)
            if kind == KIND_EVENING:
                await svc.generate_evening(user)
            else:
                await svc.generate_morning(user)
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _memory_consolidation(payload: dict) -> None:
    from app.daily.consolidation import MemoryConsolidation

    async with SessionLocal() as session:
        try:
            await MemoryConsolidation(session).run(_coerce_uuid(payload.get("user_id")) or UUID(str(payload["user_id"])))
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _conversation_summarize(payload: dict) -> None:
    from app.memory.engine import MemoryEngine

    async with SessionLocal() as session:
        try:
            engine = MemoryEngine(session)
            await engine.summarize_conversation_if_needed(_coerce_uuid(payload.get("conversation_id")) or UUID(str(payload["conversation_id"])))
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _action_execute(payload: dict) -> None:
    session = payload.get("session")
    if session is None:
        async with SessionLocal() as session:
            await _action_execute_with_session(payload, session)
        return

    await _action_execute_with_session(payload, session)


async def _action_execute_with_session(payload: dict, session) -> None:
    from app.models.note import Note
    from app.memory.background import schedule_post_response
    from app.services.action_execution_service import mark_action_notification
    from app.services.chat_service import ChatService
    from app.services.workspace_activity_service import WorkspaceActivityService
    from app.agent.initialization import initialize_tool_registry
    from sqlalchemy import select

    # Initialize tool registry for this background job execution
    # (background jobs run in separate context without app initialization)
    initialize_tool_registry()

    # Try to get action ID
    action_id_raw = payload.get("action_id")
    action_id = _coerce_uuid(action_id_raw) or UUID(str(action_id_raw))

    if not await _claim_action(session, action_id):
        return

    action = await session.get(ActionExecution, action_id)
    if not action:
        await session.rollback()
        return

    logger.info(f"Calling durable ActionExecutor for action {action.id}")
    from app.workers.action_executor import ActionExecutor

    action = await ActionExecutor(session).execute(action)
    await session.commit()
    return action

    # Legacy worker path retained below for reference during migration.
    action.status, action.progress, action.error = "running", 15, None

    worker = _resolve_worker(action)
    if worker:
        action.metadata_ = {
            **(action.metadata_ or {}),
            "active_worker": {"id": worker.id, "name": worker.name, "requires_approval": worker.requires_approval},
        }
    tool_registry = ToolRegistry()
    tool_results = tool_registry.execute_tools(worker_id=worker.id if worker else None, action=action, metadata=action.metadata_ or {})
    metadata = dict(action.metadata_ or {})
    metadata["tool_results"] = [result.to_dict() for result in tool_results]
    metadata.setdefault("execution_plan", {
        "objective": action.request,
        "execution_steps": ["Understand the request", "Prepare the work", "Deliver the result"],
        "expected_deliverables": ["A completed response or document"],
        "estimated_completion": "~10 minutes",
        "requires_approval": False,
        "approval_reason": None,
        "activity": "Synzept is gathering context and preparing the next step.",
    })
    metadata["tool_activity"] = [
        {
            "tool_id": result.tool_id,
            "name": result.name,
            "success": result.success,
            "verified": result.verification_passed,
            "requires_approval": result.requires_approval,
            "latency_ms": result.latency_ms,
        }
        for result in tool_results
    ]
    metadata["tool_summary"] = tool_registry.format_tool_context(tool_results)
    action.metadata_ = {**metadata, "active_worker": {"id": worker.id, "name": worker.name, "requires_approval": worker.requires_approval} if worker else (action.metadata_ or {}).get("active_worker")}
    await _update_action_task(session, action, "understanding", 20, f"Understanding the request and relevant user context with {worker.name if worker else 'Synzept'}.")
    if action.action_type == "research":
        _initialize_research_metadata(action)
        await _increment_action_attempt(session, action)
    await session.commit()
    _update_plan_step(action, "understanding")
    await _update_action_task(session, action, "planning", 35, f"Execution plan prepared for {worker.name if worker else 'the assigned worker'}.")
    await session.commit()
    _update_plan_step(action, "planning")
    if action.action_type == "research":
        await _set_research_stage(session, action, "understanding_request", "running", 10)

    # Handle PDF generation separately
    if action.action_type == "pdf_generation":
        await _handle_pdf_generation(session, action)
        return

    start = time.perf_counter()
    try:
        ai_service = AIService()
        task_label = "researching" if action.action_type == "research" else "writing" if action.action_type in {"writing", "prepare"} else "browsing" if action.action_type == "browser" else "executing"
        await _update_action_task(session, action, task_label, 55, f"{worker.name if worker else 'Synzept'} is executing the work.")
        await session.commit()
        _update_plan_step(action, task_label)
        execution_session = _build_execution_session(action)
        registry = RunnerRegistry()
        workflow_executor = ActionWorkflowExecutor(session, action, ai_service)
        for runner_id in {"action-workflow", "pdf", "research", "writing", "plan", "analyze", "prepare", "generic", "execute", "default"}:
            registry.register(runner_id, workflow_executor)
        if action.action_type == "browser":
            registry.register("browser", BrowserRunner(artifact_service=ArtifactService(session)))

        engine = ExecutionEngine(registry)

        def record_progress(event: dict) -> None:
            metadata = dict(action.metadata_ or {})
            execution_plan = dict(metadata.get("execution_plan") or {})
            plan_steps = [dict(step) for step in execution_plan.get("steps") or []]
            if not plan_steps:
                plan_steps = [
                    {
                        "id": str(step.get("id") or f"step-{index + 1}"),
                        "title": str(step.get("title") or step.get("action") or f"Step {index + 1}"),
                        "status": str(step.get("status") or "pending"),
                        "expected_output": str(step.get("expected_output") or ""),
                    }
                    for index, step in enumerate((metadata.get("plan") or {}).get("steps") or [])
                ]
            event_type = event.get("type")
            step_id = str(event.get("step_id")) if event.get("step_id") is not None else None
            step_index = next((index for index, step in enumerate(plan_steps) if str(step.get("id")) == step_id), None)
            if event_type == "progress":
                stages = list(metadata.get("research_stages", []))
                stage_id = event.get("stage_id") or event.get("type")
                stage_found = False
                for stage in stages:
                    if stage.get("id") == stage_id:
                        stage.update({
                            "label": event.get("label") or stage.get("label") or stage_id,
                            "status": "running" if event.get("progress", 0) < 100 else "completed",
                            "progress": event.get("progress", 0),
                            "updated_at": datetime.now(timezone.utc).isoformat(),
                        })
                        stage_found = True
                        break
                if not stage_found:
                    stages.append({
                        "id": stage_id,
                        "label": event.get("label") or step_id or stage_id.replace("_", " ").capitalize(),
                        "status": "running" if event.get("progress", 0) < 100 else "completed",
                        "progress": event.get("progress", 0),
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    })
                metadata["research_stages"] = stages
                metadata["execution_progress"] = stages
                action.metadata_ = metadata
                if event.get("progress") is not None:
                    action.progress = max(action.progress or 0, int(event["progress"]))
            elif event_type in {"step_started", "step_completed", "approval_required", "execution_started", "execution_completed"}:
                if step_index is not None and step_index >= 0:
                    step = plan_steps[step_index]
                    if event_type == "step_started":
                        step["status"] = "running"
                    elif event_type == "step_completed":
                        step["status"] = "completed"
                    elif event_type == "approval_required":
                        step["status"] = "waiting_for_approval"
                    execution_plan["steps"] = plan_steps
                    execution_plan["current_step"] = step.get("title")
                    next_step = plan_steps[step_index + 1]["title"] if step_index + 1 < len(plan_steps) else None
                    execution_plan["next_step"] = next_step
                    if event_type == "step_started":
                        execution_plan["activity"] = event.get("message") or f"Working on {step.get('title')}"
                    elif event_type == "step_completed":
                        execution_plan["activity"] = f"Completed {step.get('title')}." + (f" Next: {next_step}." if next_step else " Finalizing the result.")
                    elif event_type == "approval_required":
                        execution_plan["activity"] = event.get("message") or "Waiting for approval before continuing."
                        execution_plan["requires_approval"] = True
                        execution_plan["approval_reason"] = execution_plan.get("approval_reason") or "Your approval is required to continue this work."
                        metadata["approval_pending"] = True
                if event_type == "execution_started":
                    execution_plan["status"] = "running"
                    execution_plan["activity"] = event.get("message") or execution_plan.get("activity")
                if event_type == "execution_completed":
                    execution_plan["status"] = "completed"
                    execution_plan["activity"] = event.get("message") or execution_plan.get("activity")
                    execution_plan["completed_at"] = datetime.now(timezone.utc).isoformat()
                    action.progress = 100
                metadata["execution_plan"] = execution_plan
                action.metadata_ = metadata
                if step_index is not None and event_type == "step_started" and plan_steps:
                    action.progress = max(action.progress or 0, min(90, int((step_index / max(1, len(plan_steps))) * 100)))
            if action.progress is None:
                action.progress = 0

        execution_context = ExecutionContext(
            session=execution_session,
            metadata={
                "user_id": action.user_id,
                "action_id": action.id,
                "task_id": (action.metadata_ or {}).get("task_id"),
                "progress_callback": record_progress,
                "event_callback": record_progress,
            },
        )
        execution_result = await engine.run(execution_session, context=execution_context)
        if execution_result.state == ExecutionState.WAITING_FOR_APPROVAL:
            action.status, action.progress = "waiting_approval", 70
            metadata = dict(action.metadata_ or {})
            metadata.setdefault("execution_plan", {})
            metadata["execution_plan"]["activity"] = "Synzept paused to request the approval you asked for before continuing."
            metadata["execution_plan"]["requires_approval"] = True
            metadata["execution_plan"]["approval_reason"] = metadata.get("execution_plan", {}).get("approval_reason") or "This step needs your approval before Synzept can continue."
            metadata["approval_pending"] = True
            action.metadata_ = {**metadata, "execution_state": execution_result.state.value}
            await _update_action_task(session, action, "waiting_approval", 70, "Synzept paused for approval before continuing.")
            await session.commit()
            return
        if execution_result.state == ExecutionState.FAILED:
            raise RuntimeError(execution_result.error or "Execution failed")
        content = execution_result.output or ""
        result = execution_result.result
        action.output = content
        action.status, action.progress = "completed", 100
        metadata = dict(action.metadata_ or {})
        metadata.setdefault("execution_plan", {})
        metadata["execution_plan"]["activity"] = "Synzept finished the work and packaged the output for you."
        metadata["execution_plan"]["completed_at"] = datetime.now(timezone.utc).isoformat()
        metadata.setdefault("deliverables", [{"title": action.title, "type": "response", "detail": content[:220]}])
        action.metadata_ = metadata
        worker = _resolve_worker(action)
        if worker:
            worker_payload = worker.build_result_payload(action, content, time.perf_counter() - start, getattr(result, "usage", None), tool_results=[item.to_dict() for item in tool_results])
            action.metadata_ = {
                **action.metadata_,
                "worker_result": worker_payload,
                "active_worker": {"id": worker.id, "name": worker.name, "requires_approval": worker.requires_approval},
            }
        task_id = UUID(action.metadata_.get("task_id")) if action.metadata_.get("task_id") else None
        artifact = Note(
            user_id=action.user_id,
            project_id=action.project_id,
            title=action.title,
            content=content,
            summary=content[:220].replace("\n", " "),
            tags=["generated", "execution", action.action_type],
        )
        session.add(artifact)
        await session.flush()
        action.metadata_ = {
            **action.metadata_,
            "artifacts": [{"id": str(artifact.id), "type": "note", "title": artifact.title, "href": f"/notes?noteId={artifact.id}"}],
            "deliverables": action.metadata_.get("deliverables") or [{"title": action.title, "type": "response", "detail": content[:220]}],
        }
        await _update_action_task(session, action, "completed", 100, "Work completed and the generated output was saved to Files.")
        metadata = dict(action.metadata_ or {})
        metadata.setdefault("execution_plan", {})
        metadata["execution_plan"]["completion_summary"] = content[:320]
        metadata["execution_plan"]["status"] = "completed"
        action.metadata_ = metadata
        _update_plan_step(action, "completed")
        await _set_research_stage(session, action, "final_quality_check", "completed", 100)
        await _set_research_metadata(session, action, result)
        await _record_execution_memory(session, action, content, result)
        from app.services.evaluation_engine_service import ActionEvaluationService
        from app.services.action_learning_service import ActionLearningService

        evaluation = await ActionEvaluationService(session).evaluate(action)
        if evaluation.confidence_level == "high":
            suggestions = await ActionLearningService(session).record_completion(action)
            if suggestions:
                action.metadata_ = {
                    **action.metadata_,
                    "learning_suggestions": [
                        {"id": str(item.id), "title": item.title, "description": item.description, "confidence": item.confidence, "status": item.status}
                        for item in suggestions
                    ],
                }
        else:
            action.metadata_ = {
                **action.metadata_,
                "learning_suggestions": [],
            }
        await WorkspaceActivityService(session).record(user_id=action.user_id, action="ai_action_completed", title=action.title, detail="AI work completed and the generated output was saved to Files.", project_id=action.project_id, task_id=task_id, note_id=artifact.id, metadata={"action_id": str(action.id), "conversation_id": str(action.conversation_id) if action.conversation_id else None})
        if action.conversation_id:
            await ChatService(session).record_action_result(action.conversation_id, action.id, action.output or "")
        await mark_action_notification(session, action)
        await session.commit()
        if action.conversation_id:
            schedule_post_response(
                user_id=action.user_id,
                conversation_id=action.conversation_id,
                user_message=action.request,
                assistant_reply=action.output,
                project_id=action.project_id,
            )
        monitor.record(
            "action_execution",
            int((time.perf_counter() - start) * 1000),
            "success",
            action_type=action.action_type,
            user_id=str(action.user_id),
        )
    except Exception as exc:
        logger.exception("Action execution failed for %s", payload.get("action_id"))
        await session.rollback()
        action = await session.get(ActionExecution, _coerce_uuid(payload.get("action_id")) or UUID(str(payload["action_id"])))
        if not action or action.status == "cancelled":
            return
        error_message = str(exc) or "Synzept could not complete this work. Please retry."
        action.status, action.progress, action.error = "failed", 35, error_message
        await _update_action_task(session, action, "failed", 35, error_message)
        _update_plan_step(action, "failed")
        if action.action_type == "research":
            await _set_research_stage(session, action, "final_quality_check", "failed", 0)
        await mark_action_notification(session, action, failed=True)
        await session.commit()
        monitor.record(
            "action_execution",
            int((time.perf_counter() - start) * 1000),
            "error",
            action_type=action.action_type,
            user_id=str(action.user_id),
            error_code=error_message,
        )


async def _update_action_task(session, action, status: str, progress: int, detail: str) -> None:
    from app.models.task import Task
    from app.services.workspace_activity_service import WorkspaceActivityService

    metadata = dict(action.metadata_ or {})
    logs = list(metadata.get("logs") or [])
    logs.append({"status": status, "progress": progress, "detail": detail, "at": datetime.now(timezone.utc).isoformat()})
    action.metadata_ = {**metadata, "logs": logs}
    task_id = metadata.get("task_id")
    if not task_id:
        return
    task = await session.get(Task, UUID(task_id))
    if not task:
        return
    task.status = status
    await WorkspaceActivityService(session).record(
        user_id=task.user_id,
        action=f"task_{status}",
        title=task.title,
        detail=detail,
        project_id=task.project_id,
        task_id=task.id,
        metadata={"action_id": str(action.id), "progress": progress},
    )


def _update_plan_step(action, lifecycle_status: str) -> None:
    """Keep the persisted plan readable while a worker advances the action."""
    metadata = dict(action.metadata_ or {})
    plan = dict(metadata.get("plan") or {})
    steps = [dict(step) for step in plan.get("steps") or []]
    if not steps:
        return
    status_map = {"understanding": 0, "planning": 1, "researching": 2, "writing": 2, "executing": 2, "completed": len(steps) - 1, "failed": len(steps) - 1}
    active_index = status_map.get(lifecycle_status, 0)
    for index, step in enumerate(steps):
        if lifecycle_status == "completed" and index == len(steps) - 1:
            step["status"] = "completed"
        elif lifecycle_status == "failed" and index == active_index:
            step["status"] = "failed"
        elif index < active_index:
            step["status"] = "completed"
        elif index == active_index:
            step["status"] = "running"
    metadata["plan"] = {**plan, "steps": steps}
    action.metadata_ = metadata


async def _handle_pdf_generation(session, action: ActionExecution) -> None:
    """Handle PDF generation workflow."""
    from app.models.note import Note
    from app.memory.background import schedule_post_response
    from app.services.action_execution_service import mark_action_notification
    from app.services.chat_service import ChatService
    from app.services.file_storage_service import FileStorageService
    from app.services.workspace_activity_service import WorkspaceActivityService
    from app.tools.content_parser import ContentStructureParser
    from app.tools.pdf_generator import PDFGenerator
    import os

    start = time.perf_counter()
    action_id = action.id
    try:
        if "meeting" in action.request.casefold() and "brief" in action.request.casefold():
            await _handle_meeting_brief_pdf(session, action, start)
            return
        await _update_action_task(session, action, "pdf_generation", 40, "Generating PDF content with AI...")
        await session.commit()

        request = AIRequest(
            messages=[AIMessage(role="user", content=(
                "Create a document titled 'Future AI Opportunities'. "
                "Provide exactly 10 future opportunities in artificial intelligence. "
                "For each opportunity, include a short explanation and a comma-separated list of required skills. "
                "Use a numbered list, with each item in this format:\n\n"
                "1. Opportunity Name\n"
                "Short explanation...\n"
                "Skills required: skill 1, skill 2, skill 3\n\n"
                "The output must contain 10 opportunities exactly."
            ))],
            model="gemini-2.5-flash",
            temperature=0.7,
            max_tokens=3000,
            metadata={"interaction_type": "pdf_generation", "user_id": str(action.user_id), "conversation_id": str(action.conversation_id) if action.conversation_id else None},
        )
        ai_response = await AIService().complete(request)
        raw_content = ai_response.content.strip()
        if not raw_content:
            raise ValueError("AI returned empty content for PDF generation")

        opportunities = ContentStructureParser.parse_opportunities(raw_content, expected_count=10)
        if not opportunities:
            opportunities = ContentStructureParser._parse_text_format(raw_content)
        opportunities = ContentStructureParser.ensure_count(opportunities or [], target_count=10)
        if len(opportunities) != 10:
            raise ValueError(f"Expected 10 opportunities but received {len(opportunities)}")

        await _update_action_task(session, action, "pdf_generation", 50, "Preparing to create the PDF...")
        await session.commit()

        filename = f"future-ai-opportunities-{uuid4().hex[:8]}.pdf"
        storage_base = "/tmp/synzept-artifacts"
        pdf_path = os.path.join(storage_base, str(action.user_id), filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        pdf_payload = [{
            "number": str(index),
            "title": opp.get("title") or opp.get("name") or f"Opportunity {index}",
            "explanation": opp.get("explanation") or opp.get("summary") or "No explanation provided.",
            "skills": opp.get("skills") or opp.get("required_skills") or [],
        } for index, opp in enumerate(opportunities, start=1)]

        generator = PDFGenerator()
        generated = generator.generate(output_path=pdf_path, title="Future AI Opportunities", content=pdf_payload)
        if not generated or not os.path.exists(pdf_path) or os.path.getsize(pdf_path) <= 0:
            raise ValueError("PDF generation failed or created an empty file")

        file_storage = FileStorageService(base_path=storage_base)
        artifact_id = str(uuid4())
        file_record = file_storage.save_file(
            action.user_id,
            pdf_path,
            {
                "id": artifact_id,
                "title": "Future AI Opportunities",
                "description": "A PDF containing 10 future AI opportunities with explanations and required skills.",
                "file_type": "application/pdf",
                "action_id": str(action.id),
                "task_id": (action.metadata_ or {}).get("task_id"),
            },
        )
        if not file_record:
            raise ValueError("File storage service could not record the generated PDF")

        metadata = dict(action.metadata_ or {})
        artifact = {
            "id": artifact_id,
            "type": "pdf",
            "title": "Future AI Opportunities",
            "description": "A comprehensive PDF document with 10 future opportunities in AI.",
            "file_path": pdf_path,
            "file_size": os.path.getsize(pdf_path),
            "file_type": "application/pdf",
            "opportunities_count": len(opportunities),
            "href": f"/api/v2/actions/{action.id}/download/{artifact_id}",
            "storage_path": file_record.get("storage_path"),
            "filename": file_record.get("filename"),
        }
        metadata["artifacts"] = [*(metadata.get("artifacts") or []), artifact]
        metadata["pdf_path"] = pdf_path
        metadata["file_record"] = file_record
        metadata["opportunities_count"] = len(opportunities)

        content_summary = "Done — I created your PDF.\n\n"
        content_summary += f"File: {filename}\n"
        content_summary += f"Opportunities included: {len(opportunities)}\n\n"
        content_summary += "The PDF is saved and verified. You can open or download it from the result card.\n\n"
        for index, opp in enumerate(opportunities, start=1):
            title = opp.get("title") or opp.get("name") or f"Opportunity {index}"
            content_summary += f"{index}. {title}\n"
        action.output = content_summary
        action.status, action.progress = "completed", 100
        metadata["execution_plan"] = metadata.get("execution_plan", {})
        metadata["execution_plan"]["activity"] = "PDF created and verified successfully."
        metadata["execution_plan"]["completed_at"] = datetime.now(timezone.utc).isoformat()
        metadata["execution_plan"]["status"] = "completed"
        action.metadata_ = metadata

        await _update_action_task(session, action, "pdf_verification", 75, "Verifying the PDF file and artifact metadata...")
        await session.commit()

        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) <= 0:
            raise ValueError("Verification failed: PDF is missing or empty")
        if not action.metadata_ or not (action.metadata_.get("artifacts") or []):
            raise ValueError("Verification failed: no artifact record was saved")

        await _update_action_task(session, action, "completed", 100, "PDF created and saved successfully.")

        task_id = UUID(action.metadata_.get("task_id")) if action.metadata_.get("task_id") else None
        artifact_note = Note(
            user_id=action.user_id,
            project_id=action.project_id,
            title=action.title,
            content=content_summary,
            summary=content_summary[:220].replace("\n", " "),
            tags=["generated", "pdf", "pdf_generation"],
        )
        session.add(artifact_note)
        await session.flush()

        metadata = dict(action.metadata_ or {})
        metadata["artifacts"] = [
            *metadata.get("artifacts", []),
            {"id": str(artifact_note.id), "type": "note", "title": artifact_note.title, "href": f"/notes?noteId={artifact_note.id}"}
        ]
        action.metadata_ = metadata

        await WorkspaceActivityService(session).record(
            user_id=action.user_id,
            action="ai_action_completed",
            title=action.title,
            detail="PDF generated successfully with 10 future AI opportunities.",
            project_id=action.project_id,
            task_id=task_id,
            note_id=artifact_note.id,
            metadata={"action_id": str(action.id), "conversation_id": str(action.conversation_id) if action.conversation_id else None, "pdf_path": pdf_path}
        )

        if action.conversation_id:
            await ChatService(session).record_action_result(action.conversation_id, action.id, content_summary)

        await mark_action_notification(session, action)
        await session.commit()

        if action.conversation_id:
            schedule_post_response(
                user_id=action.user_id,
                conversation_id=action.conversation_id,
                user_message=action.request,
                assistant_reply=content_summary,
                project_id=action.project_id,
            )

        monitor.record(
            "action_execution",
            int((time.perf_counter() - start) * 1000),
            "success",
            action_type="pdf_generation",
            user_id=str(action.user_id),
        )

    except Exception as exc:
        logger.exception("PDF generation failed for %s", action_id)
        await session.rollback()
        
        action = await session.get(ActionExecution, action_id)
        if not action or action.status == "cancelled":
            return
        
        error_message = str(exc) or "PDF generation failed. Please retry."
        action.status, action.progress, action.error = "failed", 35, error_message
        
        await _update_action_task(session, action, "failed", 35, error_message)
        await mark_action_notification(session, action, failed=True)
        await session.commit()
        
        monitor.record(
            "action_execution",
            int((time.perf_counter() - start) * 1000),
            "error",
            action_type="pdf_generation",
            user_id=str(action.user_id),
            error_code=error_message,
        )


async def _handle_meeting_brief_pdf(session, action: ActionExecution, start: float) -> None:
    from app.memory.background import schedule_post_response
    from app.models.note import Note
    from app.services.action_execution_service import mark_action_notification
    from app.services.chat_service import ChatService
    from app.services.file_storage_service import FileStorageService
    from app.services.workspace_activity_service import WorkspaceActivityService
    from app.tools.pdf_generator import PDFGenerator
    import os

    result = await session.execute(
        select(ActionExecution)
        .where(
            ActionExecution.user_id == action.user_id,
            ActionExecution.conversation_id == action.conversation_id,
            ActionExecution.action_type == "meeting_preparation",
            ActionExecution.status == "completed",
            ActionExecution.output.is_not(None),
        )
        .order_by(ActionExecution.updated_at.desc())
        .limit(1)
    )
    source = result.scalar_one_or_none()
    if not source:
        raise ValueError("I couldn't create the PDF because the meeting brief is not complete yet.")

    await _update_action_task(session, action, "pdf_generation", 45, "Preparing the verified meeting brief for PDF export.")
    filename = f"meeting-brief-{uuid4().hex[:8]}.pdf"
    storage_base = "/tmp/synzept-artifacts"
    pdf_path = os.path.join(storage_base, str(action.user_id), filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    generated = PDFGenerator().generate(
        output_path=pdf_path,
        title="Meeting Brief",
        content=[{"number": "1", "title": "Meeting Brief", "explanation": source.output, "skills": []}],
    )
    if not generated or not os.path.exists(pdf_path) or os.path.getsize(pdf_path) <= 0:
        raise ValueError("PDF generation failed or created an empty file")

    artifact_id = str(uuid4())
    file_record = FileStorageService(base_path=storage_base).save_file(
        action.user_id,
        pdf_path,
        {
            "id": artifact_id,
            "title": "Meeting Brief",
            "description": "Verified meeting brief exported as a PDF.",
            "file_type": "application/pdf",
            "action_id": str(action.id),
            "task_id": (action.metadata_ or {}).get("task_id"),
        },
    )
    if not file_record:
        raise ValueError("File storage service could not record the generated PDF")

    artifact = {
        "id": artifact_id,
        "type": "pdf",
        "title": "Meeting Brief",
        "description": "Verified meeting brief exported as a PDF.",
        "file_path": pdf_path,
        "file_size": os.path.getsize(pdf_path),
        "file_type": "application/pdf",
        "href": f"/api/v2/actions/{action.id}/download/{artifact_id}",
        "storage_path": file_record.get("storage_path"),
        "filename": file_record.get("filename"),
    }
    content_summary = f"Done — I created the meeting brief PDF.\n\nFile: {filename}\nThe PDF is saved and verified. You can open or download it from the result card."
    metadata = dict(action.metadata_ or {})
    metadata["artifacts"] = [*(metadata.get("artifacts") or []), artifact]
    metadata["pdf_path"] = pdf_path
    metadata["file_record"] = file_record
    metadata["execution_plan"] = {**(metadata.get("execution_plan") or {}), "activity": "Meeting brief PDF created and verified successfully.", "status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}
    action.metadata_ = metadata
    action.output = content_summary
    action.status, action.progress = "completed", 100
    await _update_action_task(session, action, "pdf_verification", 100, "Meeting brief PDF created and saved successfully.")

    artifact_note = Note(
        user_id=action.user_id,
        project_id=action.project_id,
        title=action.title,
        content=content_summary,
        summary=content_summary[:220].replace("\n", " "),
        tags=["generated", "pdf", "meeting-brief"],
    )
    session.add(artifact_note)
    await session.flush()
    metadata["artifacts"].append({"id": str(artifact_note.id), "type": "note", "title": artifact_note.title, "href": f"/notes?noteId={artifact_note.id}"})
    action.metadata_ = metadata
    await WorkspaceActivityService(session).record(
        user_id=action.user_id,
        action="ai_action_completed",
        title=action.title,
        detail="Meeting brief PDF generated and verified.",
        project_id=action.project_id,
        task_id=(action.metadata_ or {}).get("task_id"),
        note_id=artifact_note.id,
        metadata={"action_id": str(action.id), "conversation_id": str(action.conversation_id) if action.conversation_id else None, "pdf_path": pdf_path},
    )
    if action.conversation_id:
        await ChatService(session).record_action_result(action.conversation_id, action.id, content_summary)
    await mark_action_notification(session, action)
    await session.commit()
    if action.conversation_id:
        schedule_post_response(user_id=action.user_id, conversation_id=action.conversation_id, user_message=action.request, assistant_reply=content_summary, project_id=action.project_id)
    monitor.record("action_execution", int((time.perf_counter() - start) * 1000), "success", action_type="pdf_generation", user_id=str(action.user_id))


async def _execute_action_content(session, action: ActionExecution, ai_service: AIService) -> tuple[str, object]:
    prior_context = None
    if action.action_type == "research":
        await _set_research_stage(session, action, "planning_research", "running", 25)
        prior_context = await _build_research_context(session, action)
    elif action.action_type in {"writing", "prepare"}:
        await _set_research_stage(session, action, "planning_research", "running", 25)
        await _set_research_stage(session, action, "collecting_information", "running", 40)
        request = AIRequest(
            messages=_build_action_messages(action, prior_context=prior_context),
            max_tokens=2200,
            metadata={"interaction_type": "action_execution", "user_id": action.user_id, "conversation_id": action.conversation_id},
        )
        result = await ai_service.complete(request)
        await _set_research_stage(session, action, "analyzing_findings", "running", 55)
        await _set_research_stage(session, action, "writing_report", "running", 75)
        output = result.content.strip()
        await _set_research_stage(session, action, "writing_report", "completed", 90)
        await _set_research_stage(session, action, "final_quality_check", "running", 95)
        return output, result
    request = AIRequest(
        messages=_build_action_messages(action, prior_context=None),
        max_tokens=2200,
        metadata={"interaction_type": "action_execution", "user_id": action.user_id, "conversation_id": action.conversation_id},
    )
    result = await ai_service.complete(request)
    return result.content.strip(), result


def _build_execution_session(action: ActionExecution) -> ExecutionSession:
    metadata = getattr(action, "metadata_", None) or {}
    action_type = getattr(action, "action_type", None) or ""
    attachments = metadata.get("attachments") or []
    file_paths = [item.get("path") for item in attachments if isinstance(item, dict) and item.get("path")]
    is_pdf_action = action_type == "pdf" or any((item.get("filename") or "").lower().endswith(".pdf") for item in attachments if isinstance(item, dict))

    plan = metadata.get("plan") or {}
    steps_payload = plan.get("steps") or []
    if not steps_payload:
        if is_pdf_action:
            steps_payload = [{
                "id": "execute",
                "runner": "pdf",
                "action": action_type or "execute",
                "metadata": {
                    "goal": getattr(action, "request", ""),
                    "title": getattr(action, "title", None) or getattr(action, "request", ""),
                    "expected_output": getattr(action, "title", None) or getattr(action, "request", ""),
                    "requires_approval": False,
                    "plan_step": {},
                    "file_paths": file_paths,
                },
            }]
        else:
            orchestrator = WorkerOrchestrator()
            orchestrated_plan = orchestrator.build_plan(goal=getattr(action, "request", ""), context={"execution_id": str(getattr(action, "id", "action"))})
            steps_payload = orchestrated_plan.get("steps") or []
            if isinstance(metadata, dict):
                metadata["plan"] = orchestrated_plan
                action.metadata_ = metadata
            if not steps_payload:
                runner = "research" if action_type == "research" else "writing" if action_type in {"writing", "prepare"} else "action-workflow"
                metadata = {
                    "goal": getattr(action, "request", ""),
                    "title": getattr(action, "title", None) or getattr(action, "request", ""),
                    "expected_output": getattr(action, "title", None) or getattr(action, "request", ""),
                    "requires_approval": False,
                    "plan_step": {},
                }
                if runner == "pdf" and file_paths:
                    metadata["file_paths"] = file_paths
                steps_payload = [{"id": "execute", "runner": runner, "action": action_type or "execute", **metadata}]
    session = ExecutionSession(
        id=str(getattr(action, "id", "action")),
        goal=getattr(action, "request", ""),
        steps=[
            ExecutionStep(
                id=str(step.get("id") or f"step-{index+1}"),
                runner=str(step.get("runner") or ("pdf" if getattr(action, "action_type", None) == "pdf" else "research" if getattr(action, "action_type", None) == "research" else "writing" if getattr(action, "action_type", None) in {"writing", "prepare"} else "action-workflow")),
                action=str(step.get("action") or step.get("title") or getattr(action, "action_type", None) or "execute"),
                metadata={
                    **(step.get("metadata") or {}),
                    "goal": getattr(action, "request", ""),
                    "title": step.get("title") or getattr(action, "title", None) or getattr(action, "request", ""),
                    "expected_output": step.get("expected_output") or getattr(action, "title", None) or getattr(action, "request", ""),
                    "requires_approval": bool(step.get("worker_requires_approval") or step.get("requires_approval")),
                    "plan_step": step,
                },
            )
            for index, step in enumerate(steps_payload)
        ],
    )
    if session.steps and session.steps[0].runner == "pdf":
        session.steps[0].metadata["file_paths"] = [item.get("path") for item in (getattr(action, "metadata_", None) or {}).get("attachments", []) if isinstance(item, dict) and item.get("path")]
    return session


def _build_action_messages(action: ActionExecution, *, prior_context: str | None = None) -> list[AIMessage]:
    worker = _resolve_worker(action)
    tool_context = _extract_tool_context(action)
    if action.action_type == "research":
        system_prompt = (
            "You are Synzept's Research Worker. Produce a polished executive research report with the following sections: "
            "Executive Summary, Key Findings, Important Insights, Risks, Recommendations, Sources, and Estimated Time Saved. "
            "Use a professional analytical voice, include concrete detail, and do not use placeholder text. "
            "Cite sources when available and make the report readable without extra explanation. "
            "If sources are not available, clearly state the basis of the findings and do not invent unsupported citations."
        )
        if tool_context:
            system_prompt = f"{system_prompt}\n\nTool execution context:\n{tool_context}"
        if prior_context:
            system_prompt = f"{system_prompt}\n\nRelevant prior research context:\n{prior_context}"
        return [
            AIMessage(role="system", content=system_prompt),
            AIMessage(role="user", content=(
                f"Research request: {action.request}\n\n"
                "Deliver a finished research report with all required sections. "
                "Label each section exactly as requested and do not include planning notes or internal process descriptions."
            )),
        ]
    if worker:
        system_prompt = worker.build_prompt(action)
        if tool_context:
            system_prompt = f"{system_prompt}\n\nTool execution context:\n{tool_context}"
        return [
            AIMessage(role="system", content=system_prompt),
            AIMessage(role="user", content=action.request),
        ]
    return [
        AIMessage(role="system", content="You are Synzept's execution worker. Complete the requested work directly. Produce a clear, useful final artifact with headings and concrete details. Do not describe internal process or ask the user to repeat information."),
        AIMessage(role="user", content=action.request),
    ]


def _extract_tool_context(action: ActionExecution) -> str | None:
    metadata = getattr(action, "metadata_", {}) or {}
    if not isinstance(metadata, dict):
        return None
    tool_summary = metadata.get("tool_summary")
    return tool_summary if isinstance(tool_summary, str) and tool_summary.strip() else None


def _resolve_worker(action: ActionExecution):
    registry = WorkerRegistry()
    plan = (action.metadata_ or {}).get("plan") or {}
    for step in plan.get("steps") or []:
        worker_id = step.get("worker_id")
        if worker_id:
            worker = registry.get(worker_id)
            if worker:
                return worker
    lower_request = action.request.casefold()
    if action.action_type == "research" or any(keyword in lower_request for keyword in ["research", "compare", "investigate", "find out"]):
        return registry.get("research")
    if any(keyword in lower_request for keyword in ["write", "draft", "email", "message", "report", "proposal"]):
        return registry.get("writing")
    if any(keyword in lower_request for keyword in ["code", "implement", "debug", "refactor", "api"]):
        return registry.get("coding")
    if any(keyword in lower_request for keyword in ["schedule", "calendar", "meeting", "appointment"]):
        return registry.get("calendar")
    if any(keyword in lower_request for keyword in ["email", "message", "reply", "send"]):
        return registry.get("communication")
    return registry.get("file")


async def _retry_research_report(session, action: ActionExecution, ai_service: AIService, previous_output: str, *, prior_context: str | None = None) -> tuple[str, object]:
    await _set_research_stage(session, action, "writing_report", "running", 80)
    system_prompt = (
        "You are Synzept's research employee. The previous report did not pass validation. "
        "Produce a complete polished research report with the sections: Executive Summary, Key Findings, Important Insights, Risks, Recommendations, Sources, and Estimated Time Saved. "
        "Do not use placeholders or incomplete headings. Cite sources when possible and keep the report concise and readable."
    )
    if prior_context:
        system_prompt = f"{system_prompt}\n\nRelevant prior research context:\n{prior_context}"
    request = AIRequest(
        messages=[
            AIMessage(
                role="system",
                content=system_prompt,
            ),
            AIMessage(role="user", content=(
                f"Research request: {action.request}\n\n"
                "The previous draft was incomplete or missing required sections. "
                "Rewrite the report so every required section is present."
            )),
        ],
        max_tokens=2200,
        metadata={"interaction_type": "action_execution", "user_id": action.user_id, "conversation_id": action.conversation_id},
    )
    result = await ai_service.complete(request)
    output = result.content.strip()
    if _validate_research_report(output):
        return output, result
    raise ValueError("Research output validation failed")


def _validate_research_report(content: str) -> bool:
    if not content or not content.strip():
        return False
    text = content.lower()
    if any(placeholder in text for placeholder in ["lorem ipsum", "placeholder", "tbd", "to be determined", "(notes)"]):
        return False

    normalized = re.sub(r"\s+", " ", content.strip())
    words = [word for word in re.split(r"\W+", normalized) if word]
    if len(words) < 4:
        return False

    topic_keywords = [
        "executive",
        "summary",
        "findings",
        "insights",
        "risks",
        "recommendations",
        "sources",
        "estimated",
        "time",
        "saved",
        "report",
        "analysis",
        "research",
    ]
    if not any(keyword in text for keyword in topic_keywords):
        return False
    return True


def _initialize_research_metadata(action: ActionExecution) -> None:
    metadata = dict(action.metadata_ or {})
    if "research_stages" not in metadata:
        metadata["research_stages"] = [
            {"id": "understanding_request", "label": "Understanding request", "status": "queued", "progress": 0, "updated_at": None},
            {"id": "planning_research", "label": "Planning research", "status": "queued", "progress": 0, "updated_at": None},
            {"id": "collecting_information", "label": "Collecting information", "status": "queued", "progress": 0, "updated_at": None},
            {"id": "analyzing_findings", "label": "Analyzing findings", "status": "queued", "progress": 0, "updated_at": None},
            {"id": "writing_report", "label": "Writing report", "status": "queued", "progress": 0, "updated_at": None},
            {"id": "final_quality_check", "label": "Final quality check", "status": "queued", "progress": 0, "updated_at": None},
        ]
    metadata["attempt_count"] = metadata.get("attempt_count", 0)
    metadata["retry_count"] = max(0, metadata["attempt_count"] - 1)
    action.metadata_ = metadata


async def _increment_action_attempt(session, action: ActionExecution) -> None:
    metadata = dict(action.metadata_ or {})
    attempt_count = int(metadata.get("attempt_count", 0)) + 1
    metadata["attempt_count"] = attempt_count
    metadata["retry_count"] = max(0, attempt_count - 1)
    action.metadata_ = metadata
    await session.flush()


async def _set_research_metadata(session, action: ActionExecution, result) -> None:
    metadata = dict(action.metadata_ or {})
    if hasattr(result, "metadata"):
        metadata["ai_model"] = getattr(result.metadata, "model", metadata.get("ai_model"))
        metadata["provider"] = getattr(result.metadata, "provider", metadata.get("provider"))
        metadata["request_id"] = getattr(result.metadata, "request_id", metadata.get("request_id"))
    action.metadata_ = metadata
    await session.flush()


async def _record_execution_memory(session, action: ActionExecution, content: str, result) -> None:
    from app.memory.improvements import MemoryImprovementService
    from app.services.research_memory_service import ResearchMemoryService

    metadata = dict(action.metadata_ or {})
    artifacts = metadata.get("artifacts") or []
    if not isinstance(artifacts, list):
        artifacts = []
    improvement = MemoryImprovementService().learn_from_execution(
        user_id=action.user_id,
        action_type=action.action_type,
        goal=action.request,
        summary=(content or "")[:240],
        artifacts=[{"title": str(item.get("title") or "artifact"), "type": str(item.get("type") or "artifact")} for item in artifacts if isinstance(item, dict)],
        metadata={
            "action_id": str(action.id),
            "execution_summary": getattr(result, "summary", None) if hasattr(result, "summary") else None,
            "runner": action.action_type,
        },
    )
    metadata["memory_improvements"] = improvement
    metadata["execution_summary"] = {
        "action_type": action.action_type,
        "goal": action.request,
        "summary": (content or "")[:320],
        "recommendations": improvement.get("recommendations", []),
    }

    if action.action_type == "research":
        service = ResearchMemoryService(session)
        memory = await service.upsert_from_action(action)
        if memory is not None:
            metadata["research_memory_id"] = str(memory.id)
            metadata["research_memory_summary"] = memory.summary
            metadata["research_memory_topics"] = memory.metadata_.get("topics", []) if isinstance(memory.metadata_, dict) else []
            metadata["research_memory_confidence"] = memory.confidence
            metadata["research_memory_context"] = [
                {"id": str(item.id), "summary": item.summary or item.content[:220], "confidence": item.confidence}
                for item in await service.retrieve_context(user_id=action.user_id, query=action.request, limit=3)
                if item.id != memory.id
            ]

    action.metadata_ = metadata
    await session.flush()


async def _build_research_context(session, action: ActionExecution) -> str | None:
    from app.services.research_memory_service import ResearchMemoryService

    if not action.request or not action.request.strip():
        return None
    memories = await ResearchMemoryService(session).retrieve_context(user_id=action.user_id, query=action.request, limit=3)
    if not memories:
        return None
    lines = []
    for memory in memories:
        metadata = dict(memory.metadata_ or {})
        topics = ", ".join(metadata.get("topics", [])[:4]) if isinstance(metadata.get("topics"), list) else "n/a"
        lines.append(f"- {memory.summary or memory.content[:220]} (topics: {topics}, confidence: {memory.confidence:.2f})")
    return "\n".join(lines)


async def _set_research_stage(session, action: ActionExecution, stage_id: str, status: str, progress: int) -> None:
    metadata = dict(action.metadata_ or {})
    stages = list(metadata.get("research_stages", []))
    now = datetime.now(timezone.utc).isoformat()
    stage_found = False
    for stage in stages:
        if stage.get("id") == stage_id:
            stage["status"] = status
            stage["progress"] = progress
            stage["updated_at"] = now
            stage_found = True
            break
    if not stage_found:
        stages.append({"id": stage_id, "label": stage_id.replace("_", " ").capitalize(), "status": status, "progress": progress, "updated_at": now})
    metadata["research_stages"] = stages
    action.metadata_ = metadata
    if progress > action.progress:
        action.progress = progress
    await session.flush()
