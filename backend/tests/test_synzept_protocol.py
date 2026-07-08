from app.schemas.synzept_protocol import ProtocolPermissionRequestIn, ProtocolSubscriptionIn
from app.services.synzept_protocol import SynzeptProtocolService


def test_manifest_includes_initial_resource_types():
    manifest = SynzeptProtocolService().manifest()

    assert manifest.resourceTypes == [
        "profile",
        "goals",
        "missions",
        "projects",
        "decisions",
        "knowledge",
        "memories",
        "relationships",
        "preferences",
    ]
    assert len(manifest.resources) == len(manifest.resourceTypes)


def test_resources_can_be_filtered_and_read_by_id():
    service = SynzeptProtocolService()

    goals = service.resources(resource_type="goals")
    detail = service.resource_detail("goals", "goal-return-user-clarity")

    assert len(goals) == 1
    assert goals[0].type == "goals"
    assert detail is not None
    assert detail.id == "goal-return-user-clarity"


def test_permission_grants_are_scoped_and_revocable():
    service = SynzeptProtocolService()
    grants = service.permission_grants()

    assert all(grant.resourceType and grant.scopes and grant.status for grant in grants)
    assert any(grant.status == "revoked" for grant in grants)

    result = service.revoke_permission("grant-calendar-focus")

    assert result == {"status": "revoked", "revoked": True, "grantId": "grant-calendar-focus"}
    assert next(grant for grant in service.permission_grants() if grant.id == "grant-calendar-focus").status == "revoked"


def test_permission_request_starts_pending_user_approval():
    request = ProtocolPermissionRequestIn(
        appId="app-task-bridge",
        appName="Task Bridge",
        resourceType="projects",
        scopes=["read:summary", "write:task_link"],
        purpose="Create linked tasks from approved project summaries.",
    )

    grant = SynzeptProtocolService().request_permission(request)

    assert grant.status == "pending_user_approval"
    assert grant.resourceType == "projects"
    assert "write:task_link" in grant.scopes


def test_subscriptions_can_be_created_for_change_events():
    body = ProtocolSubscriptionIn(
        appId="app-focus-calendar",
        resourceType="goals",
        eventTypes=["updated"],
        callbackUrl="https://focus-calendar.example.dev/synzept/webhook",
    )

    subscription = SynzeptProtocolService().create_subscription(body)

    assert subscription.status == "active"
    assert subscription.resourceType == "goals"
    assert subscription.eventTypes == ["updated"]


def test_audit_logs_explain_data_sharing_results():
    logs = SynzeptProtocolService().audit_logs()

    assert logs
    assert any(log.result == "allowed" for log in logs)
    assert any(log.result == "denied_revoked" for log in logs)
    assert all(log.userVisibleSummary for log in logs)


def test_manifest_exposes_sdk_and_auth_developer_experience():
    manifest = SynzeptProtocolService().manifest()

    assert {sdk.language for sdk in manifest.sdks} == {"TypeScript", "Python"}
    assert "PKCE" in manifest.authFlow.flow
    assert any("revoke" in rule.lower() for rule in manifest.authFlow.tokenRules)
