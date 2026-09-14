from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class RuntimeError(Exception):
    """Base class for runtime failures."""

    def __init__(self, message: str, *, code: str | None = None, retryable: bool = False, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.retryable = retryable
        self.metadata = metadata or {}


class RecoverableRuntimeError(RuntimeError):
    pass


class FatalRuntimeError(RuntimeError):
    pass


class RetryableRuntimeError(RecoverableRuntimeError):
    pass


class WorkerFailureError(RetryableRuntimeError):
    pass


class ConnectorFailureError(RecoverableRuntimeError):
    pass


class VerificationFailureError(FatalRuntimeError):
    pass


class TimeoutError(RetryableRuntimeError):
    pass


class CancellationError(FatalRuntimeError):
    pass
