import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.orchestrator.context_builder import ContextBundle
from app.orchestrator.conversation_intelligence import ConversationIntelligenceService
from app.orchestrator.intent_service import IntentService, OrchestrationIntentCategory
from app.orchestrator.orchestrator_service import OrchestratorService
from app.orchestrator.project_context_service import ProjectContextBundle
from app.orchestrator.prompt_builder import PromptBuilder
from app.services.ai import AIResponse, AIStreamChunk, ProviderMetadata, TokenUsage


@pytest.mark.asyncio
async def test_intent_analysis_sets_strategy_for_project_continuation():
    intent = await IntentService().classify("Continue the investor strategy from yesterday")

    assert intent.category == OrchestrationIntentCategory.PROJECT_CONTINUATION
    assert intent.strategy.memory_limit == 8
    assert intent.strategy.recent_message_limit == 18


def test_prompt_builder_includes_ranked_context_without_overloading_budget():
    intent = IntentService()._build(OrchestrationIntentCategory.PLANNING, 0.9, "plan roadmap")
    context = ContextBundle(
        user_profile="Prefers direct, structured answers.",
        conversation_summary="Discussed Synzept memory and retrieval foundations.",
        recent_messages=[{"role": "user", "content": "Earlier message " * 300}],
        memories=["[goals] Launch Synzept with strong continuity."],
        conversation_intelligence=[
            "Decision: We chose memory-first orchestration.",
            "Related discussion: Roadmap - Preserve unresolved planning threads.",
        ],
        personalization=["Prefers direct, structured answers."],
        project=ProjectContextBundle(
            project_id=uuid4(),
            name="Synzept",
            summary="AI workspace with memory-first orchestration.",
            active_tasks=["Wire orchestration into chat (high)"],
        ),
    )

    messages = PromptBuilder().build(
        user_message="Plan the next implementation step",
        intent=intent,
        context=context,
        max_prompt_tokens=650,
    )

    system = messages[0].content
    assert "Intent: planning" in system
    assert "Relevant memories" in system
    assert "Conversation continuity intelligence" in system
    assert "Light personalization cues" in system
    assert "Active project: Synzept" in system
    assert messages[-1].content == "Plan the next implementation step"


def test_conversation_intelligence_extracts_decisions_and_open_loops():
    state = ConversationIntelligenceService.extract_state(
        user_message="We decided to keep onboarding lightweight. Still need to review project linking.",
        assistant_reply="Next step: test continuation quality and preserve unresolved choices.",
    )

    assert state.decisions
    assert state.open_loops
    assert "onboarding" in state.topics


@pytest.mark.asyncio
async def test_conversation_intelligence_updates_summary_and_project_link():
    conversation = SimpleNamespace(id=uuid4(), project_id=None, summary="", active_intent="")
    project_id = uuid4()

    await ConversationIntelligenceService(SimpleNamespace()).update_after_turn(
        conversation=conversation,
        user_message="We decided to use project-linked conversations.",
        assistant_reply="Still need to test decision continuity.",
        project_id=project_id,
    )

    assert conversation.project_id == project_id
    assert "Decisions" in conversation.summary
    assert conversation.active_intent


class FakeChat:
    def __init__(self) -> None:
        self.added = []
        self.conversation = SimpleNamespace(id=uuid4(), project_id=uuid4(), summary="Previous thread summary.")

    async def get_or_create(self, user_id, conversation_id, project_id):
        if project_id:
            self.conversation.project_id = project_id
        return self.conversation

    async def add_message(self, conversation_id, role, content, **kwargs):
        message = SimpleNamespace(id=uuid4(), conversation_id=conversation_id, role=role, content=content, kwargs=kwargs)
        self.added.append(message)
        return message


class FakeProjects:
    async def detect_project(self, **kwargs):
        return kwargs["conversation"].project_id


class FakeContext:
    async def build(self, **kwargs):
        return ContextBundle(
            user_profile="User likes concise execution notes.",
            memories=["[preferences] User prefers concise answers."],
            project=ProjectContextBundle(
                project_id=kwargs["project_id"],
                name="Synzept",
                summary="Memory-first AI workspace.",
                active_tasks=["Complete orchestration tests (high)"],
            ),
        )


