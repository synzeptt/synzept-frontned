from __future__ import annotations

from .types import ExecutionState

TRANSITION_TABLE = {
    ExecutionState.CREATED: {ExecutionState.PLANNING},
    ExecutionState.PLANNING: {ExecutionState.EXECUTING, ExecutionState.WAITING_FOR_INFORMATION, ExecutionState.FAILED, ExecutionState.CANCELLED},
    ExecutionState.EXECUTING: {ExecutionState.WAITING_FOR_INFORMATION, ExecutionState.WAITING_FOR_APPROVAL, ExecutionState.RETRYING, ExecutionState.VERIFYING, ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED},
    ExecutionState.WAITING_FOR_INFORMATION: {ExecutionState.EXECUTING, ExecutionState.CANCELLED},
    ExecutionState.WAITING_FOR_APPROVAL: {ExecutionState.EXECUTING, ExecutionState.CANCELLED},
    ExecutionState.RETRYING: {ExecutionState.EXECUTING, ExecutionState.VERIFYING, ExecutionState.FAILED, ExecutionState.CANCELLED},
    ExecutionState.VERIFYING: {ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED},
    ExecutionState.COMPLETED: set(),
    ExecutionState.FAILED: set(),
    ExecutionState.CANCELLED: set(),
}

__all__ = ["TRANSITION_TABLE"]
