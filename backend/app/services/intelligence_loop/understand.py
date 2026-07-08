from __future__ import annotations

from app.schemas.intelligence_loop import EvidenceOut, IntelligenceEventOut, UserModelOut, UserModelSignalOut


class UnderstandService:
    def update_user_model(self, events: list[IntelligenceEventOut]) -> UserModelOut:
        return UserModelOut(
            goals=[
                self._signal(
                    "goal-launch-v2",
                    "goal",
                    "Launch Synzept V2",
                    "Ship the V2 intelligence foundation with a coherent daily loop.",
                    self._confidence(events, ["Synzept V2", "Memory Feed"], base=0.45),
                    events,
                    ["Synzept V2", "Memory Feed"],
                )
            ],
            priorities=[
                self._signal(
                    "priority-integrate-surfaces",
                    "priority",
                    "Integrate intelligence surfaces",
                    "Use one loop to connect memory, action, opportunity, and trust surfaces.",
                    self._confidence(events, ["integration_needed", "home_screen"], base=0.38),
                    events,
                    ["integration_needed", "home_screen"],
                ),
                self._signal(
                    "priority-beta-followup",
                    "priority",
                    "Close beta follow-ups",
                    "External commitments need attention before new surface work.",
                    self._confidence(events, ["external_commitment", "deadline"], base=0.35),
                    events,
                    ["external_commitment", "deadline"],
                ),
            ],
            interests=[
                self._signal(
                    "interest-continuity",
                    "interest",
                    "Continuity and proactive recall",
                    "Returning users should not reconstruct context.",
                    self._confidence(events, ["north_star", "proactive_recall"], base=0.42),
                    events,
                    ["north_star", "proactive_recall"],
                )
            ],
            relationships=[
                self._signal(
                    "relationship-aarav",
                    "relationship",
                    "Aarav",
                    "Useful reviewer for onboarding and first-run clarity.",
                    self._confidence(events, ["relationship", "feedback"], base=0.25),
                    events,
                    ["Aarav", "relationship"],
                )
            ],
            workingPatterns=[
                self._signal(
                    "pattern-small-steps",
                    "working_pattern",
                    "Small implementation increments",
                    "Progress improves when actions are scoped to 15 to 30 minutes.",
                    self._confidence(events, ["small_steps", "execution_style"], base=0.34),
                    events,
                    ["small_steps", "execution_style"],
                )
            ],
        )

    @staticmethod
    def _confidence(events: list[IntelligenceEventOut], needles: list[str], base: float) -> float:
        matches = 0
        for event in events:
            haystack = " ".join([event.title, event.description, *event.entities, *event.signals]).lower()
            if any(needle.lower() in haystack for needle in needles):
                matches += 1
        return min(0.95, round(base + matches * 0.11, 2))

    @staticmethod
    def _evidence(events: list[IntelligenceEventOut], needles: list[str]) -> list[EvidenceOut]:
        evidence = []
        for event in events:
            haystack = " ".join([event.title, event.description, *event.entities, *event.signals]).lower()
            if any(needle.lower() in haystack for needle in needles):
                evidence.append(
                    EvidenceOut(
                        sourceId=event.id,
                        sourceType=event.source,
                        summary=event.title,
                        strength=max(event.importance, event.urgency),
                    )
                )
        return evidence[:4]

    def _signal(
        self,
        signal_id: str,
        category: str,
        label: str,
        value: str,
        confidence: float,
        events: list[IntelligenceEventOut],
        needles: list[str],
    ) -> UserModelSignalOut:
        return UserModelSignalOut(
            id=signal_id,
            category=category,
            label=label,
            value=value,
            confidence=confidence,
            evidence=self._evidence(events, needles),
            updatedAt="2026-07-07T09:30:00+05:30",
        )
