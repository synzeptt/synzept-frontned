from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.continuity.restoration import ContinuityRestorationService
from app.services.continuity.intelligence import ContinuityIntelligenceService
from app.daily.operating import DailyOperatingService
from app.services.dashboard.aggregation import DashboardAggregationService


def test_dashboard_priority_ranking_prefers_high_and_in_progress_tasks():
    now = datetime.now(timezone.utc)
    tasks = [
        SimpleNamespace(title="Low", priority="low", status="todo", due_at=None, updated_at=now),
        SimpleNamespace(title="High", priority="high", status="todo", due_at=None, updated_at=now),
        SimpleNamespace(title="Moving", priority="medium", status="in_progress", due_at=None, updated_at=now),
    ]

    ranked = DashboardAggregationService._rank_priorities(tasks)

    assert [task.title for task in ranked] == ["High", "Moving", "Low"]


def test_recent_activity_merges_workspace_sources_by_recency():
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    new = datetime(2026, 1, 2, tzinfo=timezone.utc)
    project_id = uuid4()
    conversations = [
        SimpleNamespace(id=uuid4(), title="Thread", summary="Recent thread", active_intent=None, project_id=project_id, updated_at=new)
    ]
    notes = [SimpleNamespace(id=uuid4(), title="Note", summary=None, content="Older note", project_id=None, updated_at=old)]

    activity = DashboardAggregationService._recent_activity([], conversations, notes, [])

    assert activity[0].type == "conversation"
    assert activity[0].title == "Thread"
    assert activity[1].type == "note"


def test_continuity_cards_include_unfinished_task_and_project_restore_points():
    now = datetime.now(timezone.utc)
    project_id = uuid4()
    tasks = [
        SimpleNamespace(
            id=uuid4(),
            title="Draft launch memo",
            description="Finish the launch positioning.",
            priority="high",
            status="todo",
            due_at=None,
            project_id=project_id,
            updated_at=now,
        )
    ]
    projects = [
        SimpleNamespace(
            id=project_id,
            name="Launch",
            description=None,
            context_summary="Launch workspace context.",
            status="active",
            updated_at=now,
        )
    ]

    cards = ContinuityRestorationService(None).build_cards(projects=projects, conversations=[], tasks=tasks)

    assert cards[0].type == "task"
    assert any(card.type == "project" for card in cards)
    assert cards[0].continuation_prompt.startswith("Continue")
    assert cards[0].continuity_score > 0


def test_continuity_cards_boost_due_and_open_thread_restoration():
    now = datetime.now(timezone.utc)
    project_id = uuid4()
    overdue_task = SimpleNamespace(
        id=uuid4(),
        title="Send investor update",
        description="Needs to go out.",
        priority="medium",
        status="todo",
        due_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        project_id=project_id,
        updated_at=now,
    )
    passive_task = SimpleNamespace(
        id=uuid4(),
        title="Organize someday list",
        description=None,
        priority="medium",
        status="todo",
        due_at=None,
        project_id=None,
        updated_at=now,
    )
    conversation = SimpleNamespace(
        id=uuid4(),
        title="Roadmap planning",
        summary="Unresolved launch sequence.",
        active_intent="Decide launch sequence",
        project_id=project_id,
        archived_at=None,
        updated_at=now,
    )

    cards = ContinuityRestorationService(None).build_cards(
        projects=[],
        conversations=[conversation],
        tasks=[passive_task, overdue_task],
    )

    assert cards[0].title in {"Send investor update", "Roadmap planning"}
    assert any(card.reason in {"Timed unfinished work.", "Open thread with resumable context."} for card in cards)


def test_continuity_cards_prefer_unfinished_work_over_passive_recent_notes():
    now = datetime.now(timezone.utc)
    project_id = uuid4()
    task = SimpleNamespace(
        id=uuid4(),
        title="Finish onboarding redesign",
        description=None,
        priority="medium",
        status="in_progress",
        due_at=None,
        project_id=project_id,
        updated_at=now,
    )
    note = SimpleNamespace(
        id=uuid4(),
        title="Reference note",
        summary=None,
        content="Passive note with context.",
        project_id=None,
        updated_at=now,
    )

    cards = ContinuityRestorationService(None).build_cards(projects=[], conversations=[], tasks=[task], notes=[note])

    assert cards[0].type == "task"
    assert cards[0].reason == "Already in progress."


