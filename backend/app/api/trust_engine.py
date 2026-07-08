from fastapi import APIRouter

from app.schemas.trust_engine import TrustFeedbackIn, TrustFeedbackOut, TrustRecommendationOut
from app.services.trust_engine_service import TrustEngineService

router = APIRouter(prefix="/api/internal/trust-engine")


@router.get("", response_model=list[TrustRecommendationOut])
async def list_recommendations():
    return TrustEngineService().list_recommendations()


@router.post("/feedback", response_model=TrustFeedbackOut)
async def submit_feedback(payload: TrustFeedbackIn):
    return TrustEngineService().feedback(payload)
