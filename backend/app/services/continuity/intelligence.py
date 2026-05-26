"""Long-term continuity intelligence for recurring priorities and timeline summaries."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
import re
from typing import Sequence
from uuid import UUID

from app.models.conversation import Conversation
from app.models.daily_summary import DailySummary
from app.models.memory import Memory
from app.models.note import Note
from app.models.project import Project
from app.models.task import Task
from app.tasks.service import OPEN_STATUSES
from app.utils.text import tokenize, truncate

STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "around",
    "because",
    "been",
    "before",
    "being",
    "could",
    "from",
    "have",
    "into",
    "just",
    "more",
    "other",
    "over",
    "some",
    "that",
    "their",
    "there",
    "these",
    "this",
    "those",
    "through",
    "today",
    "very",
    "with",
    "your",
}


@dataclass(slots=True)
class ContinuityTheme:
    label: str
    summary: str
    score: float = 0.0
    count: int = 0
    href: str | None = None


@dataclass(slots=True)
class ContinuityTimelineEntry:
    date: date
    headline: str
    summary: str
    recurring_priorities: list[str] = field(default_factory=list)
    recurring_themes: list[str] = field(default_factory=list)
    unresolved_items: list[str] = field(default_factory=list)
    continuity_score: float = 0.0


@dataclass(slots=True)
class ContinuityIntelligence:
    continuity_summary: str
    recurring_priorities: list[ContinuityTheme] = field(default_factory=list)
    ongoing_themes: list[ContinuityTheme] = field(default_factory=list)
    timeline: list[ContinuityTimelineEntry] = field(default_factory=list)
    memory_evolution: list[str] = field(default_factory=list)
    recurring_priority_labels: list[str] = field(default_factory=list)
    recurring_theme_labels: list[str] = field(default_factory=list)
    unresolved_items: list[str] = field(default_factory=list)


class ContinuityIntelligenceService:
    def build_intelligence(
        self,
        *,
        projects: Sequence[Project],
        conversations: Sequence[Conversation],
        tasks: Sequence[Task],
        notes: Sequence[Note],
        memories: Sequence[Memory],
        history: Sequence[DailySummary],
    ) -> ContinuityIntelligence:
        current_unresolved = self._current_unresolved(tasks, conversations, projects)
        recurring_priority_map = self._priority_candidates(tasks, history, current_unresolved)
        recurring_theme_map = self._theme_candidates(projects, conversations, notes, memories, history)
        recurring_priorities = self._to_theme_list(
            recurring_priority_map,
            kind="priority",
            href="/dashboard",
            limit=4,
        )
        recurring_themes = self._to_theme_list(recurring_theme_map, kind="theme", href="/dashboard", limit=5)
        timeline = self._timeline(history, recurring_priorities, recurring_themes, current_unresolved)
        memory_evolution = self._memory_evolution(recurring_priorities, recurring_themes, history)
        continuity_summary = self._continuity_summary(recurring_priorities, recurring_themes, current_unresolved)

        return ContinuityIntelligence(
            continuity_summary=continuity_summary,
            recurring_priorities=recurring_priorities,
            ongoing_themes=recurring_themes,
            timeline=timeline,
            memory_evolution=memory_evolution,
            recurring_priority_labels=[item.label for item in recurring_priorities],
            recurring_theme_labels=[item.label for item in recurring_themes],
            unresolved_items=current_unresolved,
        )

    @staticmethod
    def snapshot_payload(intelligence: ContinuityIntelligence) -> dict:
        return {
            "summary": intelligence.continuity_summary,
            "recurring_priorities": intelligence.recurring_priority_labels,
            "recurring_themes": intelligence.recurring_theme_labels,
            "unresolved_items": intelligence.unresolved_items[:6],
            "memory_evolution": intelligence.memory_evolution[:4],
            "score": ContinuityIntelligenceService._score_snapshot(intelligence),
        }

    @staticmethod
    def _score_snapshot(intelligence: ContinuityIntelligence) -> float:
        base = 0.35
        base += min(len(intelligence.recurring_priorities) * 0.08, 0.24)
        base += min(len(intelligence.ongoing_themes) * 0.05, 0.2)
        if intelligence.unresolved_items:
            base += 0.12
        return round(min(base, 1.0), 4)

    @staticmethod
    def _current_unresolved(tasks: Sequence[Task], conversations: Sequence[Conversation], projects: Sequence[Project]) -> list[str]:
        items: list[str] = []
        for task in tasks:
            if task.status in OPEN_STATUSES:
                items.append(task.title)
        for conversation in conversations:
            if conversation.archived_at is None and conversation.active_intent:
                items.append(conversation.active_intent)
        for project in projects:
            if project.status == "active":
                items.append(project.name)
        return ContinuityIntelligenceService._clean_strings(items, limit=8)

    @staticmethod
    def _priority_candidates(
        tasks: Sequence[Task],
        history: Sequence[DailySummary],
        unresolved: Sequence[str],
    ) -> Counter[str]:
        counts: Counter[str] = Counter()
        for task in tasks:
            if task.status in OPEN_STATUSES:
                normalized = ContinuityIntelligenceService._normalize_phrase(task.title)
                if normalized:
                    counts[normalized] += 2
                if task.description:
                    normalized = ContinuityIntelligenceService._normalize_phrase(task.description)
                    if normalized:
                        counts[normalized] += 1
        for item in unresolved:
            normalized = ContinuityIntelligenceService._normalize_phrase(item)
            if normalized:
                counts[normalized] += 1
        for row in history:
            metadata = row.metadata_ or {}
            for value in metadata.get("recurring_priorities", []):
                normalized = ContinuityIntelligenceService._normalize_phrase(str(value))
                if normalized:
                    counts[normalized] += 2
            for value in metadata.get("unresolved_items", []):
                normalized = ContinuityIntelligenceService._normalize_phrase(str(value))
                if normalized:
                    counts[normalized] += 1
            for value in row.unfinished_priorities[:6]:
                normalized = ContinuityIntelligenceService._normalize_phrase(str(value))
                if normalized:
                    counts[normalized] += 1
            counts.update(ContinuityIntelligenceService._phrase_counter([row.summary]))
        return counts

    @staticmethod
    def _theme_candidates(
        projects: Sequence[Project],
        conversations: Sequence[Conversation],
        notes: Sequence[Note],
        memories: Sequence[Memory],
        history: Sequence[DailySummary],
    ) -> Counter[str]:
        texts: list[str] = []
        for project in projects:
            texts.extend([project.name, project.description or "", project.context_summary or ""])
        for conversation in conversations:
            texts.extend([conversation.title or "", conversation.summary or "", conversation.active_intent or ""])
        for note in notes:
            texts.extend([note.title or "", note.summary or "", note.content])
        for memory in memories:
            texts.extend([memory.summary or "", memory.content])
        for row in history:
            metadata = row.metadata_ or {}
            texts.extend([row.summary])
            texts.extend(str(item) for item in metadata.get("recurring_themes", []))
            texts.extend(str(item) for item in metadata.get("recurring_priorities", []))
        counts = ContinuityIntelligenceService._phrase_counter(texts)
        for text in texts:
            normalized = ContinuityIntelligenceService._normalize_phrase(text)
            if normalized:
                counts[normalized] += 1
        return counts

    @staticmethod
    def _timeline(
        history: Sequence[DailySummary],
        recurring_priorities: Sequence[ContinuityTheme],
        recurring_themes: Sequence[ContinuityTheme],
        current_unresolved: Sequence[str],
    ) -> list[ContinuityTimelineEntry]:
        timeline: list[ContinuityTimelineEntry] = []
        current_priority_labels = [item.label for item in recurring_priorities[:3]]
        current_theme_labels = [item.label for item in recurring_themes[:3]]
        if current_priority_labels or current_theme_labels or current_unresolved:
            timeline.append(
                ContinuityTimelineEntry(
                    date=date.today(),
                    headline="Current continuity snapshot",
                    summary=ContinuityIntelligenceService._continuity_summary(recurring_priorities, recurring_themes, current_unresolved),
                    recurring_priorities=current_priority_labels,
                    recurring_themes=current_theme_labels,
                    unresolved_items=list(current_unresolved[:5]),
                    continuity_score=ContinuityIntelligenceService._score_snapshot(
                        ContinuityIntelligence(
                            continuity_summary="",
                            recurring_priorities=list(recurring_priorities),
                            ongoing_themes=list(recurring_themes),
                            unresolved_items=list(current_unresolved),
                        )
                    ),
                )
            )
        for row in history[:6]:
            metadata = row.metadata_ or {}
            priorities = [str(value) for value in metadata.get("recurring_priorities", [])][:3]
            themes = [str(value) for value in metadata.get("recurring_themes", [])][:3]
            unresolved = [str(value) for value in metadata.get("unresolved_items", [])][:4]
            summary = row.summary or "A continuity snapshot was captured."
            timeline.append(
                ContinuityTimelineEntry(
                    date=row.summary_date,
                    headline=ContinuityIntelligenceService._headline(summary, priorities, themes),
                    summary=truncate(summary, 180),
                    recurring_priorities=priorities,
                    recurring_themes=themes,
                    unresolved_items=unresolved,
                    continuity_score=float(metadata.get("score") or 0.0),
                )
            )
        timeline.sort(key=lambda item: item.date, reverse=True)
        return timeline[:7]

    @staticmethod
    def _memory_evolution(
        recurring_priorities: Sequence[ContinuityTheme],
        recurring_themes: Sequence[ContinuityTheme],
        history: Sequence[DailySummary],
    ) -> list[str]:
        evolution: list[str] = []
        if recurring_themes:
            top_theme = recurring_themes[0]
            if top_theme.count >= 2:
                evolution.append(f"You’ve consistently focused on {top_theme.label}.")
        if recurring_priorities:
            top_priority = recurring_priorities[0]
            if top_priority.count >= 2:
                evolution.append(f"{top_priority.label} remains an active priority across recent sessions.")
        history_labels = ContinuityIntelligenceService._history_summary_labels(history)
        if history_labels:
            evolution.append(history_labels)
        if not evolution and recurring_themes:
            evolution.append(f"{recurring_themes[0].label} is the clearest long-term theme right now.")
        return evolution[:4]

    @staticmethod
    def _history_summary_labels(history: Sequence[DailySummary]) -> str | None:
        if not history:
            return None
        labels: list[str] = []
        for row in history[:3]:
            metadata = row.metadata_ or {}
            themes = [str(value) for value in metadata.get("recurring_themes", [])[:2]]
            priorities = [str(value) for value in metadata.get("recurring_priorities", [])[:2]]
            if themes:
                labels.append(themes[0])
            elif priorities:
                labels.append(priorities[0])
        labels = ContinuityIntelligenceService._clean_strings(labels, limit=3)
        if not labels:
            return None
        if len(labels) == 1:
            return f"{labels[0]} keeps resurfacing in your continuity history."
        return f"Recent continuity history keeps circling back to {', '.join(labels[:2])}."

    @staticmethod
    def _continuity_summary(
        recurring_priorities: Sequence[ContinuityTheme],
        recurring_themes: Sequence[ContinuityTheme],
        unresolved_items: Sequence[str],
    ) -> str:
        parts: list[str] = []
        if recurring_priorities:
            parts.append(f"{recurring_priorities[0].label} is the most persistent priority.")
        if recurring_themes:
            parts.append(f"The long-running theme is {recurring_themes[0].label}.")
        if unresolved_items:
            parts.append(f"{len(unresolved_items)} open continuity item{'s' if len(unresolved_items) != 1 else ''} remain visible.")
        return " ".join(parts) or "No long-term continuity pattern has been established yet."

    @staticmethod
    def _to_theme_list(
        candidates: Counter[str],
        *,
        kind: str,
        href: str | None,
        limit: int,
    ) -> list[ContinuityTheme]:
        items: list[ContinuityTheme] = []
        for label, count in candidates.most_common(12):
            cleaned = ContinuityIntelligenceService._display_label(label)
            if not cleaned or count < 2:
                continue
            summary = (
                f"Reappears in {count} continuity signal{'s' if count != 1 else ''}."
                if kind == "priority"
                else f"Seen in {count} recent continuity signal{'s' if count != 1 else ''}."
            )
            score = min(0.45 + count * 0.12, 0.95)
            items.append(ContinuityTheme(label=cleaned, summary=summary, score=score, count=count, href=href))
            if len(items) == limit:
                break
        return items

    @staticmethod
    def _phrase_counter(texts: Sequence[str]) -> Counter[str]:
        counts: Counter[str] = Counter()
        for text in texts:
            tokens = ContinuityIntelligenceService._keyword_tokens(text)
            if len(tokens) < 2:
                continue
            seen: set[str] = set()
            for size in (2, 3):
                for index in range(len(tokens) - size + 1):
                    phrase = " ".join(tokens[index : index + size])
                    if len(phrase) < 8 or phrase in seen:
                        continue
                    seen.add(phrase)
                    counts[phrase] += 1
        return counts

    @staticmethod
    def _keyword_tokens(text: str | None) -> list[str]:
        if not text:
            return []
        return [token for token in tokenize(text) if len(token) > 3 and token not in STOPWORDS]

    @staticmethod
    def _display_label(label: str) -> str:
        value = re.sub(r"\s+", " ", label).strip()
        if not value:
            return ""
        return value[:1].upper() + value[1:]

    @staticmethod
    def _normalize_phrase(text: str | None) -> str:
        tokens = ContinuityIntelligenceService._keyword_tokens(text)
        return " ".join(tokens[:6])

    @staticmethod
    def _clean_strings(values: Sequence[str], *, limit: int) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            item = re.sub(r"\s+", " ", str(value)).strip()
            if not item:
                continue
            item = truncate(item, 120)
            if item not in cleaned:
                cleaned.append(item)
            if len(cleaned) == limit:
                break
        return cleaned

    @staticmethod
    def _headline(summary: str, priorities: Sequence[str], themes: Sequence[str]) -> str:
        if priorities:
            return priorities[0]
        if themes:
            return themes[0]
        return truncate(summary, 60) or "Continuity snapshot"

    @staticmethod
    def _score_snapshot(intelligence: ContinuityIntelligence) -> float:
        base = 0.35
        base += min(len(intelligence.recurring_priorities) * 0.08, 0.24)
        base += min(len(intelligence.ongoing_themes) * 0.05, 0.2)
        if intelligence.unresolved_items:
            base += 0.12
        return round(min(base, 1.0), 4)
