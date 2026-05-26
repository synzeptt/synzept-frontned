"""Memory retrieval pipeline: intent → semantic → rank → select."""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.constants import MAX_MEMORIES_IN_CONTEXT
from app.memory.intent import IntentAnalyzer
from app.memory.scoring import score_memory
from app.memory.semantic import SemanticRetriever
from app.memory.store import MemoryStore
from app.memory.types import IntentResult, ScoredMemory, SemanticHit
from app.memory.validation import filter_scored_memories, filter_semantic_hits

logger = logging.getLogger(__name__)


class MemoryRetrievalPipeline:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.intent = IntentAnalyzer(session)
        self.semantic = SemanticRetriever(session)
        self.store = MemoryStore(session)

    async def run(
        self,
        user_id: UUID,
        query: str,
        *,
        project_id: UUID | None = None,
        explicit_project_id: UUID | None = None,
    ) -> tuple[IntentResult, list[ScoredMemory], list[SemanticHit]]:
        intent = await self.intent.analyze(user_id, query, explicit_project_id or project_id)
        active_project = intent.active_project_id or project_id

        semantic_hits = filter_semantic_hits(
            await self.semantic.search(user_id, query),
            query=query,
            limit=MAX_MEMORIES_IN_CONTEXT,
        )
        memories = await self.store.list_long_term(user_id, project_id=active_project, limit=100)

        semantic_map = self.semantic.build_semantic_score_map(
            semantic_hits, [m.id for m in memories]
        )

        scored = [
            score_memory(
                m,
                query,
                semantic_score=semantic_map.get(str(m.id), 0.0),
                project_id=str(active_project) if active_project else None,
            )
            for m in memories
        ]

        selected, diagnostics = filter_scored_memories(
            scored,
            query=query,
            limit=MAX_MEMORIES_IN_CONTEXT,
        )
        await self.store.touch_accessed([s.memory for s in selected])
        logger.info(
            "memory retrieval diagnostics",
            extra={
                "hit_count": diagnostics.semantic_hits or len(semantic_hits),
                "selected": diagnostics.selected,
                "filtered_low_score": diagnostics.filtered_low_score,
                "filtered_untrusted": diagnostics.filtered_untrusted,
            },
        )

        return intent, selected, semantic_hits
