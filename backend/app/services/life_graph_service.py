from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.schemas.life_graph import LifeGraphEntityOut, LifeGraphExplorationOut, LifeGraphPathOut, LifeGraphRelationshipOut
from app.services.life_graph_mock_data import MOCK_LIFE_GRAPH


class RelationshipInferenceService:
    def infer(self, entities: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
        inferred: list[dict[str, Any]] = []
        entity_by_id = {entity["id"]: entity for entity in entities}

        for entity in entities:
            if entity["type"] == "Task" and entity.get("metadata", {}).get("projectId"):
                inferred.append(
                    {
                        "id": f"inferred-{entity['id']}-project",
                        "source": entity["id"],
                        "target": entity["metadata"]["projectId"],
                        "type": "belongs_to",
                        "direction": "outgoing",
                        "strength": 0.9,
                        "evidence": "Task created inside project",
                    }
                )
            if entity["type"] == "Memory" and entity.get("metadata", {}).get("conversationId"):
                inferred.append(
                    {
                        "id": f"inferred-{entity['id']}-conversation",
                        "source": entity["id"],
                        "target": entity["metadata"]["conversationId"],
                        "type": "mentioned_in",
                        "direction": "outgoing",
                        "strength": 0.88,
                        "evidence": "Memory originated from the conversation",
                    }
                )
            if entity["type"] == "Decision" and entity.get("metadata", {}).get("missionId"):
                inferred.append(
                    {
                        "id": f"inferred-{entity['id']}-mission",
                        "source": entity["id"],
                        "target": entity["metadata"]["missionId"],
                        "type": "belongs_to",
                        "direction": "outgoing",
                        "strength": 0.87,
                        "evidence": "Decision impacts the mission",
                    }
                )

        existing = {(relationship["source"], relationship["target"], relationship["type"]) for relationship in relationships}
        return [item for item in inferred if (item["source"], item["target"], item["type"]) not in existing]


class GraphIntelligenceService:
    def explain_link(self, source: dict[str, Any], target: dict[str, Any], relationship: dict[str, Any]) -> str:
        return f"{source['title']} is linked to {target['title']} through {relationship['type']} because {relationship['evidence']}."

    def hidden_connections(self, entities: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> list[str]:
        return [
            f"{entity['title']} appears to connect to the wider operating system through shared context."
            for entity in entities[:3]
        ]

    def recommend_missing_links(self, entities: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> list[str]:
        return [
            "Connect the onboarding note to the daily activation goal for stronger context.",
            "Link the product review event to the mission for easier historical tracing.",
        ]

    def detect_duplicates(self, entities: list[dict[str, Any]]) -> list[str]:
        titles = defaultdict(list)
        for entity in entities:
            titles[entity["title"].lower()].append(entity["id"])
        return [f"Possible duplicate cluster: {title}" for title, ids in titles.items() if len(ids) > 1]


class LifeGraphService:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = data or MOCK_LIFE_GRAPH
        self.entities = list(self.data.get("entities", []))
        self.relationships = list(self.data.get("relationships", []))
        self.inference = RelationshipInferenceService()
        self.intelligence = GraphIntelligenceService()
        self._hydrate_relationships()

    def _hydrate_relationships(self) -> None:
        inferred = self.inference.infer(self.entities, self.relationships)
        self.relationships.extend(inferred)

    def explore(self, *, query: str = "", entity_type: str | None = None, node_id: str | None = None) -> LifeGraphExplorationOut:
        entities = self._filter_entities(query=query, entity_type=entity_type)
        if node_id:
            entities = [entity for entity in entities if entity["id"] == node_id] or [self._entity(node_id)]
        adjacent_ids = self._adjacent_ids(entities)
        related_entities = [self._entity(entity_id) for entity_id in adjacent_ids if self._entity(entity_id)]
        relationships = [relationship for relationship in self.relationships if self._relationship_matches(relationship, entities, adjacent_ids)]
        paths = self._paths(entities, relationships)
        return LifeGraphExplorationOut(
            query=query,
            entityType=entity_type,
            entities=[LifeGraphEntityOut(**entity) for entity in entities + related_entities if entity["id"] in {item["id"] for item in entities + related_entities}],
            relationships=[LifeGraphRelationshipOut(**relationship) for relationship in relationships],
            paths=paths,
            aiInsights=self._insights(entities, relationships),
        )

    def _filter_entities(self, *, query: str, entity_type: str | None) -> list[dict[str, Any]]:
        normalized = query.lower().strip()
        filtered = self.entities
        if entity_type:
            filtered = [entity for entity in filtered if entity["type"].lower() == entity_type.lower()]
        if normalized:
            filtered = [entity for entity in filtered if normalized in entity["title"].lower() or normalized in entity["summary"].lower()]
        return filtered[:8]

    def _entity(self, entity_id: str) -> dict[str, Any] | None:
        return next((entity for entity in self.entities if entity["id"] == entity_id), None)

    def _adjacent_ids(self, entities: list[dict[str, Any]]) -> set[str]:
        ids = {entity["id"] for entity in entities}
        adj = set()
        for relationship in self.relationships:
            if relationship["source"] in ids or relationship["target"] in ids:
                adj.add(relationship["source"])
                adj.add(relationship["target"])
        return adj

    def _relationship_matches(self, relationship: dict[str, Any], entities: list[dict[str, Any]], adjacent_ids: set[str]) -> bool:
        if relationship["source"] not in adjacent_ids and relationship["target"] not in adjacent_ids:
            return False
        if not entities:
            return False
        entity_ids = {entity["id"] for entity in entities}
        return relationship["source"] in entity_ids or relationship["target"] in entity_ids

    def _paths(self, entities: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> list[LifeGraphPathOut]:
        entity_ids = {entity["id"] for entity in entities}
        if len(entity_ids) < 2:
            return []
        return [
            LifeGraphPathOut(
                nodes=[LifeGraphEntityOut(**self._entity(entity_id)) for entity_id in sorted(entity_ids)[:2]],
                relationships=[LifeGraphRelationshipOut(**relationship) for relationship in relationships[:1]],
            )
        ]

    def _insights(self, entities: list[dict[str, Any]], relationships: list[dict[str, Any]]) -> list[str]:
        insights = []
        if entities:
            insights.append(f"{len(entities)} entities are currently in view for this graph slice.")
        if relationships:
            insights.append(f"{len(relationships)} relationships were surfaced, including inferred links.")
        insights.extend(self.intelligence.hidden_connections(entities, relationships))
        insights.extend(self.intelligence.recommend_missing_links(entities, relationships))
        insights.extend(self.intelligence.detect_duplicates(entities))
        return insights[:6]