def test_continuity_intelligence_surfaces_recurring_priorities_themes_and_evolution():
    now = datetime.now(timezone.utc)
    project_id = uuid4()
    intelligence = ContinuityIntelligenceService().build_intelligence(
        projects=[
            SimpleNamespace(
                id=project_id,
                name="Dashboard simplification",
                description="Reduce noise and keep the workspace calm.",
                context_summary="Dashboard simplification remains active.",
                status="active",
                updated_at=now,
            )
        ],
        conversations=[
            SimpleNamespace(
                id=uuid4(),
                title="Onboarding refinement",
                summary="Keep refining onboarding and continuity.",
                active_intent="Refine onboarding workflow",
                project_id=project_id,
                archived_at=None,
                updated_at=now,
            )
        ],
        tasks=[
            SimpleNamespace(
                id=uuid4(),
                title="Refine onboarding flow",
                description="Finish onboarding refinement and keep the handoff calm.",
                priority="high",
                status="in_progress",
                due_at=None,
                project_id=project_id,
                updated_at=now,
            )
        ],
        notes=[
            SimpleNamespace(
                id=uuid4(),
                title="Continuity note",
                summary="Dashboard simplification needs to stay easy to revisit.",
                content="Dashboard simplification and onboarding refinement both recur.",
                project_id=project_id,
                updated_at=now,
            )
        ],
        memories=[
            SimpleNamespace(
                id=uuid4(),
                memory_type="goals",
                category="goals",
                summary="Keep improving onboarding refinement and memory systems.",
                content="Onboarding refinement and dashboard simplification should stay lightweight.",
                importance_score=0.9,
                retrieval_count=0,
                updated_at=now,
            )
        ],
        history=[
            SimpleNamespace(
                summary_date=now.date(),
                summary="Onboarding refinement and dashboard simplification stayed active.",
                metadata_={
                    "recurring_priorities": ["Onboarding refinement"],
                    "recurring_themes": ["Dashboard simplification"],
                    "unresolved_items": ["Refine onboarding flow"],
                    "score": 0.78,
                },
                unfinished_priorities=["Refine onboarding flow"],
            )
        ],
    )

    assert intelligence.recurring_priorities
    assert intelligence.ongoing_themes
    assert intelligence.timeline[0].headline in {"Current continuity snapshot", "Onboarding refinement", "Dashboard simplification"}
    assert any("onboarding" in item.lower() for item in intelligence.memory_evolution)
    assert any("dashboard simplification" in item.lower() for item in intelligence.memory_evolution)


def test_memory_highlights_rank_continuity_value_above_recent_noise():
    now = datetime.now(timezone.utc)
    old_goal = SimpleNamespace(
        id=uuid4(),
        memory_type="goals",
        category="goals",
        summary=None,
        content="Launch Synzept with strong continuity and memory relevance.",
        importance_score=0.9,
        retrieval_count=0,
        created_at=now,
        updated_at=now,
    )
    noisy_recent = SimpleNamespace(
        id=uuid4(),
        memory_type="other",
        category="other",
        summary=None,
        content="A random styling note.",
        importance_score=0.2,
        retrieval_count=0,
        created_at=now,
        updated_at=now,
    )

    ranked = ContinuityRestorationService(None).rank_memories_for_dashboard([noisy_recent, old_goal])

    assert ranked[0] is old_goal


def test_manual_daily_wrap_summary_preserves_tomorrow_and_resume_points():
    summary = DailyOperatingService._manual_wrap_summary(
        progress_summary="Moved the launch plan forward.",
        completed=["Drafted homepage"],
        unfinished=["Review onboarding"],
        insights=["Users need calmer restoration"],
        tomorrow_priorities=["Finish onboarding review"],
        continuation_points=["Resume from dashboard continuity cards"],
    )

    assert "Moved the launch plan forward" in summary
    assert "Finish onboarding review" in summary
    assert "Resume from dashboard continuity cards" in summary


def test_daily_wrap_clean_items_deduplicates_and_trims_empty_values():
    cleaned = DailyOperatingService._clean_items([" Focus ", "", "Focus", "Next"])

    assert cleaned == ["Focus", "Next"]
