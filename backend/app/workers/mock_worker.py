import time
from typing import Any, Dict
from .base import Worker
from .context import WorkerContext
from .result import WorkerResult, VerificationResult, RollbackResult, ExecutionStatus
from .errors import RetryableWorkerError


class MockWorker(Worker):
    """A production-quality mock worker used for integration and tests.

    Behavior is controlled via `context.inputs`:
      - simulate_delay: seconds to sleep
      - fail: boolean to raise fatal error
      - fail_times: number of attempts to fail with retryable error
      - verify_pass: boolean whether verification passes
    """

    def __init__(self, **deps: Any):
        super().__init__(**deps)
        self._fail_count = 0
        # attempt is injected by WorkerManager per run attempt
        self._attempt = int(self.deps.get("attempt", 1))

    def execute(self, context: WorkerContext) -> WorkerResult:
        delay = float(context.inputs.get("simulate_delay", 0))
        if delay > 0:
            time.sleep(delay)

        if context.inputs.get("fail"):
            raise Exception("mock fatal failure")

        fail_times = int(context.inputs.get("fail_times", 0))
        # use injected attempt to decide retry behavior
        if self._attempt <= fail_times:
            raise RetryableWorkerError("transient mock failure")

        outputs = {"echo": context.inputs.get("payload", {})}
        return WorkerResult(status=ExecutionStatus.SUCCESS, outputs=outputs, message="ok")

    def verify(self, context: WorkerContext) -> VerificationResult:
        passed = bool(context.inputs.get("verify_pass", True))
        evidence = {"checked": True}
        return VerificationResult(passed=passed, evidence=evidence)

    def rollback(self, context: WorkerContext) -> RollbackResult:
        return RollbackResult(success=True, message="rolled back", actions_taken=["noop"])

    def cleanup(self, context: WorkerContext) -> None:
        return None
