from __future__ import annotations

from typing import Any

from .base import Connector
from .context import ConnectorContext
from .registry import default_registry
from .result import AuthenticationResult, ConnectorResult, HealthResult


def _resource_name(ctx: ConnectorContext) -> str:
    return str(ctx.metadata.get("resource_id") or ctx.metadata.get("resource_name") or "resource")


@default_registry.autoregister("google_account")
class GoogleAccountConnector(Connector):
    """A lightweight first-party connector for Google account capabilities."""

    def connect(self, ctx: ConnectorContext) -> ConnectorResult:
        return ConnectorResult(success=True, data={"provider": "google", "status": "connected", "authenticated": True}, message="Google account connector ready")

    def disconnect(self, ctx: ConnectorContext) -> ConnectorResult:
        return ConnectorResult(success=True, data={"provider": "google", "status": "disconnected"}, message="Google account disconnected")

    def authenticate(self, ctx: ConnectorContext) -> AuthenticationResult:
        return AuthenticationResult(authenticated=True, token="google-token", message="Google account authentication available")

    def refresh_credentials(self, ctx: ConnectorContext) -> AuthenticationResult:
        return AuthenticationResult(authenticated=True, token="google-token-refreshed", message="Google account credentials refreshed")

    def health(self, ctx: ConnectorContext) -> HealthResult:
        return HealthResult(available=True, auth_ok=True, message="Google account connector healthy")

    def capabilities(self) -> list[str]:
        return ["google_account", "gmail", "google_calendar", "google_drive"]

    def search(self, ctx: ConnectorContext) -> ConnectorResult:
        query = str(ctx.metadata.get("query") or ctx.metadata.get("search_query") or "")
        return ConnectorResult(success=True, data={"items": [{"id": "google-item-1", "title": f"Google result for {query or 'query'}", "kind": "google"}]}, message="Google search executed")

    def read(self, ctx: ConnectorContext) -> ConnectorResult:
        resource_id = _resource_name(ctx)
        return ConnectorResult(success=True, data={"resource_id": resource_id, "account": "google-user", "kind": "google"}, message=f"Read resource {resource_id}")

    def create(self, ctx: ConnectorContext) -> ConnectorResult:
        resource_id = _resource_name(ctx)
        return ConnectorResult(success=True, data={"id": f"created-{resource_id}", "resource_id": resource_id}, message=f"Created {resource_id}")

    def update(self, ctx: ConnectorContext) -> ConnectorResult:
        resource_id = _resource_name(ctx)
        return ConnectorResult(success=True, data={"id": f"updated-{resource_id}", "resource_id": resource_id}, message=f"Updated {resource_id}")

    def delete(self, ctx: ConnectorContext) -> ConnectorResult:
        if ctx.metadata.get("requires_approval") or ctx.metadata.get("approval_required") is not False:
            return ConnectorResult(success=False, data={"approval_required": True, "resource_id": _resource_name(ctx)}, message="Deletion requires approval")
        return ConnectorResult(success=True, data={"deleted": True, "resource_id": _resource_name(ctx)}, message="Deleted resource")

    def execute(self, ctx: ConnectorContext) -> ConnectorResult:
        return ConnectorResult(success=True, data={"executed": True, "resource_id": _resource_name(ctx)}, message="Google account execution placeholder")
