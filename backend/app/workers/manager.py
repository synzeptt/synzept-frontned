import time
from typing import Any, Dict, Optional, Type
from copy import deepcopy

from .context import WorkerContext
from .result import WorkerResult, VerificationResult, RollbackResult, ExecutionMetrics, ExecutionStatus
from .registry import default_registry
from ..events import default_event_bus
from .errors import RetryableWorkerError, FatalWorkerError


class WorkerManager:
    """Responsible for discovery, instantiation, DI and lifecycle management."""

    def __init__(self, registry=default_registry, default_retry: int = 2, dependencies: Dict[str, Any] = None, event_bus=None):
        self.registry = registry
        self.default_retry = default_retry
        self.dependencies = dependencies or {}
        self.event_bus = event_bus or default_event_bus

    def _instantiate(self, worker_cls: Type, **overrides) -> object:
        deps = dict(self.dependencies)
        deps.update(overrides)
        return worker_cls(**deps)

    def get_worker(self, capability: str):
        worker_cls = self.registry.get_worker_class(capability)
        if worker_cls is None:
            raise KeyError(f"Worker not found for capability: {capability}")
        return worker_cls

    def run(self, capability: str, context: WorkerContext, retry: Optional[int] = None) -> WorkerResult:
        retry = self.default_retry if retry is None else retry
        worker_cls = self.get_worker(capability)
        attempts = 0
        last_err: Optional[Exception] = None
        metrics = ExecutionMetrics()
        while attempts <= retry:
            attempts += 1
            metrics.attempts = attempts
            worker = self._instantiate(worker_cls, attempt=attempts)
            try:
                # emit worker started
                try:
                    self.event_bus.emit("worker.started", {"execution_id": context.execution_id, "capability": capability, "attempt": attempts})
                except Exception:
                    pass
                worker.before_execute(context)
                result = worker.execute(context)
                worker.after_execute(context, result)
                # emit worker completed
                try:
                    self.event_bus.emit("worker.completed", {"execution_id": context.execution_id, "capability": capability, "result": result})
                except Exception:
                    pass
                # verify
                worker.before_verify(context)
                verification = worker.verify(context)
                worker.after_verify(context, verification)
                metrics.finish()
                result.metrics = metrics
                if verification.passed:
                    result.status = ExecutionStatus.SUCCESS
                    return result
                else:
                    # Treat verification failure as retryable first
                    last_err = RuntimeError("verification failed: " + (verification.message or ""))
                    self.event_bus.emit("verification.failed", {"execution_id": context.execution_id, "capability": capability, "verification": verification})
                    if attempts > retry:
                        result.status = ExecutionStatus.FAILURE
                        return result
                    time.sleep(0.1)
            except RetryableWorkerError as e:
                last_err = e
                self.event_bus.emit("worker.retry", {"execution_id": context.execution_id, "capability": capability, "attempt": attempts, "error": str(e)})
                if attempts > retry:
                    metrics.finish()
                    return WorkerResult(status=ExecutionStatus.FAILURE, message=str(e), metrics=metrics)
                time.sleep(0.1)
                continue
            except FatalWorkerError as e:
                self.event_bus.emit("worker.failed", {"execution_id": context.execution_id, "capability": capability, "error": str(e)})
                metrics.finish()
                return WorkerResult(status=ExecutionStatus.FAILURE, message=str(e), metrics=metrics)
            except Exception as e:
                last_err = e
                # attempt rollback
                try:
                    rb = worker.rollback(context)
                except Exception:
                    rb = RollbackResult(success=False, message="rollback failed")
                metrics.finish()
                try:
                    self.event_bus.emit("worker.failed", {"execution_id": context.execution_id, "capability": capability, "error": str(e)})
                except Exception:
                    pass
                return WorkerResult(status=ExecutionStatus.FAILURE, message=str(e), metrics=metrics)

        # unreachable but safe
        metrics.finish()
        return WorkerResult(status=ExecutionStatus.FAILURE, message=str(last_err), metrics=metrics)
