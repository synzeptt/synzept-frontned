from fastapi import APIRouter

from app.schemas.action_center import ActionCenterOut
from app.services.action_center_service import ActionCenterService

router = APIRouter(prefix="/api/internal/action-center")


@router.get("", response_model=ActionCenterOut)
async def action_center_dashboard():
    return ActionCenterService().get_dashboard()
