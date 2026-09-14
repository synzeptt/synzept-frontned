import time
from typing import Any, Dict, List
from .base import Connector
from .context import ConnectorContext
from .result import (
    ConnectorResult,
    AuthenticationResult,
    HealthResult,
    SearchResult,
    ReadResult,
    WriteResult,
)


class MockConnector(Connector):
    """Simple mock connector that simulates external service behavior."""

    def connect(self, ctx: ConnectorContext) -> ConnectorResult:
        return ConnectorResult(success=True, data={"connected": True})

    def disconnect(self, ctx: ConnectorContext) -> ConnectorResult:
        return ConnectorResult(success=True, data={"disconnected": True})

    def authenticate(self, ctx: ConnectorContext) -> AuthenticationResult:
        token = ctx.config.get("token") or ctx.auth.get("token")
        if token:
            return AuthenticationResult(authenticated=True, token=token)
        # simulate creating a token
        return AuthenticationResult(authenticated=True, token="mock-token")

    def refresh_credentials(self, ctx: ConnectorContext) -> AuthenticationResult:
        return AuthenticationResult(authenticated=True, token="refreshed-token")

    def health(self, ctx: ConnectorContext) -> HealthResult:
        return HealthResult(available=True, latency_seconds=0.01, auth_ok=True, last_success=time.time())

    def capabilities(self) -> List[str]:
        return ["search", "read", "create", "update", "delete"]

    def search(self, ctx: ConnectorContext) -> SearchResult:
        q = ctx.metadata.get("query")
        return SearchResult(success=True, results=[{"id": "1", "text": f"result for {q}"}])

    def read(self, ctx: ConnectorContext) -> ReadResult:
        return ReadResult(success=True, record={"id": ctx.metadata.get("id"), "data": "hello"})

    def create(self, ctx: ConnectorContext) -> WriteResult:
        return WriteResult(success=True, id="new-1", record=ctx.metadata)

    def update(self, ctx: ConnectorContext) -> WriteResult:
        return WriteResult(success=True, id=ctx.metadata.get("id"), record=ctx.metadata)

    def delete(self, ctx: ConnectorContext) -> ConnectorResult:
        return ConnectorResult(success=True, data={"deleted": ctx.metadata.get("id")})

    def execute(self, ctx: ConnectorContext) -> ConnectorResult:
        return ConnectorResult(success=True, data={"executed": True})
