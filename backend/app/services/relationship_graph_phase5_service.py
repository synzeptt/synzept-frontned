from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.relationship_graph_phase5 import RelationshipEdge, RelationshipNode
from app.schemas.relationship_graph_phase5 import (
    RelationshipEdgeCreate,
    RelationshipEdgeUpdate,
    RelationshipNodeCreate,
    RelationshipNodeUpdate,
)


class RelationshipGraphPhase5Service:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def graph(self, user_id: UUID) -> dict:
        return {"nodes": [self._node_out(item) for item in await self.list_nodes(user_id)], "edges": [self._edge_out(item) for item in await self.list_edges(user_id)]}

    async def list_nodes(self, user_id: UUID) -> list[RelationshipNode]:
        result = await self.session.execute(
            select(RelationshipNode).where(RelationshipNode.user_id == user_id).order_by(RelationshipNode.created_at.desc())
        )
        return list(result.scalars())

    async def get_node(self, user_id: UUID, node_id: UUID) -> RelationshipNode:
        result = await self.session.execute(
            select(RelationshipNode).where(RelationshipNode.id == node_id, RelationshipNode.user_id == user_id)
        )
        node = result.scalar_one_or_none()
        if not node:
            raise NotFoundError("Relationship node not found")
        return node

    async def node_for_entity(self, user_id: UUID, node_type: str, entity_id: UUID) -> dict:
        result = await self.session.execute(
            select(RelationshipNode).where(
                RelationshipNode.user_id == user_id,
                RelationshipNode.node_type == node_type,
                RelationshipNode.entity_id == entity_id,
            )
        )
        node = result.scalar_one_or_none()
        if not node:
            raise NotFoundError("Relationship node not found")
        return await self.neighborhood(user_id, node.id)

    async def create_node(self, user_id: UUID, data: RelationshipNodeCreate) -> dict:
        node = RelationshipNode(
            user_id=user_id,
            node_type=data.nodeType,
            entity_id=data.entityId,
            title=data.title.strip(),
            description=data.description.strip(),
        )
        self.session.add(node)
        await self.session.flush()
        return self._node_out(node)

    async def update_node(self, user_id: UUID, node_id: UUID, data: RelationshipNodeUpdate) -> dict:
        node = await self.get_node(user_id, node_id)
        if data.title is not None:
            node.title = data.title.strip()
        if data.description is not None:
            node.description = data.description.strip()
        node.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._node_out(node)

    async def delete_node(self, user_id: UUID, node_id: UUID) -> None:
        await self.session.delete(await self.get_node(user_id, node_id))

    async def list_edges(self, user_id: UUID) -> list[RelationshipEdge]:
        result = await self.session.execute(
            select(RelationshipEdge).where(RelationshipEdge.user_id == user_id).order_by(RelationshipEdge.created_at.desc())
        )
        return list(result.scalars())

    async def get_edge(self, user_id: UUID, edge_id: UUID) -> RelationshipEdge:
        result = await self.session.execute(
            select(RelationshipEdge).where(RelationshipEdge.id == edge_id, RelationshipEdge.user_id == user_id)
        )
        edge = result.scalar_one_or_none()
        if not edge:
            raise NotFoundError("Relationship edge not found")
        return edge

    async def create_edge(self, user_id: UUID, data: RelationshipEdgeCreate) -> dict:
        await self.get_node(user_id, data.sourceNodeId)
        await self.get_node(user_id, data.targetNodeId)
        edge = RelationshipEdge(
            user_id=user_id,
            source_node_id=data.sourceNodeId,
            target_node_id=data.targetNodeId,
            relationship_type=data.relationshipType.strip(),
            reason=data.reason.strip(),
            strength=data.strength,
        )
        self.session.add(edge)
        await self.session.flush()
        return self._edge_out(edge)

    async def update_edge(self, user_id: UUID, edge_id: UUID, data: RelationshipEdgeUpdate) -> dict:
        edge = await self.get_edge(user_id, edge_id)
        if data.relationshipType is not None:
            edge.relationship_type = data.relationshipType.strip()
        if data.reason is not None:
            edge.reason = data.reason.strip()
        if data.strength is not None:
            edge.strength = data.strength
        edge.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._edge_out(edge)

    async def delete_edge(self, user_id: UUID, edge_id: UUID) -> None:
        await self.session.delete(await self.get_edge(user_id, edge_id))

    async def neighborhood(self, user_id: UUID, node_id: UUID) -> dict:
        node = await self.get_node(user_id, node_id)
        edge_result = await self.session.execute(
            select(RelationshipEdge).where(
                RelationshipEdge.user_id == user_id,
                or_(RelationshipEdge.source_node_id == node_id, RelationshipEdge.target_node_id == node_id),
            )
        )
        edges = list(edge_result.scalars())
        related_ids = {
            edge.target_node_id if edge.source_node_id == node_id else edge.source_node_id
            for edge in edges
        }
        nodes: list[RelationshipNode] = []
        if related_ids:
            node_result = await self.session.execute(
                select(RelationshipNode).where(RelationshipNode.user_id == user_id, RelationshipNode.id.in_(related_ids))
            )
            nodes = list(node_result.scalars())
        return {
            "node": self._node_out(node),
            "relatedNodes": [self._node_out(item) for item in nodes],
            "edges": [self._edge_out(item) for item in edges],
        }

    @staticmethod
    def _node_out(node: RelationshipNode) -> dict:
        return {
            "id": node.id,
            "userId": node.user_id,
            "nodeType": node.node_type,
            "entityId": node.entity_id,
            "title": node.title,
            "description": node.description or "",
            "createdAt": node.created_at,
            "updatedAt": node.updated_at,
        }

    @staticmethod
    def _edge_out(edge: RelationshipEdge) -> dict:
        return {
            "id": edge.id,
            "userId": edge.user_id,
            "sourceNodeId": edge.source_node_id,
            "targetNodeId": edge.target_node_id,
            "relationshipType": edge.relationship_type,
            "reason": edge.reason or "",
            "strength": edge.strength,
            "createdAt": edge.created_at,
            "updatedAt": edge.updated_at,
        }
