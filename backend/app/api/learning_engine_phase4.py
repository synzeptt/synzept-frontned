from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.learning_engine_phase4 import (
    LearningAnalysisOut,
    LearningEngineOut,
    LearningObservationCreate,
    LearningObservationOut,
)
from app.services.learning_engine_phase4_service import LearningEnginePhase4Service

router = APIRouter(prefix="/api/learning-engine")


@router.get("", response_model=LearningEngineOut)
async def get_learning_engine(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await LearningEnginePhase4Service(session).overview(user.id)


@router.post("/observations", response_model=LearningObservationOut)
async def create_observation(
    body: LearningObservationCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    return await LearningEnginePhase4Service(session).create_observation(user.id, body)


@router.post("/analyze", response_model=LearningAnalysisOut)
async def analyze_learning(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await LearningEnginePhase4Service(session).analyze(user.id)
