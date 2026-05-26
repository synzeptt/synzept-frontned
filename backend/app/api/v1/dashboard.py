from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.dashboard import DashboardOut
from app.services.dashboard import DashboardAggregationService

router = APIRouter(prefix="/dashboard")


@router.get("", response_model=DashboardOut)
async def get_dashboard(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await DashboardAggregationService(session).get_dashboard(user)
