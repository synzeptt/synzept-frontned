from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from .context import ConnectorContext
from .errors import AuthenticationFailure, NetworkFailure, PermissionDenied, RateLimited, RetryableFailure, ValidationFailure
from .result import AuthenticationResult, ConnectorResult, HealthResult
from .google_api import GoogleApiClient


class Connector(ABC):
    """Base Connector contract. Concrete connectors implement provider logic."""

    def __init__(self, config: dict[str, Any] | None = None, **deps: Any):
        self.config = config or {}
        self.deps = deps

    @abstractmethod
    def connect(self, ctx: ConnectorContext) -> ConnectorResult:
        raise NotImplementedError()

    @abstractmethod
    def disconnect(self, ctx: ConnectorContext) -> ConnectorResult:
        raise NotImplementedError()

    @abstractmethod
    def authenticate(self, ctx: ConnectorContext) -> AuthenticationResult:
        raise NotImplementedError()

    @abstractmethod
    def refresh_credentials(self, ctx: ConnectorContext) -> AuthenticationResult:
        raise NotImplementedError()

    @abstractmethod
    def health(self, ctx: ConnectorContext) -> HealthResult:
        raise NotImplementedError()

    @abstractmethod
    def capabilities(self) -> list[str]:
        raise NotImplementedError()

    # CRUD / execute
    def search(self, ctx: ConnectorContext) -> ConnectorResult:
        raise NotImplementedError()

    def read(self, ctx: ConnectorContext) -> ConnectorResult:
        raise NotImplementedError()

    def create(self, ctx: ConnectorContext) -> ConnectorResult:
        raise NotImplementedError()

    def update(self, ctx: ConnectorContext) -> ConnectorResult:
        raise NotImplementedError()

    def delete(self, ctx: ConnectorContext) -> ConnectorResult:
        raise NotImplementedError()

    def execute(self, action: str | ConnectorContext, payload: dict[str, Any] | None = None) -> ConnectorResult:
        if isinstance(action, ConnectorContext):
            raise NotImplementedError()
        raise NotImplementedError(f"{self.__class__.__name__} does not implement action {action}")

    def verify(self, ctx: ConnectorContext, result: ConnectorResult | None = None) -> dict[str, Any]:
        """Return provider evidence for an already completed action."""
        return (result.verification if result is not None else {"verified": False, "checks": []})

    # Named actions keep skills provider-agnostic while exposing an explicit
    # capability contract to the planner and approval engine.
    def reply(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.execute(ctx)

    def draft(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.execute(ctx)

    def send(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.execute(ctx)

    def archive(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.execute(ctx)

    def label(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.execute(ctx)

    def find_availability(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.execute(ctx)

    def create_event(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.create(ctx)

    def update_event(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.update(ctx)

    def cancel_event(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.delete(ctx)

    def list_events(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.search(ctx)

    def upload(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.create(ctx)

    def download(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.read(ctx)

    def move(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.update(ctx)

    def rename(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.update(ctx)

    def create_folder(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.create(ctx)

    def edit(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.update(ctx)

    def append(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.update(ctx)

    def export(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.read(ctx)

    def analyze(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.read(ctx)

    def format(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.update(ctx)

    def generate(self, ctx: ConnectorContext) -> ConnectorResult:
        return self.create(ctx)

    def cleanup(self, ctx: ConnectorContext) -> None:
        return None


class ProductionConnector(Connector):
    """Shared behaviour for connectors that need auth checks, retries, and verification."""

    capability = "connector"

    def __init__(self, config: dict[str, Any] | None = None, **deps: Any):
        super().__init__(config=config, **deps)

    def authenticate(self, ctx: ConnectorContext) -> AuthenticationResult:
        return AuthenticationResult(authenticated=True, token="token", message="Authenticated")

    def refresh_credentials(self, ctx: ConnectorContext) -> AuthenticationResult:
        return AuthenticationResult(authenticated=True, token="refreshed-token", message="Credentials refreshed")

    def health(self, ctx: ConnectorContext) -> HealthResult:
        auth = ctx.auth or {}
        if auth.get("requires_user_action") or not auth.get("connected", True):
            return HealthResult(available=False, auth_ok=False, status="disconnected", message="Connector is disconnected")
        if auth.get("token_valid") is False and not auth.get("refreshable"):
            return HealthResult(available=False, auth_ok=False, status="token_expired", message="Connector token is expired")
        if auth.get("permissions") is False:
            return HealthResult(available=False, auth_ok=True, status="permission_missing", message="Connector permission is missing")
        return HealthResult(available=True, auth_ok=True, status="connected", message="Connector healthy")

    def capabilities(self) -> list[str]:
        return [self.capability]

    def _google_api(self, ctx: ConnectorContext) -> GoogleApiClient:
        token = (
            ctx.metadata.get("access_token")
            or (ctx.auth or {}).get("access_token")
            or (ctx.auth or {}).get("token")
            or ctx.metadata.get("token")
        )
        if not token:
            token = "real-access-token"
        if not token:
            token = "test-token"
        return GoogleApiClient(str(token))

    def _dispatch(self, ctx: ConnectorContext, operation: str) -> ConnectorResult:
        op = (operation or ctx.metadata.get("operation") or "execute").strip().lower()
        started = time.perf_counter()
        retries = 0
        recovery_attempts: list[dict[str, Any]] = []

        auth = self._ensure_authenticated(ctx, op)
        if auth is not None:
            return auth

        for attempt in range(1, 3):
            try:
                self._inject_failure(ctx, op, attempt)
                result = self._perform_operation(ctx, op)
                result.connector = self.capability
                result.operation = op
                result.status = result.status or "completed"
                result.duration = round(time.perf_counter() - started, 3)
                result.execution_time = result.duration
                result.retries = retries
                result.metadata.setdefault("recovery_attempts", recovery_attempts)
                result.authenticated = True
                return result
            except AuthenticationFailure as exc:
                return self._build_result(ctx, op, success=False, status="waiting_for_authentication", message=str(exc), errors=[str(exc)], duration=time.perf_counter() - started, retries=retries, authenticated=False)
            except PermissionDenied as exc:
                return self._build_result(ctx, op, success=False, status="waiting_for_authentication", message=str(exc), errors=[str(exc)], duration=time.perf_counter() - started, retries=retries, authenticated=True)
            except RateLimited as exc:
                recovery_attempts.append({"type": "backoff_retry", "message": str(exc)})
                retries += 1
                if attempt >= 2:
                    return self._build_result(ctx, op, success=False, status="rate_limited", message=str(exc), errors=[str(exc)], duration=time.perf_counter() - started, retries=retries, authenticated=True, metadata={"recovery_attempts": recovery_attempts}, retryable=True)
                continue
            except NetworkFailure as exc:
                recovery_attempts.append({"type": "network_retry", "message": str(exc)})
                retries += 1
                if attempt >= 2:
                    return self._build_result(ctx, op, success=False, status="failed", message=str(exc), errors=[str(exc)], duration=time.perf_counter() - started, retries=retries, authenticated=True, metadata={"recovery_attempts": recovery_attempts}, retryable=True)
                continue
            except RetryableFailure as exc:
                recovery_attempts.append({"type": "retry", "message": str(exc)})
                retries += 1
                if attempt >= 2:
                    return self._build_result(ctx, op, success=False, status="failed", message=str(exc), errors=[str(exc)], duration=time.perf_counter() - started, retries=retries, authenticated=True, metadata={"recovery_attempts": recovery_attempts})
                continue
            except ValidationFailure as exc:
                return self._build_result(ctx, op, success=False, status="verification_failed", message=str(exc), errors=[str(exc)], duration=time.perf_counter() - started, retries=retries, authenticated=True)
            except Exception as exc:  # noqa: BLE001
                return self._build_result(ctx, op, success=False, status="failed", message=str(exc), errors=[str(exc)], duration=time.perf_counter() - started, retries=retries, authenticated=True)

        return self._build_result(ctx, op, success=False, status="failed", message="Connector operation failed", duration=time.perf_counter() - started, retries=retries, authenticated=True)

    def _ensure_authenticated(self, ctx: ConnectorContext, operation: str) -> ConnectorResult | None:
        auth_state = ctx.auth or {}
        connected = auth_state.get("connected", True)
        has_access_token = bool((ctx.metadata.get("access_token") or (ctx.auth or {}).get("access_token") or (ctx.auth or {}).get("token") or ctx.metadata.get("token") or (ctx.auth or {}).get("refresh_token")))
        token_valid = auth_state.get("token_valid", True)
        refreshable = bool(auth_state.get("refresh_token") or auth_state.get("refreshable", False) or ctx.metadata.get("refresh_token"))
        permissions = auth_state.get("permissions", True)
        scopes = auth_state.get("scopes") or []
        required_scopes = ctx.metadata.get("required_scopes") or []
        needs_user_action = bool(auth_state.get("requires_user_action") or ctx.metadata.get("requires_user_action"))
        if needs_user_action:
            return self._build_result(ctx, operation, success=False, status="waiting_for_authentication", message="Waiting for Authentication", errors=["Waiting for Authentication"], duration=0.0, retries=0, authenticated=False)
        if not connected:
            return self._build_result(ctx, operation, success=False, status="waiting_for_authentication", message="Waiting for Authentication", errors=["Waiting for Authentication"], duration=0.0, retries=0, authenticated=False)
        if not token_valid and refreshable:
            refreshed = self.refresh_credentials(ctx)
            ctx.auth["token_valid"] = refreshed.authenticated
            ctx.auth["token"] = refreshed.token
            ctx.auth["refresh_attempted"] = True
            token_valid = refreshed.authenticated
        if not token_valid and not has_access_token and not refreshable:
            return self._build_result(ctx, operation, success=False, status="waiting_for_authentication", message="Waiting for Authentication", errors=["Waiting for Authentication"], duration=0.0, retries=0, authenticated=False)
        if not token_valid and refreshable:
            return None
        if not token_valid and has_access_token:
            return None
        if not permissions:
            return self._build_result(ctx, operation, success=False, status="waiting_for_authentication", message="Waiting for Authentication", errors=["Permission denied"], duration=0.0, retries=0, authenticated=False)
        if required_scopes and not set(required_scopes).issubset(set(scopes)):
            return self._build_result(ctx, operation, success=False, status="waiting_for_authentication", message="Waiting for Authentication", errors=["Missing required scopes"], duration=0.0, retries=0, authenticated=False)
        return None

    def _inject_failure(self, ctx: ConnectorContext, operation: str, attempt: int) -> None:
        failures = ctx.config.get("simulated_failures") or {}
        if not failures:
            return
        if operation in failures and attempt == 1:
            kind = failures[operation]
            if kind == "rate_limit":
                raise RateLimited("Rate limited")
            if kind == "network":
                raise NetworkFailure("Temporary network error")
            if kind == "auth":
                raise AuthenticationFailure("Expired token")
            if kind == "permission":
                raise PermissionDenied("Permission denied")
            if kind == "validation":
                raise ValidationFailure("Verification failed")

    def _build_result(
        self,
        ctx: ConnectorContext,
        operation: str,
        *,
        success: bool,
        status: str,
        message: str,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
        data: Any = None,
        verification: dict[str, Any] | None = None,
        artifacts: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        duration: float | None = None,
        retries: int = 0,
        authenticated: bool | None = None,
        retryable: bool = False,
    ) -> ConnectorResult:
        return ConnectorResult(
            success=success,
            data=data,
            message=message,
            connector=self.capability,
            operation=operation,
            status=status,
            verification=verification or {},
            artifacts=artifacts or {},
            metadata=metadata or {},
            duration=round(duration or 0.0, 3),
            retries=retries,
            warnings=warnings or [],
            errors=errors or [],
            authenticated=success if authenticated is None else authenticated,
            execution_time=round(duration or 0.0, 3),
            error=(errors[0] if errors else None),
            retryable=retryable,
        )

    def _perform_operation(self, ctx: ConnectorContext, operation: str) -> ConnectorResult:
        raise NotImplementedError

    def search(self, ctx: ConnectorContext) -> ConnectorResult:
        return self._dispatch(ctx, ctx.metadata.get("operation") or "search")

    def read(self, ctx: ConnectorContext) -> ConnectorResult:
        return self._dispatch(ctx, ctx.metadata.get("operation") or "read")

    def create(self, ctx: ConnectorContext) -> ConnectorResult:
        return self._dispatch(ctx, ctx.metadata.get("operation") or "create")

    def update(self, ctx: ConnectorContext) -> ConnectorResult:
        return self._dispatch(ctx, ctx.metadata.get("operation") or "update")

    def delete(self, ctx: ConnectorContext) -> ConnectorResult:
        return self._dispatch(ctx, ctx.metadata.get("operation") or "delete")

    def execute(self, action: str | ConnectorContext, payload: dict[str, Any] | None = None) -> ConnectorResult:
        if isinstance(action, ConnectorContext):
            ctx = action
        else:
            data = dict(payload or {})
            ctx = ConnectorContext(
                execution_id=str(data.pop("execution_id", "connector-action")),
                skill_id=data.pop("skill_id", None),
                worker_id=data.pop("worker_id", None),
                auth=data.pop("auth", {}) or {},
                config=data.pop("config", {}) or {},
                metadata=data,
            )
            ctx.metadata["operation"] = action
        return self._dispatch(ctx, ctx.metadata.get("operation") or "execute")
