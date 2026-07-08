from fastapi import APIRouter, Query

from app.schemas.memory_feed import MemoryFeedOut
from app.services.memory_feed.service import MemoryFeedService

router = APIRouter(prefix="/api/internal/memory-feed")


@router.get("", response_model=MemoryFeedOut)
async def get_memory_feed(limit: int = Query(default=7, ge=5, le=7)):
    return MemoryFeedService().get_feed(limit=limit)


@router.post("/refresh", response_model=MemoryFeedOut)
async def refresh_memory_feed(limit: int = Query(default=7, ge=5, le=7)):
    return MemoryFeedService().refresh_feed(limit=limit)
