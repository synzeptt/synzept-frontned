from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.project_intelligence import (
    ProjectDecisionCreate,
    ProjectDecisionOut,
    ProjectDecisionUpdate,
    ProjectIntelligenceOut,
    ProjectIntelligencePageOut,
    ProjectIntelligenceUpdate,
    ProjectOpenLoopCreate,
    ProjectOpenLoopOut,
    ProjectOpenLoopUpdate,
)
from app.services.project_intelligence_service import ProjectIntelligenceService

router = APIRouter(prefix="/projects/{project_id}/intelligence")


@router.get("", response_model=ProjectIntelligencePageOut)
async def get_project_intelligence(
    project_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligenceService(session).get_page(user.id, project_id)


@router.patch("", response_model=ProjectIntelligenceOut)
async def update_project_intelligence(
    project_id: UUID,
    body: ProjectIntelligenceUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligenceService(session).update_intelligence(user.id, project_id, body)


@router.post("/decisions", response_model=ProjectDecisionOut)
async def create_decision(
    project_id: UUID,
    body: ProjectDecisionCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligenceService(session).create_decision(user.id, project_id, body)


@router.patch("/decisions/{decision_id}", response_model=ProjectDecisionOut)
async def update_decision(
    project_id: UUID,
    decision_id: UUID,
    body: ProjectDecisionUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligenceService(session).update_decision(user.id, project_id, decision_id, body)


@router.post("/open-loops", response_model=ProjectOpenLoopOut)
async def create_open_loop(
    project_id: UUID,
    body: ProjectOpenLoopCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligenceService(session).create_loop(user.id, project_id, body)


@router.patch("/open-loops/{loop_id}", response_model=ProjectOpenLoopOut)
async def update_open_loop(
    project_id: UUID,
    loop_id: UUID,
    body: ProjectOpenLoopUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await ProjectIntelligenceService(session).update_loop(user.id, project_id, loop_id, body)
