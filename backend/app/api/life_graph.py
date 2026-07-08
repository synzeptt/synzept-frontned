from fastapi import APIRouter, Query

from app.schemas.life_graph import LifeGraphExplorationOut
from app.services.life_graph_service import LifeGraphService

router = APIRouter(prefix="/api/internal/life-graph")


@router.get("/explore", response_model=LifeGraphExplorationOut)
async def explore_graph(
    query: str = Query(default=""),
    entity_type: str | None = Query(default=None),
    node_id: str | None = Query(default=None),
):
    return LifeGraphService().explore(query=query, entity_type=entity_type, node_id=node_id)
