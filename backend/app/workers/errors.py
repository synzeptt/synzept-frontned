from typing import Optional


class WorkerError(Exception):
    def __init__(self, message: str = "", *, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class RetryableWorkerError(WorkerError):
    pass


class FatalWorkerError(WorkerError):
    pass


class ValidationError(WorkerError):
    pass


class TimeoutWorkerError(WorkerError):
    pass


class VerificationFailure(WorkerError):
    pass

