from fastapi import APIRouter

from app.schemas.onboarding_wow import OnboardingWowAdvanceIn, OnboardingWowAdvanceOut, OnboardingWowStartOut
from app.services.onboarding_wow_service import OnboardingWowService

router = APIRouter(prefix="/api/internal/onboarding-wow")


@router.get("/start", response_model=OnboardingWowStartOut)
async def start_onboarding_wow():
    return OnboardingWowService().start()


@router.post("/advance", response_model=OnboardingWowAdvanceOut)
async def advance_onboarding_wow(payload: OnboardingWowAdvanceIn):
    return OnboardingWowService().advance(payload)


@router.post("/approve")
async def approve_onboarding_wow():
    return OnboardingWowService().approve()
