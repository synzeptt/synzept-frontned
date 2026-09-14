from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import time


class SkillExecutionStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


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
class PlanningResult:
    planned_steps: List[Dict[str, Any]] = field(default_factory=list)
    estimated_cost: Optional[float] = None
    estimated_duration: Optional[float] = None


@dataclass
class DeliverableReference:
    id: str
    type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationResult:
    passed: bool
    evidence: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None


@dataclass
class SkillResult:
    status: SkillExecutionStatus
    deliverables: List[DeliverableReference] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    metrics: ExecutionMetrics = field(default_factory=ExecutionMetrics)
