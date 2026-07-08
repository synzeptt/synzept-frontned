from fastapi import APIRouter

from app.services.coach.service import CoachService

router = APIRouter(prefix="/api/internal/coach")


@router.get("/morning")
async def morning_brief():
    return CoachService().get_morning_brief()


@router.get("/midday")
async def midday_checkin():
    return CoachService().get_midday_checkin()


@router.get("/evening")
async def evening_reflection():
    return CoachService().get_evening_reflection()


@router.get("/weekly")
async def weekly_summary():
    return CoachService().get_weekly_summary()


@router.get("/state")
async def coaching_state():
    return CoachService().get_coaching_state()
