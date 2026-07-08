from app.services.action_center_service import ActionCenterService


def test_action_center_dashboard_contains_expected_sections():
    dashboard = ActionCenterService().get_dashboard()

    assert dashboard.missionTitle
    assert len(dashboard.actions) == 3
    assert dashboard.aiInsight
    assert dashboard.momentumScore >= 0
    assert len(dashboard.openLoops) <= 5
    assert len(dashboard.quickActions) == 4
