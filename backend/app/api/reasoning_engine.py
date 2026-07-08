from fastapi import APIRouter

from app.schemas.reasoning_engine import ReasoningRequestIn, ReasoningResponseOut
from app.services.reasoning_engine import ReasoningEngineService

router = APIRouter(prefix="/api/reasoning-engine", tags=["reasoning-engine"])


@router.get("/examples", response_model=list[dict])
async def reasoning_examples():
    return ReasoningEngineService().examples()


@router.post("/reason", response_model=ReasoningResponseOut)
async def reason(body: ReasoningRequestIn):
    return ReasoningEngineService().reason(body)
