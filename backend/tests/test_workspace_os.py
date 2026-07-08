from app.schemas.workspace_os import WorkspaceCommandRunIn
from app.services.workspace_os import WorkspaceOSService


def test_workspace_os_home_contains_required_sections():
    snapshot = WorkspaceOSService().snapshot()
    home = snapshot.home

    assert home.currentMission.title
    assert home.todaysFocus
    assert home.activeAgents
    assert home.pendingApprovals
    assert home.recentKnowledge
    assert home.opportunities
    assert home.openLoops
    assert home.dailyBrief.headline


def test_workspace_os_navigation_is_simple_and_persistent():
    nav = WorkspaceOSService().snapshot().navigation

    assert [item.label for item in nav] == [
        "Home",
        "Missions",
        "Knowledge",
        "Projects",
        "Agents",
        "Daily OS",
        "Search",
        "Settings",
    ]


def test_workspace_search_covers_required_domains_and_filters_results():
    service = WorkspaceOSService()
    all_types = {item.type for item in service.search().results}
    filtered = service.search(query="decision", filters=["decision"])

    assert all_types >= {"conversation", "memory", "project", "task", "file", "decision", "people", "mission"}
    assert filtered.results
    assert all(item.type == "decision" for item in filtered.results)


def test_workspace_commands_include_universal_actions():
    commands = WorkspaceOSService().snapshot().commands
    titles = {command.title for command in commands}

    assert {
        "Create a mission",
        "Find a decision",
        "Start a focus session",
        "Ask Synzept",
        "Capture a thought",
    } <= titles


def test_workspace_command_run_never_executes_production_action_in_mock_mode():
    result = WorkspaceOSService().run_command(WorkspaceCommandRunIn(commandId="cmd-focus-session"))

    assert result["status"] == "queued_mock"
    assert result["executed"] is False


def test_agent_workspace_exposes_activity_steps_and_approvals():
    agents = WorkspaceOSService().snapshot().agents

    assert agents
    assert all(agent.goal and agent.status for agent in agents)
    assert any(agent.approvalsAwaitingUser for agent in agents)
