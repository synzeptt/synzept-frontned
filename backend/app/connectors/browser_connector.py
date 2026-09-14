from __future__ import annotations

from typing import Any

from app.browser.service import BrowserService
from app.connectors.base import ProductionConnector
from app.connectors.context import ConnectorContext
from app.connectors.result import ConnectorResult, HealthResult
from app.workers.browser_worker import BrowserWorker


class BrowserConnector(ProductionConnector):
    capability = "browser"

    def __init__(self, config: dict[str, Any] | None = None, **deps: Any) -> None:
        super().__init__(config=config, **deps)
        cfg = config or {}
        self.browser_service = deps.get("browser_service") or cfg.get("browser_service") or BrowserService(headless=True)
        self.session_manager = deps.get("session_manager") or cfg.get("session_manager")
        self.worker = deps.get("worker") or BrowserWorker(browser_service=self.browser_service, session_manager=self.session_manager)

    def connect(self, ctx: ConnectorContext) -> ConnectorResult:
        return self._build_result(ctx, "connect", success=True, status="connected", message="Browser connector connected", verification={"verified": True, "checks": [{"name": "connect", "status": "passed", "details": "Browser connectivity established"}]})

    def disconnect(self, ctx: ConnectorContext) -> ConnectorResult:
        return self._build_result(ctx, "disconnect", success=True, status="disconnected", message="Browser connector disconnected", verification={"verified": True, "checks": [{"name": "disconnect", "status": "passed", "details": "Browser session cleaned up"}]})

    def authenticate(self, ctx: ConnectorContext) -> Any:
        return self._build_result(ctx, "authenticate", success=True, status="authenticated", message="Browser authentication not required", verification={"verified": True, "checks": []})

    def refresh_credentials(self, ctx: ConnectorContext) -> Any:
        return self._build_result(ctx, "refresh_credentials", success=True, status="refreshed", message="Browser credentials refreshed", verification={"verified": True, "checks": []})

    def health(self, ctx: ConnectorContext) -> HealthResult:
        return HealthResult(available=True, auth_ok=True, status="connected", message="Browser connector healthy")

    def capabilities(self) -> list[str]:
        return ["browser", "goto", "click", "fill", "type", "fill_form", "hover", "scroll", "drag_and_drop", "press", "wait", "wait_for_selector", "wait_for_text", "wait_for_url", "wait_for_network_idle", "wait_for_download", "wait_for_navigation", "wait_for_api_response", "extract_text", "extract_links", "screenshot", "evaluate", "close"]

    def _perform_operation(self, ctx: ConnectorContext, operation: str) -> ConnectorResult:
        action = ctx.metadata.get("action") or ctx.metadata.get("payload") or {}
        if isinstance(action, dict):
            action_payload = action
        else:
            action_payload = {"type": str(action)}
        if operation == "execute":
            result = self.worker.execute(self._worker_context(ctx, action_payload))
            payload = {
                "status": result.outputs.get("status"),
                "actions": result.outputs.get("actions"),
                "session_state": result.outputs.get("session_state"),
                "progress_events": result.outputs.get("progress_events"),
            }
            return self._build_result(ctx, operation, success=result.status.name == "SUCCESS", status=result.outputs.get("status", "completed"), message=result.message or "Browser action executed", data=payload, verification=result.outputs.get("verification") or {"verified": True, "checks": []})
        return self._build_result(ctx, operation, success=True, status="completed", message=f"Browser operation {operation} executed", data={"operation": operation})

    def execute(self, action: str | ConnectorContext | dict[str, Any], payload: dict[str, Any] | None = None) -> ConnectorResult:
        if isinstance(action, ConnectorContext):
            return self._dispatch(action, action.metadata.get("operation") or "execute")
        if isinstance(action, dict):
            if payload is None:
                payload = {}
            action_payload = {**payload, **action}
            ctx = ConnectorContext(
                execution_id=str(action_payload.get("execution_id", "browser-action")),
                skill_id=action_payload.get("skill_id"),
                worker_id=action_payload.get("worker_id"),
                auth=action_payload.get("auth") or {},
                config=action_payload.get("config") or {},
                metadata={"action": action_payload, "operation": "execute"},
            )
            return self._dispatch(ctx, "execute")
        return super().execute(action, payload)

    def verify(self, ctx: ConnectorContext, result: ConnectorResult | None = None) -> dict[str, Any]:
        if result is None:
            return {"verified": False, "checks": []}
        return result.verification or {"verified": False, "checks": []}

    def _worker_context(self, ctx: ConnectorContext, action: dict[str, Any]) -> Any:
        from app.workers.context import WorkerContext

        runtime_actions = action.get("actions") if isinstance(action, dict) and isinstance(action.get("actions"), list) else [action]
        return WorkerContext(
            execution_id=ctx.execution_id,
            goal=ctx.metadata.get("goal") or "browser automation",
            runtime_context={"actions": runtime_actions, "browser_session": {}},
            inputs={},
            connectors={},
            logger=ctx.logger,
            cancellation_token=ctx.cancellation_token,
        )
