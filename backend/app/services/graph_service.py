from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.graph import GraphEdge, GraphNode
from app.schemas.core import GraphEdgeCreate, GraphEdgeUpdate, GraphNodeCreate, GraphNodeUpdate


class GraphService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_nodes(self, user_id: UUID) -> list[GraphNode]:
        result = await self.session.execute(select(GraphNode).where(GraphNode.user_id == user_id).order_by(GraphNode.created_at.desc()))
        return list(result.scalars())

    async def get_node(self, user_id: UUID, item_id: UUID) -> GraphNode:
        result = await self.session.execute(select(GraphNode).where(GraphNode.id == item_id, GraphNode.user_id == user_id))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Graph node not found")
        return item

    async def create_node(self, user_id: UUID, data: GraphNodeCreate) -> GraphNode:
        item = GraphNode(user_id=user_id, **data.model_dump())
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_node(self, user_id: UUID, item_id: UUID, data: GraphNodeUpdate) -> GraphNode:
        item = await self.get_node(user_id, item_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def delete_node(self, user_id: UUID, item_id: UUID) -> None:
        await self.session.delete(await self.get_node(user_id, item_id))

    async def list_edges(self, user_id: UUID) -> list[GraphEdge]:
        result = await self.session.execute(select(GraphEdge).where(GraphEdge.user_id == user_id).order_by(GraphEdge.created_at.desc()))
        return list(result.scalars())

    async def get_edge(self, user_id: UUID, item_id: UUID) -> GraphEdge:
        result = await self.session.execute(select(GraphEdge).where(GraphEdge.id == item_id, GraphEdge.user_id == user_id))
        item = result.scalar_one_or_none()
        if not item:
            raise NotFoundError("Graph edge not found")
        return item

    async def create_edge(self, user_id: UUID, data: GraphEdgeCreate) -> GraphEdge:
        await self.get_node(user_id, data.source_node_id)
        await self.get_node(user_id, data.target_node_id)
        item = GraphEdge(user_id=user_id, **data.model_dump())
        self.session.add(item)
        await self.session.flush()
        return item

    async def update_edge(self, user_id: UUID, item_id: UUID, data: GraphEdgeUpdate) -> GraphEdge:
        item = await self.get_edge(user_id, item_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await self.session.flush()
        return item

    async def delete_edge(self, user_id: UUID, item_id: UUID) -> None:
        await self.session.delete(await self.get_edge(user_id, item_id))
