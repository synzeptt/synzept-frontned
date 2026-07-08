from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.schemas.continue_context import ContinueContextOut
from app.schemas.user_understanding import UserUnderstandingProfileOut
from app.services.s1_context_service import S1ContextService


@pytest.mark.asyncio
async def test_s1_context_composes_existing_systems(monkeypatch):
    user_id = uuid4()
    user = SimpleNamespace(id=user_id)
    recommendation = SimpleNamespace(title="Continue the launch review", reason="It is the clearest open loop.", href="/chat")
    personal_os = SimpleNamespace(
        greeting="Welcome back",
        current_mission="Ship Synzept S1",
        current_focus="Validate continuity",
        open_loops=[SimpleNamespace(id="loop-1", title="Review launch", next_step="Open the checklist", description="", href="/chat", priority="high", type="open_loop")],
        suggested_next_action=recommendation,
    )
    returning = SimpleNamespace(
        is_returning=True,
        days_since_last_seen=7,
        what_changed=[SimpleNamespace(id="change-1", title="Daily Brief updated", description="New focus", href="/daily-brief", type="brief")],
    )
    dashboard = SimpleNamespace(personal_os=personal_os, returning_user=returning, recent_activity=[])
    continuation = ContinueContextOut(headline="Continue", cards=[], context_used={"memories": 3})
    profile = UserUnderstandingProfileOut(user_id=user_id, current_mission=["Ship Synzept S1"])
    brief = {
        "id": None,
        "userId": user_id,
        "contextSnapshotId": None,
        "briefDate": "2026-06-21",
        "whatMattersToday": [],
        "whatChanged": [],
        "openLoops": [],
        "recommendedNextStep": {},
        "focusForToday": {},
        "currentMission": {},
        "currentFocus": {},
        "recentProgress": [],
        "recentDecisions": [],
        "upcomingPriorities": [],
        "projectsNeedingAttention": [],
        "contextToRemember": [],
        "createdAt": None,
        "updatedAt": None,
    }

    async def dashboard_context(*_args, **_kwargs):
        return dashboard

    async def continue_context(*_args, **_kwargs):
        return continuation

    async def daily_context(*_args, **_kwargs):
        return brief

    async def understanding_context(*_args, **_kwargs):
        return profile

    monkeypatch.setattr("app.services.s1_context_service.DashboardAggregationService.get_dashboard", dashboard_context)
    monkeypatch.setattr("app.services.s1_context_service.ContinueContextService.get_context", continue_context)
    monkeypatch.setattr("app.services.s1_context_service.DailyBriefPhase8Service.today", daily_context)
    monkeypatch.setattr("app.services.s1_context_service.UserUnderstandingService.profile_for_user", understanding_context)

    result = await S1ContextService(None).get_context(user)

    assert result.version == "s1"
    assert result.home.mission == "Ship Synzept S1"
    assert result.home.last_time[0].title == "Daily Brief updated"
    assert result.home.open_loops[0].priority == "high"
    assert result.context_sources["memories"] == 3
    assert result.capabilities["platforms"] == ["web", "mobile"]
