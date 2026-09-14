from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time


@dataclass
class ExecutionMetrics:
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    attempts: int = 1
    extra: Dict[str, Any] = field(default_factory=dict)

    def finish(self) -> None:
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time


@dataclass
class ConnectorResult:
    success: bool
    data: Any = None
    message: Optional[str] = None
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
    connector: Optional[str] = None
    operation: Optional[str] = None
    status: str = "completed"
    verification: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    duration: Optional[float] = None
    retries: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    authenticated: bool = False
    execution_time: Optional[float] = None
    error: Optional[Dict[str, Any] | str] = None
    retryable: bool = False


ActionResult = ConnectorResult


@dataclass
class AuthenticationResult:
    authenticated: bool
    token: Optional[str] = None
    expires_at: Optional[float] = None
    message: Optional[str] = None


@dataclass
class HealthResult:
    available: bool
    latency_seconds: Optional[float] = None
    auth_ok: Optional[bool] = None
    rate_limit: Optional[Dict[str, Any]] = None
    last_success: Optional[float] = None
    failures: int = 0
    message: Optional[str] = None
    status: str = "connected"


@dataclass
class SearchResult(ConnectorResult):
    results: List[Any] = field(default_factory=list)


@dataclass
class ReadResult(ConnectorResult):
    record: Any = None


@dataclass
class WriteResult(ConnectorResult):
    id: Optional[str] = None
    record: Any = None
