from fastapi import APIRouter, Query

from app.schemas.decision_intelligence import (
    DecisionDetectionOut,
    DecisionDNATraitOut,
    DecisionIntelligenceOut,
    DecisionOutcomeAnalysisOut,
    DecisionRecordOut,
    DecisionRecommendationOut,
    DecisionReviewOut,
    DecisionReviewUpdateIn,
)
from app.services.decision_intelligence import DecisionIntelligenceService

router = APIRouter(prefix="/api/internal/decision-intelligence")


@router.get("", response_model=DecisionIntelligenceOut)
async def decision_intelligence_snapshot():
    return DecisionIntelligenceService().snapshot()


@router.get("/detect", response_model=list[DecisionDetectionOut])
async def detect_decisions(min_confidence: float = Query(default=0.75, ge=0, le=1)):
    return DecisionIntelligenceService().detection_candidates(min_confidence=min_confidence)


@router.get("/decisions", response_model=list[DecisionRecordOut])
async def decisions(status: str | None = None):
    return DecisionIntelligenceService().decisions(status=status)


@router.get("/decisions/{decision_id}", response_model=DecisionRecordOut | None)
async def decision_detail(decision_id: str):
    return DecisionIntelligenceService().decision_detail(decision_id)


@router.get("/reviews", response_model=list[DecisionReviewOut])
async def decision_reviews():
    return DecisionIntelligenceService().reviews()


@router.post("/reviews/update", response_model=dict)
async def update_decision_review(body: DecisionReviewUpdateIn):
    return DecisionIntelligenceService().update_review(body)


@router.get("/outcomes", response_model=list[DecisionOutcomeAnalysisOut])
async def decision_outcomes():
    return DecisionIntelligenceService().outcome_analyses()


@router.get("/dna", response_model=list[DecisionDNATraitOut])
async def decision_dna():
    return DecisionIntelligenceService().decision_dna()


@router.get("/recommendations", response_model=list[DecisionRecommendationOut])
async def decision_recommendations():
    return DecisionIntelligenceService().recommendations()
