from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import ApprovalCheckpoint, Execution, ExecutionState, ExecutionStep, RetryPolicy, VerificationResult


class FileExecutionStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, execution: Execution) -> None:
        payload = self._to_payload(execution)
        path = self._path(execution.id)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def load(self, execution_id: str) -> Execution | None:
        path = self._path(execution_id)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return self._from_payload(payload)

    def delete(self, execution_id: str) -> None:
        path = self._path(execution_id)
        if path.exists():
            path.unlink()

    def _path(self, execution_id: str) -> Path:
        return self.root / f"{execution_id}.json"

    def _to_payload(self, execution: Execution) -> dict[str, Any]:
        return {
            "id": execution.id,
            "goal": execution.goal,
            "steps": [self._step_to_payload(step) for step in execution.steps],
            "state": execution.state.value,
            "current_step_index": execution.current_step_index,
            "result": execution.result,
            "error": execution.error,
            "verification": self._verification_to_payload(execution.verification),
            "approval": self._approval_to_payload(execution.approval),
            "metadata": execution.metadata,
        }

    def _from_payload(self, payload: dict[str, Any]) -> Execution:
        return Execution(
            id=payload["id"],
            goal=payload["goal"],
            steps=[self._step_from_payload(step) for step in payload.get("steps", [])],
            state=ExecutionState(payload.get("state", ExecutionState.CREATED.value)),
            current_step_index=int(payload.get("current_step_index", 0)),
            result=payload.get("result"),
            error=payload.get("error"),
            verification=self._verification_from_payload(payload.get("verification")),
            approval=self._approval_from_payload(payload.get("approval")),
            metadata=payload.get("metadata", {}),
        )

    def _step_to_payload(self, step: ExecutionStep) -> dict[str, Any]:
        return {
            "id": step.id,
            "runner": step.runner,
            "action": step.action,
            "metadata": step.metadata,
            "status": step.status,
            "output": step.output,
            "error": step.error,
            "attempts": step.attempts,
        }

    def _step_from_payload(self, payload: dict[str, Any]) -> ExecutionStep:
        return ExecutionStep(
            id=payload["id"],
            runner=payload["runner"],
            action=payload["action"],
            metadata=payload.get("metadata", {}),
            status=payload.get("status", "pending"),
            output=payload.get("output"),
            error=payload.get("error"),
            attempts=int(payload.get("attempts", 0)),
        )

    def _verification_to_payload(self, verification: VerificationResult | None) -> dict[str, Any] | None:
        if verification is None:
            return None
        return {"passed": verification.passed, "details": verification.details, "evidence": verification.evidence}

    def _verification_from_payload(self, payload: dict[str, Any] | None) -> VerificationResult | None:
        if not payload:
            return None
        return VerificationResult(passed=bool(payload.get("passed", False)), details=payload.get("details"), evidence=payload.get("evidence", {}))

    def _approval_to_payload(self, approval: ApprovalCheckpoint | None) -> dict[str, Any] | None:
        if approval is None:
            return None
        return {"required": approval.required, "granted": approval.granted, "reason": approval.reason}

    def _approval_from_payload(self, payload: dict[str, Any] | None) -> ApprovalCheckpoint | None:
        if not payload:
            return None
        return ApprovalCheckpoint(required=bool(payload.get("required", False)), granted=bool(payload.get("granted", False)), reason=payload.get("reason"))
