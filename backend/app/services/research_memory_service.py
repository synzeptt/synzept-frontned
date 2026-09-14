from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import Memory


class ResearchMemoryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_from_action(self, action) -> Memory | None:
        if getattr(action, "action_type", None) != "research":
            return None

        metadata = dict(getattr(action, "metadata_", None) or {}) if isinstance(getattr(action, "metadata_", None), dict) else {}
        report_id = metadata.get("report_id") or str(action.id)
        output = getattr(action, "output", "") or ""
        query = getattr(action, "request", "") or ""
        content = self._build_content(query, output)
        summary = self._build_summary(query, output)
        topics = self._extract_topics(query, output)
        companies = self._extract_metadata_values(output, ["company", "companies", "org", "organization", "vendor", "vendor names"])
        technologies = self._extract_metadata_values(output, ["technology", "technologies", "tool", "tools", "platform", "platforms"])
        recommendations = self._extract_recommendations(output)
        source_list = self._extract_sources(output)
        confidence_score = self._coerce_confidence(metadata.get("confidence_score"), metadata.get("confidence"))

        memory_metadata = {
            "report_id": report_id,
            "query": query,
            "topics": topics,
            "companies": companies,
            "technologies": technologies,
            "recommendations": recommendations,
            "source_list": source_list,
            "confidence_score": confidence_score,
            "created_at": metadata.get("created_at") or datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "action_id": str(action.id),
        }

        existing = await self._find_existing(action.user_id, report_id)
        if existing is not None:
            existing.content = content
            existing.summary = summary
            existing.memory_type = "research"
            existing.category = "research"
            existing.confidence = confidence_score
            existing.importance_score = max(existing.importance_score, min(0.99, 0.7 + confidence_score * 0.25))
            existing.metadata_ = {**(existing.metadata_ or {}), **memory_metadata}
            existing.content_hash = self._content_hash(content)
            existing.version += 1
            await self.session.flush()
            return existing

        memory = Memory(
            user_id=action.user_id,
            conversation_id=getattr(action, "conversation_id", None),
            project_id=getattr(action, "project_id", None),
            memory_type="research",
            category="research",
            content=content,
            summary=summary,
            importance_score=min(0.99, 0.65 + confidence_score * 0.25),
            recency_score=1.0,
            retrieval_count=0,
            version=1,
            confidence=confidence_score,
            metadata_=memory_metadata,
            content_hash=self._content_hash(content),
        )
        self.session.add(memory)
        await self.session.flush()
        return memory

    async def retrieve_context(self, *, user_id: UUID, query: str, limit: int = 5) -> list[Memory]:
        if not query or not query.strip():
            return []
        rows = await self._fetch_memories(user_id=user_id, limit=max(limit * 3, 20))
        if not rows:
            return []

        terms = self._tokenize(query)
        scored: list[tuple[float, Memory]] = []
        for memory in rows:
            score = 0.0
            text = f"{memory.content or ''} {memory.summary or ''} {' '.join(str(item) for item in (memory.metadata_ or {}).values() if isinstance(item, (str, int, float, bool)))}".lower()
            for term in terms:
                if term in text:
                    score += 2.0
            metadata = dict(memory.metadata_ or {})
            for field in ("topics", "companies", "technologies", "recommendations", "source_list"):
                values = metadata.get(field) or []
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, str) and any(term in value.lower() for term in terms):
                            score += 1.2
            scored.append((score + memory.importance_score, memory))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [memory for _, memory in scored[:limit]]

    async def related_memories(self, *, user_id: UUID, memory_id: UUID, limit: int = 5) -> list[Memory]:
        memory = await self.session.get(Memory, memory_id)
        if not memory or memory.user_id != user_id or memory.memory_type != "research":
            return []

        rows = await self._fetch_memories(user_id=user_id, limit=50)
        if not rows:
            return []

        scored: list[tuple[float, Memory]] = []
        current_metadata = dict(memory.metadata_ or {})
        for candidate in rows:
            if candidate.id == memory.id:
                continue
            candidate_metadata = dict(candidate.metadata_ or {})
            overlap = 0.0
            for field in ("topics", "companies", "technologies", "recommendations"):
                left = set(str(item).casefold() for item in current_metadata.get(field, []) if isinstance(item, (str, int, float, bool)))
                right = set(str(item).casefold() for item in candidate_metadata.get(field, []) if isinstance(item, (str, int, float, bool)))
                overlap += len(left & right) * 1.8
            if overlap > 0:
                scored.append((overlap + candidate.importance_score, candidate))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [memory for _, memory in scored[:limit]]

    def build_change_summary(self, previous: dict[str, Any] | None, current: dict[str, Any] | None) -> dict[str, Any]:
        previous_data = previous or {}
        current_data = current or {}

        def as_list(value: Any) -> list[str]:
            if isinstance(value, list):
                return [str(item) for item in value if str(item).strip()]
            if isinstance(value, str):
                return [value]
            return []

        previous_recommendations = {item.casefold(): item for item in as_list(previous_data.get("recommendations"))}
        current_recommendations = {item.casefold(): item for item in as_list(current_data.get("recommendations"))}
        new_recommendations = [current_recommendations[key] for key in current_recommendations if key not in previous_recommendations]

        previous_companies = {item.casefold(): item for item in as_list(previous_data.get("companies"))}
        current_companies = {item.casefold(): item for item in as_list(current_data.get("companies"))}
        new_companies = [current_companies[key] for key in current_companies if key not in previous_companies]

        previous_sources = {item.casefold(): item for item in as_list(previous_data.get("source_list"))}
        current_sources = {item.casefold(): item for item in as_list(current_data.get("source_list"))}
        new_sources = [current_sources[key] for key in current_sources if key not in previous_sources]

        previous_confidence = float(previous_data.get("confidence_score") or 0.0)
        current_confidence = float(current_data.get("confidence_score") or 0.0)
        return {
            "new_recommendations": new_recommendations,
            "new_companies": new_companies,
            "new_sources": new_sources,
            "confidence_delta": round(current_confidence - previous_confidence, 2),
        }

    async def _fetch_memories(self, *, user_id: UUID, limit: int) -> list[Memory]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == user_id, Memory.memory_type == "research", Memory.deleted_at.is_(None), Memory.archived_at.is_(None))
            .order_by(Memory.importance_score.desc(), Memory.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _find_existing(self, user_id: UUID, report_id: str) -> Memory | None:
        if not report_id:
            return None
        result = await self.session.execute(
            select(Memory).where(
                Memory.user_id == user_id,
                Memory.memory_type == "research",
                Memory.deleted_at.is_(None),
                Memory.archived_at.is_(None),
            )
        )
        for memory in result.scalars().all():
            metadata = dict(memory.metadata_ or {})
            if metadata.get("report_id") == report_id:
                return memory
        return None

    def _build_content(self, query: str, output: str) -> str:
        output_text = (output or "").strip()
        if output_text:
            return f"Research request: {query}\n\n{output_text}"
        return f"Research request: {query}"

    def _build_summary(self, query: str, output: str) -> str:
        text = (output or "").strip()
        if not text:
            return query[:220]
        cleaned = re.sub(r"\s+", " ", text)
        return cleaned[:320]

    def _extract_topics(self, query: str, output: str) -> list[str]:
        text = f"{query} {output}".casefold()
        explicit_topics = []
        if "ai workflow tools" in text:
            explicit_topics.append("ai workflow tools")
        if "startup team" in text:
            explicit_topics.append("startup team")
        if "workflow tools" in text and "ai workflow tools" not in text:
            explicit_topics.append("workflow tools")
        if "pricing model" in text:
            explicit_topics.append("pricing model")
        if "market research" in text:
            explicit_topics.append("market research")
        if "roadmap planning" in text:
            explicit_topics.append("roadmap planning")
        if "delivery plan" in text:
            explicit_topics.append("delivery plan")
        if explicit_topics:
            return explicit_topics[:8]

        terms = self._tokenize(query) + self._tokenize(output)
        seen: set[str] = set()
        topics: list[str] = []
        for term in terms:
            if len(term) < 3 or term in {"the", "and", "for", "with", "from", "that", "this", "your"}:
                continue
            if term not in seen:
                seen.add(term)
                topics.append(term)
        return topics[:8]

    def _extract_metadata_values(self, output: str, labels: list[str]) -> list[str]:
        text = (output or "").lower()
        values: list[str] = []
        for label in labels:
            if label in text:
                values.append(label)
        return values

    def _extract_recommendations(self, output: str) -> list[str]:
        lines = [line.strip(" -•*\n") for line in (output or "").splitlines() if line.strip()]
        recommendations = []
        for line in lines:
            lower = line.lower()
            if lower.startswith("recommendation") or lower.startswith("recommendations") or lower.startswith("- ") or lower.startswith("•"):
                recommendations.append(line)
        return recommendations[:8]

    def _extract_sources(self, output: str) -> list[str]:
        lines = [line.strip(" -•*\n") for line in (output or "").splitlines() if line.strip()]
        sources = []
        for line in lines:
            if "source" in line.lower() and line.lower() != "sources":
                sources.append(line)
        return sources[:8]

    def _coerce_confidence(self, *values: Any) -> float:
        for value in values:
            if value is None:
                continue
            try:
                return max(0.0, min(0.99, float(value)))
            except (TypeError, ValueError):
                continue
        return 0.75

    def _tokenize(self, text: str) -> list[str]:
        normalized = re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()
        return [token for token in normalized.split() if len(token) >= 3]

    def _content_hash(self, content: str) -> str:
        normalized = " ".join((content or "").lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
