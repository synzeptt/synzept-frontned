from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.intelligence_dataset import (
    ConversationExtractIn,
    ExtractionResultOut,
    GraphEdgeOut,
    KnowledgeGraphOut,
    PipelineStageOut,
    ReviewActionOut,
    ReviewEditIn,
    ReviewItemOut,
    SynzeptObjectOut,
)
from app.services.intelligence_dataset.extractors import ConversationPreprocessor, DecisionExtractor, GoalExtractor, TaskExtractor
from app.services.intelligence_dataset.mock_data import MOCK_APPROVED_OBJECTS, MOCK_CONVERSATION


class IntelligenceDatasetService:
    _pending_review: dict[str, dict[str, Any]] = {}
    _graph_nodes: dict[str, dict[str, Any]] = {item["id"]: deepcopy(item) for item in MOCK_APPROVED_OBJECTS}
    _graph_edges: list[dict[str, Any]] = [
        {
            "id": "edge-decision-supports-goal",
            "sourceId": "decision-review-before-graph-save",
            "targetId": "goal-decision-intelligence-foundation",
            "type": "supports",
            "confidence": 0.86,
            "evidence": "The review gate decision supports the foundation goal.",
        }
    ]

    def __init__(self) -> None:
        self.preprocessor = ConversationPreprocessor()
        self.extractors = [GoalExtractor(), DecisionExtractor(), TaskExtractor()]

    def sample_conversation(self) -> dict[str, Any]:
        return deepcopy(MOCK_CONVERSATION)

    def extract(self, body: ConversationExtractIn) -> ExtractionResultOut:
        conversation = body.dict()
        sentences = self.preprocessor.run(body.transcript)
        stages = [
            PipelineStageOut(
                name="preprocessing",
                status="completed",
                summary=f"Normalized conversation into {len(sentences)} candidate statements.",
                objectCount=len(sentences),
            )
        ]

        review_items: list[ReviewItemOut] = []
        for extractor in self.extractors:
            extracted = extractor.extract(sentences, conversation)
            stages.append(
                PipelineStageOut(
                    name=extractor.extractor_name,
                    status="completed",
                    summary=f"Extracted {len(extracted)} {extractor.object_type} candidate(s).",
                    objectCount=len(extracted),
                )
            )
            for item in extracted:
                scored = self._score_confidence(item)
                review_item = self._to_review_item(scored, extractor.extractor_name)
                self._pending_review[review_item["id"]] = review_item
                review_items.append(ReviewItemOut(**review_item))

        stages.append(
            PipelineStageOut(
                name="review_queue",
                status="requires_user_confirmation",
                summary="High-impact knowledge is held for approve, edit, or reject before graph save.",
                objectCount=len(review_items),
            )
        )

        return ExtractionResultOut(
            conversationId=body.conversationId,
            stages=stages,
            pendingReviewItems=review_items,
            graphPreview=self.graph(),
        )

    def pending_review_items(self) -> list[ReviewItemOut]:
        return [ReviewItemOut(**item) for item in self._pending_review.values() if item["status"] == "pending"]

    def approve(self, review_item_id: str, edits: ReviewEditIn | None = None) -> ReviewActionOut:
        item = self._pending_review.get(review_item_id)
        if not item or item["status"] != "pending":
            return ReviewActionOut(status="not_found")

        approved_item = deepcopy(item)
        if edits:
            patch = edits.dict(exclude_none=True)
            for field in ("title", "summary", "confidence"):
                if field in patch:
                    approved_item["object"][field] = patch[field]
            if "metadata" in patch:
                approved_item["object"]["metadata"] = {**approved_item["object"]["metadata"], **patch["metadata"]}

        approved_item["status"] = "approved"
        item["status"] = "approved"
        graph_node = approved_item["object"]
        self._graph_nodes[graph_node["id"]] = graph_node
        self._add_edges_from_relationships(graph_node)
        return ReviewActionOut(status="approved", reviewItem=ReviewItemOut(**approved_item), graphNode=SynzeptObjectOut(**graph_node))

    def reject(self, review_item_id: str) -> ReviewActionOut:
        item = self._pending_review.get(review_item_id)
        if not item or item["status"] != "pending":
            return ReviewActionOut(status="not_found")
        item["status"] = "rejected"
        return ReviewActionOut(status="rejected", reviewItem=ReviewItemOut(**item))

    def graph(self) -> KnowledgeGraphOut:
        return KnowledgeGraphOut(
            nodes=[SynzeptObjectOut(**node) for node in self._graph_nodes.values()],
            edges=[GraphEdgeOut(**edge) for edge in self._graph_edges],
        )

    def _score_confidence(self, obj: dict[str, Any]) -> dict[str, Any]:
        scored = deepcopy(obj)
        if scored["type"] == "decision" and scored["metadata"].get("impact") == "high":
            scored["confidence"] = min(0.97, scored["confidence"] + 0.03)
        if scored["confidence"] < 0.75:
            scored["metadata"]["reviewReason"] = "Low confidence extraction needs confirmation."
        else:
            scored["metadata"]["reviewReason"] = "User confirmation required before saving structured knowledge."
        return scored

    def _to_review_item(self, obj: dict[str, Any], extractor_name: str) -> dict[str, Any]:
        return {
            "id": f"review-{obj['id']}",
            "object": obj,
            "status": "pending",
            "impact": str(obj["metadata"].get("impact", "medium")),
            "extractor": extractor_name,
            "rationale": str(obj["metadata"].get("reviewReason", "Pending user confirmation.")),
            "createdAt": obj["createdAt"],
        }

    def _add_edges_from_relationships(self, graph_node: dict[str, Any]) -> None:
        for relationship in graph_node.get("relationships", []):
            edge_id = f"edge-{graph_node['id']}-{relationship['type']}-{relationship['targetId']}"
            if any(edge["id"] == edge_id for edge in self._graph_edges):
                continue
            self._graph_edges.append(
                {
                    "id": edge_id,
                    "sourceId": graph_node["id"],
                    "targetId": relationship["targetId"],
                    "type": relationship["type"],
                    "confidence": relationship.get("confidence", 0.75),
                    "evidence": relationship.get("evidence") or "Approved review item relationship.",
                }
            )
