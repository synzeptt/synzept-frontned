from fastapi import APIRouter

from app.schemas.learning_evaluation import (
    FeedbackIn,
    LearningEvaluationDashboardOut,
    OutcomeOut,
    RecordOutcomeIn,
    RecordRecommendationIn,
    RecommendationOut,
)
from app.services.learning_evaluation import LearningEvaluationService

router = APIRouter(prefix="/api/learning-evaluation", tags=["learning-evaluation"])


@router.get("", response_model=LearningEvaluationDashboardOut)
async def dashboard():
    return LearningEvaluationService().dashboard()


@router.get("/recommendations", response_model=list[RecommendationOut])
async def recommendations():
    return LearningEvaluationService().recommendations()


@router.post("/recommendations", response_model=RecommendationOut)
async def record_recommendation(body: RecordRecommendationIn):
    return LearningEvaluationService().record_recommendation(body)


@router.post("/recommendations/{recommendation_id}/outcome", response_model=OutcomeOut)
async def record_outcome(recommendation_id: str, body: RecordOutcomeIn):
    return LearningEvaluationService().record_outcome(recommendation_id, body)


@router.post("/recommendations/{recommendation_id}/feedback", response_model=dict)
async def record_feedback(recommendation_id: str, body: FeedbackIn):
    return LearningEvaluationService().feedback(recommendation_id, body)
