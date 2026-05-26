from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.task import TaskCreate, TaskUpdate
from app.workspace.continuity import ProjectContinuityService


def test_task_status_aliases_normalize_to_continuity_vocabulary():
    assert TaskUpdate(status="pending").status == "todo"
    assert TaskUpdate(status="done").status == "completed"
    assert TaskUpdate(status="in_progress").status == "in_progress"


def test_task_rejects_invalid_status_and_priority():
    with pytest.raises(ValidationError):
        TaskUpdate(status="blocked")
    with pytest.raises(ValidationError):
        TaskCreate(title="Ship", priority="urgent")


def test_project_continuity_summary_combines_linked_resources():
    project = SimpleNamespace(description="Investor strategy workspace.", context_summary=None)
    conversations = [SimpleNamespace(title="Roadmap discussion")]
    notes = [SimpleNamespace(title="Investor memo", summary="Memo summary")]
    tasks = [SimpleNamespace(title="Draft outreach list")]
    memories = [SimpleNamespace(summary="Prefers concise strategy docs", content="")]

    summary = ProjectContinuityService._continuity_summary(project, conversations, notes, tasks, memories)

    assert "Investor strategy workspace" in summary
    assert "Roadmap discussion" in summary
    assert "Draft outreach list" in summary
    assert "Prefers concise strategy docs" in summary
