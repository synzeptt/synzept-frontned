"""End-to-end execution API endpoints with automatic orchestration."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.user import User
from app.services.execution_persistence_service import ExecutionPersistenceService
from app.services.execution_orchestration_service import ExecutionOrchestrationService
from app.execution.engine import ExecutionEngine, RunnerRegistry
from app.execution.skill_executor import register_skill_runner
from app.execution.artifacts import ArtifactService
from app.execution.runners import BrowserRunner, CalendarRunner, CommunicationRunner, FileRunner, ResearchRunner, WritingRunner
from app.connectors.manager import ConnectorManager
from app.core.reliability import safe_error_message

router = APIRouter(prefix="/execute", tags=["execution"])


def get_execution_service(
    session: AsyncSession = Depends(get_db),
) -> ExecutionOrchestrationService:
    """Get the execution orchestration service."""
    # Initialize persistence service
    persistence_service = ExecutionPersistenceService(session)
    
    # Initialize execution engine with persistence
    runners = RunnerRegistry()
    runners.register("browser", BrowserRunner(artifact_service=ArtifactService(session)))
    artifact_service = ArtifactService(session)
    connector_manager = ConnectorManager(dependencies={"session": session})
    register_skill_runner(runners, "research", "research", ResearchRunner(artifact_service=artifact_service))
    register_skill_runner(runners, "writing", None, WritingRunner(artifact_service=artifact_service, connector_manager=connector_manager))
    register_skill_runner(runners, "communication", "email", CommunicationRunner(artifact_service=artifact_service, connector_manager=connector_manager))
    register_skill_runner(runners, "calendar", None, CalendarRunner(artifact_service=artifact_service, connector_manager=connector_manager))
    register_skill_runner(runners, "file", None, FileRunner(artifact_service=artifact_service, connector_manager=connector_manager))
    engine = ExecutionEngine(runners, persistence_service=persistence_service)
    
    # Return orchestration service
    return ExecutionOrchestrationService(
        engine=engine,
        persistence_service=persistence_service,
        session=session,
    )


@router.post("/goal")
async def execute_goal(
    goal: str,
    workflow_type: str | None = None,
    clarification_answers: dict[str, str] | None = None,
    user: User = Depends(get_current_user),
    service: ExecutionOrchestrationService = Depends(get_execution_service),
):
    """
    Execute a user goal end-to-end with automatic:
    - Planning and workflow inference
    - Execution with browser and connectors
    - Timeline and metrics recording
    - Artifact generation
    - Completion and persistence
    """
    try:
        result = await service.execute_goal(
            user_id=user.id,
            goal=goal,
            workflow_type=workflow_type,
            clarification_answers=clarification_answers or {},
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message("internal_error")) from exc


@router.post("/resume/{execution_id}")
async def resume_execution(
    execution_id: str,
    approval_decision: str | None = None,
    user: User = Depends(get_current_user),
    service: ExecutionOrchestrationService = Depends(get_execution_service),
):
    """Resume a previously interrupted execution."""
    try:
        result = await service.resume_execution(
            user_id=user.id,
            execution_id=execution_id,
            approval_decision=approval_decision,
        )
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Execution not found")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message("internal_error")) from exc


@router.get("/status/{execution_id}")
async def get_execution_status(
    execution_id: str,
    user: User = Depends(get_current_user),
    service: ExecutionOrchestrationService = Depends(get_execution_service),
):
    """Get current status of an execution with timeline and metrics."""
    try:
        result = await service.get_execution_status(
            user_id=user.id,
            execution_id=execution_id,
        )
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail="Execution not found")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=safe_error_message("internal_error")) from exc
