from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.memory.embedding_service import EmbeddingGenerationService
from app.memory.extraction_service import ConversationTurn, MemoryExtractionService
from app.memory.memory_service import MemoryService
from app.models.memory import Memory
from app.retrieval.ranking_service import MemoryRankingService
from app.retrieval.retrieval_service import SemanticRetrievalService


class FakeProvider:
    name = "fake"

    async def embed(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.executed = []

    def add(self, value) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        for value in self.added:
            if getattr(value, "id", None) is None:
                value.id = uuid4()

    async def execute(self, statement, params=None):
        self.executed.append((statement, params))
        return []


@pytest.mark.asyncio
async def test_memory_extraction_keeps_meaningful_context_and_skips_noise():
    service = MemoryExtractionService()

    extracted = await service.extract_from_conversation(
        [
            ConversationTurn(role="user", content="thanks"),
            ConversationTurn(role="assistant", content="Happy to help."),
            ConversationTurn(role="user", content="My goal is to launch Synzept with strong memory retrieval."),
            ConversationTurn(role="user", content="I prefer concise answers with concrete next steps."),
        ]
    )

    assert [item.memory_type for item in extracted] == ["goals", "preferences"]
    assert extracted[0].importance_score > 0.7
    assert "Synzept" in extracted[0].summary


@pytest.mark.asyncio
async def test_embedding_generation_upserts_provider_metadata():
    session = FakeSession()
    service = EmbeddingGenerationService(provider=FakeProvider())
    user_id = uuid4()
    source_id = uuid4()

    embedding = await service.upsert_embedding(
        session,
        user_id=user_id,
        source_type="memory",
        source_id=source_id,
        content="User prefers direct answers.",
    )

    assert embedding.provider_name == "fake"
    assert embedding.embedding == [0.1, 0.2, 0.3]
    assert session.added[-1] is embedding


@pytest.mark.asyncio
async def test_memory_persistence_prepares_embedding_and_required_fields():
    session = FakeSession()
    embeddings = EmbeddingGenerationService(provider=FakeProvider())
    service = MemoryService(session, embeddings=embeddings)
    extracted = (
        await MemoryExtractionService().extract_from_conversation(
            [ConversationTurn(role="user", content="I prefer async processing for chat memory updates.")]
        )
    )[0]

    memory = await service.create_memory(user_id=uuid4(), item=extracted)

    assert memory.memory_type == "preferences"
    assert memory.importance_score >= 0.7
    assert memory.retrieval_count == 0
    assert memory.metadata_["source"] == "conversation"
    assert memory.embedding_id is not None


def test_ranking_prioritizes_semantic_project_and_importance():
    now = datetime.now(timezone.utc)
    project_id = uuid4()
    relevant = Memory(
        id=uuid4(),
        user_id=uuid4(),
        project_id=project_id,
        memory_type="projects",
        content="Synzept memory retrieval must prioritize continuity and relevance.",
        summary="Synzept retrieval priorities.",
        importance_score=0.9,
        retrieval_count=3,
        created_at=now,
    )
    stale = Memory(
        id=uuid4(),
        user_id=uuid4(),
        memory_type="work",
        content="Old unrelated dashboard styling note.",
        summary="Old dashboard note.",
        importance_score=0.4,
        retrieval_count=0,
        created_at=now - timedelta(days=90),
    )

    ranked = MemoryRankingService().rank(
        [stale, relevant],
        query="memory retrieval relevance",
        semantic_scores={relevant.id: 0.88, stale.id: 0.1},
        project_id=project_id,
        limit=2,
        min_score=0.0,
    )

    assert ranked[0].memory is relevant
    assert ranked[0].score > ranked[1].score


def test_ranking_does_not_over_reward_retrieval_frequency():
    now = datetime.now(timezone.utc)
    relevant = Memory(
        id=uuid4(),
        user_id=uuid4(),
        memory_type="goals",
        content="User wants Synzept to improve continuity and memory retrieval quality.",
        summary="Continuity and retrieval quality goal.",
        importance_score=0.75,
        retrieval_count=0,
        created_at=now,
    )
    repeated_but_unrelated = Memory(
        id=uuid4(),
        user_id=uuid4(),
        memory_type="work",
        content="Old note about changing a button color.",
        summary="Button color note.",
        importance_score=0.75,
        retrieval_count=80,
        created_at=now,
    )

    ranked = MemoryRankingService().rank(
        [repeated_but_unrelated, relevant],
        query="continuity memory retrieval",
        semantic_scores={relevant.id: 0.74, repeated_but_unrelated.id: 0.0},
        limit=2,
        min_score=0.0,
    )

    assert ranked[0].memory is relevant
    assert ranked[1].retrieval_frequency_score <= 0.08


@pytest.mark.asyncio
async def test_semantic_retrieval_builds_pgvector_similarity_query():
    session = FakeSession()
    service = SemanticRetrievalService(session, embeddings=EmbeddingGenerationService(provider=FakeProvider()))
    candidate_id = uuid4()

    scores = await service._semantic_scores(
        user_id=uuid4(),
        query="retrieval quality",
        candidate_ids=[candidate_id],
        limit=4,
    )

    statement, params = session.executed[-1]
    assert "embedding <=>" in str(statement)
    assert params["query_vec"] == "[0.1,0.2,0.3]"
    assert params["candidate_ids"] == [candidate_id]
    assert scores == {}


def test_async_memory_processing_enqueue_payload(monkeypatch):
    captured = {}

    def fake_enqueue(job_type, **payload):
        captured["job_type"] = job_type
        captured["payload"] = payload

    monkeypatch.setattr("app.memory.memory_service.enqueue", fake_enqueue)
    service = MemoryService(SimpleNamespace())
    user_id = uuid4()
    conversation_id = uuid4()

    service.enqueue_post_response_processing(
        user_id=user_id,
        conversation_id=conversation_id,
        user_message="My goal is better recall.",
        assistant_reply="Got it.",
    )

    assert captured["job_type"].value == "memory_post_response"
    assert captured["payload"]["user_id"] == user_id
    assert captured["payload"]["conversation_id"] == conversation_id
