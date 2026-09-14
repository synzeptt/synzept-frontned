from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


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
class WorkerResult:
    status: ExecutionStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)


@dataclass
class VerificationResult:
    passed: bool
    evidence: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None


@dataclass
class RollbackResult:
    success: bool
    message: Optional[str] = None
    actions_taken: List[str] = field(default_factory=list)

