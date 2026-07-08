from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.decision_graph import (
    DecisionGraphChainOut,
    DecisionGraphInsightOut,
    DecisionGraphNodeOut,
    DecisionGraphOut,
)
from app.services.decision_graph.mock_data import MOCK_DECISION_GRAPH


class DecisionGraphService:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = deepcopy(data or MOCK_DECISION_GRAPH)

    def graph(self, relationship: str | None = None) -> DecisionGraphOut:
        edges = self.data["edges"]
        if relationship:
            edges = [edge for edge in edges if edge["relationship"] == relationship]
            node_ids = {edge["source"] for edge in edges} | {edge["target"] for edge in edges}
            nodes = [node for node in self.data["nodes"] if node["id"] in node_ids]
        else:
            nodes = self.data["nodes"]
        return DecisionGraphOut(
            generatedAt=self.data["generatedAt"],
            nodes=nodes,
            edges=edges,
            insights=self.data["insights"],
            chains=self.data["chains"],
            supportedRelationships=self.data["supportedRelationships"],
        )

    def node_neighborhood(self, node_id: str) -> DecisionGraphOut:
        edges = [edge for edge in self.data["edges"] if edge["source"] == node_id or edge["target"] == node_id]
        node_ids = {node_id} | {edge["source"] for edge in edges} | {edge["target"] for edge in edges}
        nodes = [node for node in self.data["nodes"] if node["id"] in node_ids]
        return DecisionGraphOut(
            generatedAt=self.data["generatedAt"],
            nodes=nodes,
            edges=edges,
            insights=[insight for insight in self.data["insights"] if any(edge_id in {edge["id"] for edge in edges} for edge_id in insight["supportingConnectionIds"])],
            chains=[chain for chain in self.data["chains"] if node_id in chain["nodeIds"]],
            supportedRelationships=self.data["supportedRelationships"],
        )

    def decision_nodes(self) -> list[DecisionGraphNodeOut]:
        return [DecisionGraphNodeOut(**node) for node in self.data["nodes"] if node["type"] == "decision"]

    def insights(self) -> list[DecisionGraphInsightOut]:
        ranked = sorted(self.data["insights"], key=lambda item: (item["impact"], item["confidence"]), reverse=True)
        return [DecisionGraphInsightOut(**insight) for insight in ranked]

    def chains(self) -> list[DecisionGraphChainOut]:
        return [DecisionGraphChainOut(**chain) for chain in self.data["chains"]]
