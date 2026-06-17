from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.agent_memory import AgentMemoryTimelineOut
from app.services.agent_memory_service import AgentMemoryService

router = APIRouter(prefix="/agent-memory")


@router.get("/timeline", response_model=AgentMemoryTimelineOut)
async def memory_timeline(
    days: int = Query(default=90, ge=1, le=365),
    limit: int = Query(default=80, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await AgentMemoryService(session).timeline(user.id, days=days, limit=limit)
