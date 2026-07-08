from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.services.reasoning_engine.mock_data import MOCK_CONTEXT, MOCK_DECISIONS, MOCK_KNOWLEDGE, MOCK_MEMORIES


class ReasoningComponent(ABC):
    name: str

    @abstractmethod
    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


def _score_by_terms(message: str, item: dict[str, Any]) -> float:
    terms = {term.strip(".,?!:;").lower() for term in message.split() if len(term.strip(".,?!:;")) > 3}
    haystack = f"{item['title']} {item['summary']}".lower()
    overlap = sum(1 for term in terms if term in haystack)
    return min(0.99, item["relevance"] + (overlap * 0.015))


class IntentAnalyzer(ReasoningComponent):
    name = "IntentAnalyzer"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        message = state["request"]["message"]
        lowered = message.lower()
        if "should" in lowered or "recommend" in lowered:
            intent = "decision_support"
            objective = "Help choose a next step with evidence and risk awareness."
        elif "plan" in lowered or "build" in lowered:
            intent = "implementation_planning"
            objective = "Create a structured execution plan."
        else:
            intent = "general_reasoning"
            objective = "Understand the request and provide a grounded answer."
        state["intent"] = {
            "intent": intent,
            "objective": objective,
            "urgency": "high" if any(word in lowered for word in ["urgent", "now", "today", "important"]) else "medium",
            "confidence": 0.86 if intent != "general_reasoning" else 0.72,
            "signals": [signal for signal in ["should", "recommend", "plan", "important"] if signal in lowered],
        }
        return state


class ContextRetriever(ReasoningComponent):
    name = "ContextRetriever"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        state["context"] = sorted(
            [{**item, "relevance": _score_by_terms(state["request"]["message"], item)} for item in MOCK_CONTEXT],
            key=lambda item: item["relevance"],
            reverse=True,
        )
        return state


class MemoryRetriever(ReasoningComponent):
    name = "MemoryRetriever"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        state["memories"] = sorted(
            [{**item, "relevance": _score_by_terms(state["request"]["message"], item)} for item in MOCK_MEMORIES],
            key=lambda item: item["relevance"],
            reverse=True,
        )
        return state


class KnowledgeRetriever(ReasoningComponent):
    name = "KnowledgeRetriever"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        state["knowledge"] = sorted(
            [{**item, "relevance": _score_by_terms(state["request"]["message"], item)} for item in MOCK_KNOWLEDGE],
            key=lambda item: item["relevance"],
            reverse=True,
        )
        return state


class DecisionAnalyzer(ReasoningComponent):
    name = "DecisionAnalyzer"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        state["decisions"] = sorted(
            [{**item, "relevance": _score_by_terms(state["request"]["message"], item)} for item in MOCK_DECISIONS],
            key=lambda item: item["relevance"],
            reverse=True,
        )
        return state


class EvidenceCollector(ReasoningComponent):
    name = "EvidenceCollector"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        evidence = []
        for item in [*state.get("memories", [])[:2], *state.get("knowledge", [])[:2], *state.get("decisions", [])[:2]]:
            evidence.append(
                {
                    "id": f"evidence-{item['id']}",
                    "claim": item["summary"],
                    "source": item["source"],
                    "strength": round(item["relevance"], 2),
                    "supports": item["id"],
                }
            )
        state["evidence"] = evidence
        return state


class RiskAnalyzer(ReasoningComponent):
    name = "RiskAnalyzer"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        risks = [
            {
                "id": "risk-insufficient-context",
                "title": "Recommendation may be premature if the user objective is underspecified",
                "severity": "medium",
                "likelihood": 0.42,
                "mitigation": "Ask one clarifying question when evidence is thin or intent confidence is below threshold.",
            },
            {
                "id": "risk-llm-overreach",
                "title": "LLM may invent product decisions without a plan",
                "severity": "high",
                "likelihood": 0.58,
                "mitigation": "Pass a structured plan and guardrails into the composition layer.",
            },
        ]
        if state["intent"]["confidence"] > 0.8 and len(state.get("evidence", [])) >= 4:
            risks[0]["likelihood"] = 0.24
        state["risks"] = risks
        return state


class OpportunityAnalyzer(ReasoningComponent):
    name = "OpportunityAnalyzer"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        state["opportunities"] = [
            {
                "id": "opp-reasoning-contract",
                "title": "Create a durable reasoning contract before LLM generation",
                "expectedImpact": 0.88,
                "rationale": "The plan can be tested independently and reused by future response surfaces.",
            },
            {
                "id": "opp-module-extension",
                "title": "Add future modules without changing pipeline orchestration",
                "expectedImpact": 0.78,
                "rationale": "Components share a simple run(state) interface.",
            },
        ]
        return state


class Planner(ReasoningComponent):
    name = "Planner"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        evidence = state.get("evidence", [])
        memories = state.get("memories", [])
        decisions = state.get("decisions", [])
        has_enough = state["intent"]["confidence"] >= 0.75 and len(evidence) >= 3
        clarification = not has_enough
        state["plan"] = {
            "hasEnoughInformation": has_enough,
            "clarificationNeeded": clarification,
            "clarificationQuestion": "Which specific product decision are you trying to make right now?" if clarification else None,
            "relevantMemoryIds": [item["id"] for item in memories[:2]],
            "similarDecisionIds": [item["id"] for item in decisions[:2]],
            "evidenceIds": [item["id"] for item in evidence[:5]],
            "risksToMention": [item["id"] for item in state.get("risks", []) if item["severity"] in {"high", "medium"}],
            "opportunitiesToMention": [item["id"] for item in state.get("opportunities", [])[:2]],
            "recommendation": "Proceed with a structured answer and include the reasoning plan, evidence, risks, and one next action." if has_enough else "Ask a focused clarification before recommending a product direction.",
            "responseStrategy": "reasoned_recommendation" if has_enough else "clarify_first",
            "llmInstructions": [
                "Preserve the recommendation chosen by the planner.",
                "Do not introduce unsupported decisions.",
                "Mention evidence and risks in plain language.",
                "Keep the response concise and action-oriented.",
            ],
        }
        return state


class ResponseComposer(ReasoningComponent):
    name = "ResponseComposer"

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        plan = state["plan"]
        if plan["clarificationNeeded"]:
            response = f"I need one detail before recommending a direction: {plan['clarificationQuestion']}"
        else:
            response = (
                f"Recommendation: {plan['recommendation']} "
                f"This is grounded in {len(plan['evidenceIds'])} evidence items, "
                f"{len(plan['similarDecisionIds'])} similar decisions, and {len(plan['risksToMention'])} risk checks."
            )
        state["composedResponse"] = response
        state["llmHandoff"] = {
            "role": "language_generation_only",
            "structuredContext": {
                "intent": state["intent"],
                "contextIds": [item["id"] for item in state.get("context", [])],
                "memoryIds": plan["relevantMemoryIds"],
                "decisionIds": plan["similarDecisionIds"],
            },
            "reasoningPlan": plan,
            "supportingEvidence": state.get("evidence", []),
            "guardrails": [
                "LLM must not change planner recommendation.",
                "LLM must not claim access to production data.",
                "LLM must ask clarification if the plan requires it.",
            ],
        }
        return state
