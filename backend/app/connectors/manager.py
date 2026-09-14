import asyncio
import logging
from typing import Any, Dict, Optional, Type
import time

from .registry import default_registry
from .context import ConnectorContext
from .result import ConnectorResult, HealthResult, ExecutionMetrics, AuthenticationResult
from .errors import PermissionDenied, RetryableFailure, ConnectorError
from app.events import default_event_bus
from app.models.connected_app import ConnectedAppAccount
from app.services.connected_apps.oauth_lifecycle import ConnectedAppOAuthLifecycle
from app.core.config import get_settings
from sqlalchemy import select

logger = logging.getLogger(__name__)


class ConnectorManager:
    def __init__(self, registry=default_registry, dependencies: Dict[str, Any] = None, event_bus=None):
        self.registry = registry
        self.dependencies = dependencies or {}
        self.event_bus = event_bus or default_event_bus
        self._instances: Dict[str, Any] = {}

    async def request_async(self, capability: str, method: str, ctx: ConnectorContext) -> ConnectorResult:
        """Resolve the user's encrypted Google account, refresh it when needed, then execute."""
        session = self.dependencies.get("session")
        user_id = ctx.metadata.get("user_id")
        provider = capability if capability.startswith("google_") else {"gmail": "google_gmail"}.get(capability, capability)
        if session is not None and user_id and provider.startswith("google_"):
            lifecycle = ConnectedAppOAuthLifecycle(session)
            account = await lifecycle.required_account(user_id, provider)
            settings = get_settings()
            required_scopes = {
                "google_gmail": "https://www.googleapis.com/auth/gmail.readonly",
                "google_calendar": "https://www.googleapis.com/auth/calendar.readonly",
                "google_drive": "https://www.googleapis.com/auth/drive.metadata.readonly",
                "google_docs": "https://www.googleapis.com/auth/documents",
                "google_sheets": "https://www.googleapis.com/auth/spreadsheets",
                "google_slides": "https://www.googleapis.com/auth/presentations",
            }.get(provider)
            if required_scopes and required_scopes not in (account.scopes or []):
                raise PermissionDenied(f"{provider} requires reconnecting with scope {required_scopes}")
            access_token = await lifecycle.access_token(
                account,
                label=provider,
                token_url="https://oauth2.googleapis.com/token",
                client_id=settings.google_connected_apps_client_id,
                client_secret=settings.google_connected_apps_client_secret,
            )
            auth = {**ctx.auth, "connected": True, "token_valid": True, "access_token": access_token, "scopes": account.scopes}
            ctx = ConnectorContext(
                execution_id=ctx.execution_id,
                skill_id=ctx.skill_id,
                worker_id=ctx.worker_id,
                auth=auth,
                config=ctx.config,
                metadata={**ctx.metadata, "user_id": user_id, "access_token": access_token},
                memory_snapshot=ctx.memory_snapshot,
                logger=ctx.logger,
                cancellation_token=ctx.cancellation_token,
            )
        return await asyncio.to_thread(self.request, capability, method, ctx)

    def get_connector_class(self, capability: str) -> Type:
        cls = self.registry.get_connector_class(capability)
        if cls is None:
            raise KeyError(f"Connector not found for capability: {capability}")
        return cls

    def instantiate(self, capability: str, config: Dict[str, Any] = None):
        cls = self.get_connector_class(capability)
        inst = cls(config=config or {}, **self.dependencies)
        self._instances[capability] = inst
        self.event_bus.emit("connector.registered", {"capability": capability})
        return inst

    def authenticate(self, capability: str, ctx: ConnectorContext) -> AuthenticationResult:
        inst = self._instances.get(capability) or self.instantiate(capability, ctx.config)
        self.event_bus.emit("connector.authenticate.started", {"capability": capability, "execution_id": ctx.execution_id})
        try:
            res = inst.authenticate(ctx)
            self.event_bus.emit("connector.authenticate.completed", {"capability": capability, "execution_id": ctx.execution_id, "result": res})
            return res
        except Exception as e:
            self.event_bus.emit("connector.authenticate.failed", {"capability": capability, "execution_id": ctx.execution_id, "error": str(e)})
            raise

    def health(self, capability: str, ctx: ConnectorContext) -> HealthResult:
        inst = self._instances.get(capability) or self.instantiate(capability, ctx.config)
        self.event_bus.emit("connector.health.started", {"capability": capability, "execution_id": ctx.execution_id})
        try:
            res = inst.health(ctx)
            self.event_bus.emit("connector.health.completed", {"capability": capability, "execution_id": ctx.execution_id, "result": res})
            return res
        except Exception as e:
            self.event_bus.emit("connector.health.failed", {"capability": capability, "execution_id": ctx.execution_id, "error": str(e)})
            raise

    def request(self, capability: str, method: str, ctx: ConnectorContext) -> ConnectorResult:
        inst = self._instances.get(capability) or self.instantiate(capability, ctx.config)
        self.event_bus.emit("connector.request.started", {"capability": capability, "method": method, "execution_id": ctx.execution_id})
        metrics = ExecutionMetrics()
        try:
            fn = getattr(inst, method)
            res = fn(ctx)
            metrics.finish()
            res.metrics = metrics
            logger.info(
                "connector_action connector=%s action=%s duration=%.3f success=%s status=%s verification=%s retries=%s error=%s",
                capability,
                method,
                metrics.duration or 0.0,
                res.success,
                res.status,
                bool(res.verification.get("verified")) if isinstance(res.verification, dict) else False,
                res.retries,
                res.error or res.errors,
            )
            self.event_bus.emit("connector.request.completed", {"capability": capability, "method": method, "execution_id": ctx.execution_id, "result": res})
            return res
        except RetryableFailure as e:
            self.event_bus.emit("connector.request.retry", {"capability": capability, "method": method, "execution_id": ctx.execution_id, "error": str(e)})
            raise
        except Exception as e:
            self.event_bus.emit("connector.request.failed", {"capability": capability, "method": method, "execution_id": ctx.execution_id, "error": str(e)})
            raise

    def list_connectors(self):
        return self.registry.list_connectors()
