from __future__ import annotations

import re
from abc import ABC, abstractmethod
from hashlib import sha1
from typing import Any


NOW = "2026-07-08T10:00:00+05:30"


def _stable_id(prefix: str, text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:42]
    digest = sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}-{slug or digest}-{digest}"


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip(" .\n\t"))


class ConversationPreprocessor:
    def run(self, transcript: str) -> list[str]:
        lines = [_clean_text(line) for line in transcript.splitlines()]
        candidates = []
        for line in lines:
            if not line:
                continue
            parts = re.split(r"(?<=[.!?])\s+", line)
            candidates.extend(_clean_text(part) for part in parts if _clean_text(part))
        return candidates


class BaseExtractor(ABC):
    object_type: str
    extractor_name: str

    @abstractmethod
    def extract(self, sentences: list[str], conversation: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    def build_object(self, *, title: str, summary: str, confidence: float, conversation: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": _stable_id(self.object_type, title),
            "type": self.object_type,
            "title": title,
            "summary": summary,
            "confidence": confidence,
            "source": f"{conversation.get('source', 'conversation')}:{conversation['conversationId']}",
            "createdAt": NOW,
            "updatedAt": NOW,
            "metadata": metadata,
            "relationships": [
                {
                    "type": "created_from",
                    "targetId": conversation["conversationId"],
                    "confidence": 0.95,
                    "evidence": conversation["title"],
                }
            ],
        }


class GoalExtractor(BaseExtractor):
    object_type = "goal"
    extractor_name = "goal_extractor"

    def extract(self, sentences: list[str], conversation: dict[str, Any]) -> list[dict[str, Any]]:
        objects = []
        for sentence in sentences:
            lowered = sentence.lower()
            if lowered.startswith("goal:") or "goal" in lowered or "objective" in lowered:
                title = sentence.split(":", 1)[-1].strip() if ":" in sentence else sentence
                objects.append(
                    self.build_object(
                        title=title[:96],
                        summary=f"Goal inferred from conversation: {title}",
                        confidence=0.84 if lowered.startswith("goal:") else 0.72,
                        conversation=conversation,
                        metadata={"extractor": self.extractor_name, "impact": "high" if "decision intelligence" in lowered else "medium"},
                    )
                )
        return objects[:3]


class DecisionExtractor(BaseExtractor):
    object_type = "decision"
    extractor_name = "decision_extractor"

    def extract(self, sentences: list[str], conversation: dict[str, Any]) -> list[dict[str, Any]]:
        objects = []
        for sentence in sentences:
            lowered = sentence.lower()
            if lowered.startswith("decision:") or "decided" in lowered or "decision" in lowered:
                title = sentence.split(":", 1)[-1].strip() if ":" in sentence else sentence
                objects.append(
                    self.build_object(
                        title=title[:96],
                        summary=f"Decision candidate requiring user review: {title}",
                        confidence=0.9 if lowered.startswith("decision:") else 0.76,
                        conversation=conversation,
                        metadata={"extractor": self.extractor_name, "impact": "high", "requiresReview": True},
                    )
                )
        return objects[:4]


class TaskExtractor(BaseExtractor):
    object_type = "task"
    extractor_name = "task_extractor"

    def extract(self, sentences: list[str], conversation: dict[str, Any]) -> list[dict[str, Any]]:
        objects = []
        for sentence in sentences:
            lowered = sentence.lower()
            if lowered.startswith("task:") or lowered.startswith("todo:") or "need to" in lowered:
                title = sentence.split(":", 1)[-1].strip() if ":" in sentence else sentence
                objects.append(
                    self.build_object(
                        title=title[:96],
                        summary=f"Task extracted from conversation: {title}",
                        confidence=0.88 if lowered.startswith("task:") else 0.7,
                        conversation=conversation,
                        metadata={"extractor": self.extractor_name, "impact": "medium"},
                    )
                )
        return objects[:6]
