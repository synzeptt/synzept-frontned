from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_pro_user
from app.models.user import User
from app.schemas.relationship_graph_phase5 import (
    RelationshipEdgeCreate,
    RelationshipEdgeOut,
    RelationshipEdgeUpdate,
    RelationshipGraphOut,
    RelationshipNeighborhoodOut,
    RelationshipNodeCreate,
    RelationshipNodeOut,
    RelationshipNodeUpdate,
)
from app.services.relationship_graph_phase5_service import RelationshipGraphPhase5Service

router = APIRouter(prefix="/api/relationship-graph")


@router.get("", response_model=RelationshipGraphOut)
async def get_graph(user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    return await RelationshipGraphPhase5Service(session).graph(user.id)


@router.post("/refresh", response_model=RelationshipGraphOut)
async def refresh_graph(user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    return await RelationshipGraphPhase5Service(session).refresh(user.id)


@router.get("/insights")
async def graph_insights(user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    return {"insights": await RelationshipGraphPhase5Service(session).insights(user.id)}


@router.get("/nodes", response_model=list[RelationshipNodeOut])
async def list_nodes(user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    nodes = await RelationshipGraphPhase5Service(session).list_nodes(user.id)
    return [RelationshipGraphPhase5Service._node_out(item) for item in nodes]


@router.post("/nodes", response_model=RelationshipNodeOut)
async def create_node(
    body: RelationshipNodeCreate,
    user: User = Depends(require_pro_user),
    session: AsyncSession = Depends(get_db),
):
    return await RelationshipGraphPhase5Service(session).create_node(user.id, body)


@router.get("/nodes/{node_id}", response_model=RelationshipNeighborhoodOut)
async def get_node(node_id: UUID, user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    return await RelationshipGraphPhase5Service(session).neighborhood(user.id, node_id)


@router.put("/nodes/{node_id}", response_model=RelationshipNodeOut)
async def update_node(
    node_id: UUID,
    body: RelationshipNodeUpdate,
    user: User = Depends(require_pro_user),
    session: AsyncSession = Depends(get_db),
):
    return await RelationshipGraphPhase5Service(session).update_node(user.id, node_id, body)


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: UUID, user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    await RelationshipGraphPhase5Service(session).delete_node(user.id, node_id)
    return {"ok": True}


@router.get("/edges", response_model=list[RelationshipEdgeOut])
async def list_edges(user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    edges = await RelationshipGraphPhase5Service(session).list_edges(user.id)
    return [RelationshipGraphPhase5Service._edge_out(item) for item in edges]


@router.post("/edges", response_model=RelationshipEdgeOut)
async def create_edge(
    body: RelationshipEdgeCreate,
    user: User = Depends(require_pro_user),
    session: AsyncSession = Depends(get_db),
):
    return await RelationshipGraphPhase5Service(session).create_edge(user.id, body)


@router.put("/edges/{edge_id}", response_model=RelationshipEdgeOut)
async def update_edge(
    edge_id: UUID,
    body: RelationshipEdgeUpdate,
    user: User = Depends(require_pro_user),
    session: AsyncSession = Depends(get_db),
):
    return await RelationshipGraphPhase5Service(session).update_edge(user.id, edge_id, body)


@router.delete("/edges/{edge_id}")
async def delete_edge(edge_id: UUID, user: User = Depends(require_pro_user), session: AsyncSession = Depends(get_db)):
    await RelationshipGraphPhase5Service(session).delete_edge(user.id, edge_id)
    return {"ok": True}


@router.get("/entity/{node_type}/{entity_id}", response_model=RelationshipNeighborhoodOut)
async def get_entity_neighborhood(
    node_type: str,
    entity_id: UUID,
    user: User = Depends(require_pro_user),
    session: AsyncSession = Depends(get_db),
):
    return await RelationshipGraphPhase5Service(session).node_for_entity(user.id, node_type, entity_id)
