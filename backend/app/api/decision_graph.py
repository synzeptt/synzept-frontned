from fastapi import APIRouter

from app.schemas.decision_graph import DecisionGraphChainOut, DecisionGraphInsightOut, DecisionGraphNodeOut, DecisionGraphOut
from app.services.decision_graph import DecisionGraphService

router = APIRouter(prefix="/api/internal/decision-graph")


@router.get("", response_model=DecisionGraphOut)
async def decision_graph(relationship: str | None = None):
    return DecisionGraphService().graph(relationship=relationship)


@router.get("/nodes/decisions", response_model=list[DecisionGraphNodeOut])
async def decision_nodes():
    return DecisionGraphService().decision_nodes()


@router.get("/nodes/{node_id}", response_model=DecisionGraphOut)
async def node_neighborhood(node_id: str):
    return DecisionGraphService().node_neighborhood(node_id)


@router.get("/insights", response_model=list[DecisionGraphInsightOut])
async def graph_insights():
    return DecisionGraphService().insights()


@router.get("/chains", response_model=list[DecisionGraphChainOut])
async def graph_chains():
    return DecisionGraphService().chains()
