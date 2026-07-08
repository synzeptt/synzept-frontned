from __future__ import annotations

from typing import Any

from app.schemas.reasoning_engine import ReasoningRequestIn, ReasoningResponseOut, PipelineStepOut
from app.services.reasoning_engine.components import (
    ContextRetriever,
    DecisionAnalyzer,
    EvidenceCollector,
    IntentAnalyzer,
    KnowledgeRetriever,
    MemoryRetriever,
    OpportunityAnalyzer,
    Planner,
    ResponseComposer,
    RiskAnalyzer,
)
from app.services.reasoning_engine.mock_data import MOCK_REQUESTS


class ReasoningEngineService:
    def __init__(self) -> None:
        self.components = [
            IntentAnalyzer(),
            ContextRetriever(),
            MemoryRetriever(),
            KnowledgeRetriever(),
            DecisionAnalyzer(),
            EvidenceCollector(),
            RiskAnalyzer(),
            OpportunityAnalyzer(),
            Planner(),
            ResponseComposer(),
        ]

    def examples(self) -> list[dict[str, Any]]:
        return MOCK_REQUESTS

    def reason(self, body: ReasoningRequestIn) -> ReasoningResponseOut:
        state: dict[str, Any] = {"request": body.dict(), "pipeline": []}
        previous_counts: dict[str, int] = {}

        for component in self.components:
            state = component.run(state)
            state["pipeline"].append(self._step(component.name, state, previous_counts))

        return ReasoningResponseOut(
            requestId=body.requestId,
            generatedAt="2026-07-08T11:00:00+05:30",
            pipeline=state["pipeline"],
            intent=state["intent"],
            context=state.get("context", []),
            memories=state.get("memories", []),
            knowledge=state.get("knowledge", []),
            decisions=state.get("decisions", []),
            evidence=state.get("evidence", []),
            risks=state.get("risks", []),
            opportunities=state.get("opportunities", []),
            plan=state["plan"],
            llmHandoff=state["llmHandoff"],
            composedResponse=state["composedResponse"],
        )

    def _step(self, component_name: str, state: dict[str, Any], previous_counts: dict[str, int]) -> PipelineStepOut:
        key_map = {
            "IntentAnalyzer": "intent",
            "ContextRetriever": "context",
            "MemoryRetriever": "memories",
            "KnowledgeRetriever": "knowledge",
            "DecisionAnalyzer": "decisions",
            "EvidenceCollector": "evidence",
            "RiskAnalyzer": "risks",
            "OpportunityAnalyzer": "opportunities",
            "Planner": "plan",
            "ResponseComposer": "llmHandoff",
        }
        key = key_map[component_name]
        value = state.get(key)
        count = len(value) if isinstance(value, list) else 1 if value else 0
        previous_counts[key] = count
        confidence = self._confidence_for(component_name, state)
        return PipelineStepOut(
            name=self._stage_name(component_name),
            component=component_name,
            status="completed",
            summary=f"{component_name} produced {count} structured output item(s).",
            confidence=confidence,
        )

    def _confidence_for(self, component_name: str, state: dict[str, Any]) -> float:
        if component_name == "IntentAnalyzer":
            return state["intent"]["confidence"]
        if component_name == "Planner":
            return 0.88 if state["plan"]["hasEnoughInformation"] else 0.62
        values = []
        for key in ("context", "memories", "knowledge", "decisions"):
            values.extend(item.get("relevance", 0.7) for item in state.get(key, []))
        if not values:
            return 0.75
        return round(sum(values) / len(values), 2)

    def _stage_name(self, component_name: str) -> str:
        names = {
            "IntentAnalyzer": "Intent Analysis",
            "ContextRetriever": "Context Retrieval",
            "MemoryRetriever": "Memory Retrieval",
            "KnowledgeRetriever": "Knowledge Graph Lookup",
            "DecisionAnalyzer": "Decision History Lookup",
            "EvidenceCollector": "Evidence Collection",
            "RiskAnalyzer": "Risk Analysis",
            "OpportunityAnalyzer": "Opportunity Analysis",
            "Planner": "Planning",
            "ResponseComposer": "Response Generation",
        }
        return names[component_name]
