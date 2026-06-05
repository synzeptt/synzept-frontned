from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.project_intelligence_phase2 import (
    DecisionCreate,
    DecisionOut,
    DecisionUpdate,
    OpenLoopCreate,
    OpenLoopOut,
    OpenLoopUpdate,
    ProjectCreatePhase2,
    ProjectOutPhase2,
    ProjectUpdatePhase2,
)
from app.services.project_intelligence_phase2_service import ProjectIntelligencePhase2Service

router = APIRouter(prefix="/api")


@router.get("/projects", response_model=list[ProjectOutPhase2])
async def list_projects(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProjectIntelligencePhase2Service(session).list_projects(user.id)


@router.post("/projects", response_model=ProjectOutPhase2)
async def create_project(
    body: ProjectCreatePhase2,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligencePhase2Service(session).create_project(user.id, body)


@router.get("/projects/{project_id}", response_model=ProjectOutPhase2)
async def get_project(project_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProjectIntelligencePhase2Service(session).get_project(user.id, project_id)


@router.put("/projects/{project_id}", response_model=ProjectOutPhase2)
async def update_project(
    project_id: UUID,
    body: ProjectUpdatePhase2,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligencePhase2Service(session).update_project(user.id, project_id, body)


@router.delete("/projects/{project_id}")
async def delete_project(project_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await ProjectIntelligencePhase2Service(session).delete_project(user.id, project_id)
    return {"ok": True}


@router.get("/projects/{project_id}/open-loops", response_model=list[OpenLoopOut])
async def list_open_loops(project_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProjectIntelligencePhase2Service(session).list_open_loops(user.id, project_id)


@router.post("/projects/{project_id}/open-loops", response_model=OpenLoopOut)
async def create_open_loop(
    project_id: UUID,
    body: OpenLoopCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligencePhase2Service(session).create_open_loop(user.id, project_id, body)


@router.put("/open-loops/{open_loop_id}", response_model=OpenLoopOut)
async def update_open_loop(
    open_loop_id: UUID,
    body: OpenLoopUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligencePhase2Service(session).update_open_loop(user.id, open_loop_id, body)


@router.delete("/open-loops/{open_loop_id}")
async def delete_open_loop(open_loop_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await ProjectIntelligencePhase2Service(session).delete_open_loop(user.id, open_loop_id)
    return {"ok": True}


@router.get("/projects/{project_id}/decisions", response_model=list[DecisionOut])
async def list_decisions(project_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await ProjectIntelligencePhase2Service(session).list_decisions(user.id, project_id)


@router.post("/projects/{project_id}/decisions", response_model=DecisionOut)
async def create_decision(
    project_id: UUID,
    body: DecisionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligencePhase2Service(session).create_decision(user.id, project_id, body)


@router.put("/decisions/{decision_id}", response_model=DecisionOut)
async def update_decision(
    decision_id: UUID,
    body: DecisionUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligencePhase2Service(session).update_decision(user.id, decision_id, body)


@router.delete("/decisions/{decision_id}")
async def delete_decision(decision_id: UUID, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    await ProjectIntelligencePhase2Service(session).delete_decision(user.id, decision_id)
    return {"ok": True}