class FakeResponses:
    async def complete(self, **kwargs):
        return AIResponse(
            content="Here is the organized next step.",
            usage=TokenUsage(prompt_tokens=20, completion_tokens=8, total_tokens=28),
            metadata=ProviderMetadata(provider="fake", model="fake-model"),
        )

    async def stream(self, **kwargs):
        yield AIStreamChunk(event="meta", metadata=ProviderMetadata(provider="fake", model="fake-model"))
        yield AIStreamChunk(event="token", content="First ")
        yield AIStreamChunk(event="token", content="second.")
        yield AIStreamChunk(event="usage", usage=TokenUsage(prompt_tokens=20, completion_tokens=3, total_tokens=23))


class FakeFailingResponses:
    async def complete(self, **kwargs):
        raise RuntimeError("provider timeout")

    async def stream(self, **kwargs):
        raise RuntimeError("provider timeout")
        yield  # pragma: no cover


class FakeCommitSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_orchestrator_run_coordinates_context_ai_and_memory(monkeypatch):
    scheduled = {}

    def fake_schedule(**payload):
        scheduled.update(payload)

    monkeypatch.setattr("app.orchestrator.orchestrator_service.schedule_post_response", fake_schedule)
    service = OrchestratorService(
        SimpleNamespace(),
        uuid4(),
        projects=FakeProjects(),
        context=FakeContext(),
        responses=FakeResponses(),
    )
    service.chat = FakeChat()

    result = await service.run("Continue the Synzept roadmap")

    assert result.reply == "Here is the organized next step."
    assert result.intent.category == OrchestrationIntentCategory.PROJECT_CONTINUATION
    assert service.chat.added[0].role == "user"
    assert service.chat.added[1].role == "assistant"
    assert service.chat.conversation.summary
    assert scheduled["assistant_reply"] == result.reply
    assert scheduled["project_id"] == service.chat.conversation.project_id


@pytest.mark.asyncio
async def test_orchestrator_run_preserves_user_message_when_ai_fails(monkeypatch):
    monkeypatch.setattr("app.orchestrator.orchestrator_service.schedule_post_response", lambda **payload: None)
    session = FakeCommitSession()
    service = OrchestratorService(
        session,
        uuid4(),
        projects=FakeProjects(),
        context=FakeContext(),
        responses=FakeFailingResponses(),
    )
    service.chat = FakeChat()

    result = await service.run("Continue the roadmap")

    assert session.commits == 1
    assert service.chat.added[0].role == "user"
    assert service.chat.added[1].role == "assistant"
    assert "saved" in result.reply.lower()
    assert service.chat.added[1].kwargs["metadata"]["status"] == "failed"


@pytest.mark.asyncio
async def test_orchestrator_stream_returns_saved_fallback_when_ai_fails(monkeypatch):
    monkeypatch.setattr("app.orchestrator.orchestrator_service.schedule_post_response", lambda **payload: None)
    session = FakeCommitSession()
    service = OrchestratorService(
        session,
        uuid4(),
        projects=FakeProjects(),
        context=FakeContext(),
        responses=FakeFailingResponses(),
    )
    service.chat = FakeChat()

    events = [json.loads(chunk) async for chunk in service.stream("Resume the roadmap")]

    assert session.commits == 1
    assert any("token" in event for event in events)
    assert events[-1]["done"] is True
    assert service.chat.added[-1].role == "assistant"
    assert service.chat.added[-1].kwargs["metadata"]["status"] == "failed"


@pytest.mark.asyncio
async def test_orchestrator_stream_yields_incremental_tokens_and_saves(monkeypatch):
    monkeypatch.setattr("app.orchestrator.orchestrator_service.schedule_post_response", lambda **payload: None)
    service = OrchestratorService(
        SimpleNamespace(),
        uuid4(),
        projects=FakeProjects(),
        context=FakeContext(),
        responses=FakeResponses(),
    )
    service.chat = FakeChat()

    events = [json.loads(chunk) async for chunk in service.stream("Resume yesterday's roadmap discussion")]

    assert events[0]["intent"] == "project_continuation"
    assert [event["token"] for event in events if "token" in event] == ["First ", "second."]
    assert events[-1]["done"] is True
    assert service.chat.added[-1].content == "First second."
