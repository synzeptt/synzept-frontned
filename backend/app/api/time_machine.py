from fastapi import APIRouter, Query

from app.schemas.time_machine import (
    TimeMachineComparisonOut,
    TimeMachineReflectionOut,
    TimeMachineSearchResultOut,
    TimeMachineTimelineEntryOut,
    TimeMachineTurningPointOut,
)
from app.services.time_machine_service import TimeMachineService

router = APIRouter(prefix="/api/internal/time-machine")


@router.get("/journey", response_model=list[TimeMachineTimelineEntryOut])
async def journey(kind: str | None = None, query: str = Query(default="")):
    return TimeMachineService().journey(kind=kind, query=query)


@router.get("/turning-points", response_model=list[TimeMachineTurningPointOut])
async def turning_points():
    return TimeMachineService().turning_points()


@router.get("/reflections", response_model=list[TimeMachineReflectionOut])
async def reflections():
    return TimeMachineService().reflections()


@router.get("/compare", response_model=list[TimeMachineComparisonOut])
async def compare():
    return TimeMachineService().compare()


@router.get("/search", response_model=list[TimeMachineSearchResultOut])
async def search(query: str = Query(default="")):
    return TimeMachineService().search(query=query)
