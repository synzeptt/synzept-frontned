from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.user import User
from app.models.user_understanding import UserUnderstanding
from app.schemas.user_understanding import (
    UnderstandingInsightOut,
    UnderstandingModelOut,
    UserUnderstandingCoverageOut,
    UserUnderstandingEngineOut,
    UserUnderstandingRefreshOut,
)
from app.services.insight_generation_service import InsightGenerationService
from app.services.knows_you_service import KnowsYouService
from app.services.priority_engine import PriorityEngine
from app.services.understanding_extraction_service import UnderstandingExtractionService, UnderstandingFact
from app.services.understanding_update_service import UnderstandingUpdateService
from app.services.user_understanding_service import UserUnderstandingService


class UnderstandingEngineService:
    """Coordinates extraction, updates, priorities, and insights for Synzept Knows You."""

    def __init__(self, session) -> None:
        self.session = session
        self.extraction = UnderstandingExtractionService(session)
        self.updates = UnderstandingUpdateService(session)
        self.priorities = PriorityEngine(session)
        self.insights = InsightGenerationService(session, priorities=self.priorities)
        self.understanding = UserUnderstandingService(session)
        self.knows_you = KnowsYouService(session)

    async def get_understanding(self, user: User) -> UserUnderstandingEngineOut:
        items = await self.understanding.list_for_user(user)
        profile = await self.knows_you.get_understanding(user.id)
        coverage = await self.understanding.coverage_for_user(user)
        insights = await self.insights.insights_for_user(user.id)
        model = await self._model(user.id, items)
        summary = self._summary(model, insights)
        return self._out(user, profile, model, summary, coverage, insights)

    async def refresh(self, user: User) -> UserUnderstandingRefreshOut:
        facts = await self.extraction.extract_for_user(user.id)
        update_result = await self.updates.apply_facts(user.id, facts)
        priority_facts = await self._priority_facts(user.id)
        priority_result = await self.updates.apply_facts(user.id, priority_facts)
        coverage = await self.understanding.coverage_for_user(user)
        understanding = await self.get_understanding(user)
        return UserUnderstandingRefreshOut(
            created=update_result.created + priority_result.created,
            updated=update_result.updated + priority_result.updated,
            unchanged=update_result.unchanged + priority_result.unchanged,
            extracted=len(facts) + len(priority_facts),
            coverage=coverage,
            insights=understanding.insights,
            understanding=understanding,
        )

    async def insights_for_user(self, user: User) -> list[UnderstandingInsightOut]:
        return await self.insights.insights_for_user(user.id)

    async def refresh_from_memories(self, user: User, memories: list) -> tuple[int, UserUnderstandingCoverageOut]:
        facts = [fact for memory in memories for fact in self.extraction.extract_from_memory(memory)]
        update_result = await self.updates.apply_facts(user.id, facts)
        priority_result = await self.updates.apply_facts(user.id, await self._priority_facts(user.id))
        coverage = await self.understanding.coverage_for_user(user)
        return update_result.created + priority_result.created, coverage

    async def _model(self, user_id: UUID, items: list[UserUnderstanding]) -> UnderstandingModelOut:
        model = {
            "identity": {"name": "", "background": [], "personalInformation": []},
            "personalLife": {"interests": [], "habits": [], "preferences": [], "healthGoals": []},
            "professionalLife": {"company": [], "role": [], "projects": [], "responsibilities": []},
            "goals": {"shortTermGoals": [], "longTermGoals": [], "mission": []},
            "relationships": {"importantPeople": [], "commitments": []},
            "currentState": {"currentFocus": [], "currentStruggles": [], "openLoops": []},
            "intelligence": {"whatMattersMost": [], "priorities": [], "recommendedNextActions": await self.priorities.recommended_next_actions(user_id)},
        }
        mapping = {
            "about_me": ("identity", "personalInformation"),
            "interests": ("personalLife", "interests"),
            "habits": ("personalLife", "habits"),
            "preferences": ("personalLife", "preferences"),
            "health_goals": ("personalLife", "healthGoals"),
            "company": ("professionalLife", "company"),
            "job": ("professionalLife", "role"),
            "startup": ("professionalLife", "projects"),
            "projects": ("professionalLife", "projects"),
            "responsibilities": ("professionalLife", "responsibilities"),
            "skills": ("professionalLife", "responsibilities"),
            "short_term_goals": ("goals", "shortTermGoals"),
            "long_term_goals": ("goals", "longTermGoals"),
            "missions": ("goals", "mission"),
            "important_people": ("relationships", "importantPeople"),
            "commitments": ("relationships", "commitments"),
            "current_focus": ("currentState", "currentFocus"),
            "current_struggles": ("currentState", "currentStruggles"),
            "open_loops": ("currentState", "openLoops"),
            "priorities": ("intelligence", "priorities"),
            "next_suggested_actions": ("intelligence", "recommendedNextActions"),
        }
        for item in items:
            if item.category == "profile" or not item.value.strip():
                continue
            section_field = mapping.get(item.category)
            if not section_field:
                continue
            section, field = section_field
            self._append(model[section], field, item.value)
        if model["currentState"]["currentFocus"]:
            model["intelligence"]["whatMattersMost"] = model["currentState"]["currentFocus"][:3]
        elif model["goals"]["mission"]:
            model["intelligence"]["whatMattersMost"] = model["goals"]["mission"][:3]
        return UnderstandingModelOut(**model)

    async def _priority_facts(self, user_id: UUID) -> list[UnderstandingFact]:
        priorities = await self.priorities.priorities_for_user(user_id, limit=4)
        actions = await self.priorities.recommended_next_actions(user_id, limit=3)
        facts = [
            UnderstandingFact(
                category="priorities",
                section="intelligence",
                field="priorities",
                title="Priorities",
                value=item["title"],
                confidence=min(item["score"], 0.95),
                evidence=[item["reason"]],
            )
            for item in priorities
        ]
        facts.extend(
            UnderstandingFact(
                category="next_suggested_actions",
                section="intelligence",
                field="recommendedNextActions",
                title="Next Suggested Actions",
                value=action,
                confidence=0.82,
                evidence=["Generated by the priority engine."],
            )
            for action in actions
        )
        return facts

    def _out(
        self,
        user: User,
        profile: dict,
        model: UnderstandingModelOut,
        summary: dict,
        coverage: UserUnderstandingCoverageOut,
        insights: list[UnderstandingInsightOut],
    ) -> UserUnderstandingEngineOut:
        now = datetime.now(timezone.utc)
        return UserUnderstandingEngineOut(
            id=profile["id"],
            userId=user.id,
            personal=profile.get("personal", {}),
            professional=profile.get("professional", {}),
            goals=profile.get("goals", {}),
            preferences=profile.get("preferences", {}),
            learning=profile.get("learning", {}),
            currentFocus=profile.get("currentFocus", {}),
            understandingModel=model,
            summary=summary,
            coverage=coverage,
            insights=insights,
            createdAt=profile.get("createdAt", now),
            updatedAt=profile.get("updatedAt", now),
        )

    @staticmethod
    def _summary(model: UnderstandingModelOut, insights: list[UnderstandingInsightOut]) -> dict:
        data = model.model_dump()
        return {
            "whoYouAre": UnderstandingEngineService._first(data["identity"].get("background") or data["identity"].get("personalInformation")) or data["identity"].get("name") or "",
            "whatYouCareAbout": UnderstandingEngineService._first(data["goals"].get("mission") or data["personalLife"].get("interests")),
            "whatYouAreWorkingOn": UnderstandingEngineService._first(data["currentState"].get("currentFocus") or data["professionalLife"].get("projects")),
            "whatYouShouldDoNext": insights[0].action if insights and insights[0].action else UnderstandingEngineService._first(data["intelligence"].get("recommendedNextActions")),
        }

    @staticmethod
    def _append(section: dict, field: str, value: str) -> None:
        existing = section.get(field)
        if isinstance(existing, list):
            if value not in existing:
                existing.append(value)
            section[field] = existing[:8]
        elif not existing:
            section[field] = value

    @staticmethod
    def _first(value) -> str:
        if isinstance(value, list):
            return value[0] if value else ""
        return value or ""
