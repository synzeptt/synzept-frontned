from abc import ABC, abstractmethod
from typing import Any

from .context import WorkerContext
from .result import WorkerResult, VerificationResult, RollbackResult


class Worker(ABC):
    """Base Worker contract.

    Concrete workers must implement execute/verify/rollback/cleanup and may
    override hook methods.
    """

    def __init__(self, **dependencies: Any):
        self.deps = dependencies

    @abstractmethod
    def execute(self, context: WorkerContext) -> WorkerResult:
        raise NotImplementedError()

    @abstractmethod
    def verify(self, context: WorkerContext) -> VerificationResult:
        raise NotImplementedError()

    @abstractmethod
    def rollback(self, context: WorkerContext) -> RollbackResult:
        raise NotImplementedError()

    @abstractmethod
    def cleanup(self, context: WorkerContext) -> None:
        raise NotImplementedError()

    # Optional lifecycle hooks
    def before_execute(self, context: WorkerContext) -> None:
        return None

    def after_execute(self, context: WorkerContext, result: WorkerResult) -> None:
        return None

    def before_verify(self, context: WorkerContext) -> None:
        return None

    def after_verify(self, context: WorkerContext, verification: VerificationResult) -> None:
        return None

