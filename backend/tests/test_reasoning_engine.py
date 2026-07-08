from app.schemas.reasoning_engine import ReasoningRequestIn
from app.services.reasoning_engine import ReasoningEngineService


def _request(message: str = "Should Synzept recommend the next product step or ask for clarification first?"):
    return ReasoningRequestIn(requestId="test-reasoning-001", message=message, conversationId="conv-test")


def test_reasoning_pipeline_runs_all_required_stages_before_response_generation():
    result = ReasoningEngineService().reason(_request())

    assert [step.name for step in result.pipeline] == [
        "Intent Analysis",
        "Context Retrieval",
        "Memory Retrieval",
        "Knowledge Graph Lookup",
        "Decision History Lookup",
        "Evidence Collection",
        "Risk Analysis",
        "Opportunity Analysis",
        "Planning",
        "Response Generation",
    ]


def test_planner_produces_structured_plan_before_llm_handoff():
    result = ReasoningEngineService().reason(_request())

    assert result.plan.hasEnoughInformation is True
    assert result.plan.relevantMemoryIds
    assert result.plan.similarDecisionIds
    assert result.plan.evidenceIds
    assert result.llmHandoff.reasoningPlan == result.plan
    assert result.llmHandoff.role == "language_generation_only"


def test_clarification_path_when_intent_and_evidence_are_weak():
    result = ReasoningEngineService().reason(_request("Hello"))

    assert result.plan.clarificationNeeded is True
    assert result.plan.clarificationQuestion
    assert "need one detail" in result.composedResponse.lower()


def test_llm_handoff_contains_guardrails_and_supporting_evidence():
    result = ReasoningEngineService().reason(_request())

    assert result.llmHandoff.supportingEvidence
    assert any("must not change planner recommendation" in guardrail.lower() for guardrail in result.llmHandoff.guardrails)
    assert result.plan.recommendation in result.composedResponse
