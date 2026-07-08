from fastapi import APIRouter

from app.schemas.intelligence_loop import (
    ActionApprovalIn,
    IntelligenceEventOut,
    IntelligenceLoopSnapshotOut,
    LearningOutcomeIn,
    LearningOutcomeOut,
    PredictionOut,
    RecommendationOut,
    UserModelOut,
)
from app.services.intelligence_loop import IntelligenceLoopService

router = APIRouter(prefix="/api/internal/intelligence-loop")


@router.get("", response_model=IntelligenceLoopSnapshotOut)
async def intelligence_loop_snapshot():
    return IntelligenceLoopService().snapshot()


@router.post("/observe", response_model=dict)
async def observe_event(event: IntelligenceEventOut):
    return IntelligenceLoopService().observe_event(event)


@router.get("/understand", response_model=UserModelOut)
async def user_model():
    return IntelligenceLoopService().snapshot().userModel


@router.get("/predict", response_model=list[PredictionOut])
async def predictions():
    return IntelligenceLoopService().snapshot().predictions


@router.get("/recommend", response_model=list[RecommendationOut])
async def recommendations():
    return IntelligenceLoopService().snapshot().recommendations


@router.post("/act/approval", response_model=dict)
async def action_approval(body: ActionApprovalIn):
    return IntelligenceLoopService().record_approval(body)


@router.post("/learn", response_model=LearningOutcomeOut)
async def learning_outcome(body: LearningOutcomeIn):
    return IntelligenceLoopService().record_outcome(body)
