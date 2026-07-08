from fastapi import APIRouter, Query

from app.schemas.opportunity import OpportunityFeedbackOut, OpportunityOut, OpportunityScoreBreakdownOut
from app.services.opportunity_service import OpportunityEngineService

router = APIRouter(prefix="/api/internal/opportunities")


@router.get("", response_model=list[OpportunityOut])
async def current_opportunities(limit: int = Query(default=5, ge=1, le=10)):
    return OpportunityEngineService().current_opportunities(limit=limit)


@router.get("/history")
async def opportunity_history():
    return {"history": OpportunityEngineService().history_items()}


@router.post("/feedback", response_model=dict)
async def opportunity_feedback(body: OpportunityFeedbackOut):
    return OpportunityEngineService().feedback(body.opportunityId, body.action, body.note)


@router.get("/score-breakdown/{opportunity_id}", response_model=OpportunityScoreBreakdownOut | None)
async def opportunity_score_breakdown(opportunity_id: str):
    return OpportunityEngineService().score_breakdown(opportunity_id)
