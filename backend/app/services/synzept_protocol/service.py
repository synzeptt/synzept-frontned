from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.synzept_protocol import (
    ProtocolAuditLogOut,
    ProtocolPermissionGrantOut,
    ProtocolPermissionRequestIn,
    ProtocolResourceOut,
    ProtocolSubscriptionIn,
    ProtocolSubscriptionOut,
    SynzeptProtocolOut,
)
from app.services.synzept_protocol.mock_data import MOCK_PROTOCOL


class SynzeptProtocolService:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = deepcopy(data or MOCK_PROTOCOL)

    def manifest(self) -> SynzeptProtocolOut:
        return SynzeptProtocolOut(**self.data)

    def resources(self, resource_type: str | None = None) -> list[ProtocolResourceOut]:
        rows = self.data["resources"]
        if resource_type:
            rows = [row for row in rows if row["type"] == resource_type]
        return [ProtocolResourceOut(**row) for row in rows]

    def resource_detail(self, resource_type: str, resource_id: str) -> ProtocolResourceOut | None:
        match = next((row for row in self.data["resources"] if row["type"] == resource_type and row["id"] == resource_id), None)
        return ProtocolResourceOut(**match) if match else None

    def update_resource(self, resource_type: str, resource_id: str, payload: dict[str, Any]) -> dict[str, str | bool]:
        resource = next((row for row in self.data["resources"] if row["type"] == resource_type and row["id"] == resource_id), None)
        if not resource:
            return {"status": "not_found", "updated": False, "resourceId": resource_id}
        resource["data"] = {**resource["data"], **payload}
        resource["updatedAt"] = "2026-07-07T19:30:00+05:30"
        return {"status": "updated_mock", "updated": True, "resourceId": resource_id}

    def permission_grants(self) -> list[ProtocolPermissionGrantOut]:
        return [ProtocolPermissionGrantOut(**grant) for grant in self.data["permissionGrants"]]

    def request_permission(self, body: ProtocolPermissionRequestIn) -> ProtocolPermissionGrantOut:
        grant = {
            "id": f"grant-{body.appId}-{body.resourceType}",
            "appId": body.appId,
            "appName": body.appName,
            "resourceType": body.resourceType,
            "scopes": body.scopes,
            "status": "pending_user_approval",
            "grantedAt": "2026-07-07T19:30:00+05:30",
            "expiresAt": None,
            "purpose": body.purpose,
        }
        self.data["permissionGrants"].append(grant)
        return ProtocolPermissionGrantOut(**grant)

    def revoke_permission(self, grant_id: str) -> dict[str, str | bool]:
        grant = next((row for row in self.data["permissionGrants"] if row["id"] == grant_id), None)
        if not grant:
            return {"status": "not_found", "revoked": False, "grantId": grant_id}
        grant["status"] = "revoked"
        return {"status": "revoked", "revoked": True, "grantId": grant_id}

    def subscriptions(self) -> list[ProtocolSubscriptionOut]:
        return [ProtocolSubscriptionOut(**subscription) for subscription in self.data["subscriptions"]]

    def create_subscription(self, body: ProtocolSubscriptionIn) -> ProtocolSubscriptionOut:
        subscription = {
            "id": f"sub-{body.appId}-{body.resourceType}",
            "appId": body.appId,
            "resourceType": body.resourceType,
            "eventTypes": body.eventTypes,
            "callbackUrl": body.callbackUrl,
            "status": "active",
            "createdAt": "2026-07-07T19:30:00+05:30",
        }
        self.data["subscriptions"].append(subscription)
        return ProtocolSubscriptionOut(**subscription)

    def audit_logs(self) -> list[ProtocolAuditLogOut]:
        return [ProtocolAuditLogOut(**item) for item in self.data["auditLogs"]]
