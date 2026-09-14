from typing import Optional


class ConnectorError(Exception):
    def __init__(self, message: str = "", *, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class AuthenticationFailure(ConnectorError):
    pass


class PermissionDenied(ConnectorError):
    pass


class RateLimited(ConnectorError):
    pass


class TimeoutError(ConnectorError):
    pass


class NetworkFailure(ConnectorError):
    pass


class ProviderError(ConnectorError):
    pass


class ValidationFailure(ConnectorError):
    pass


class RetryableFailure(ConnectorError):
    pass


class FatalFailure(ConnectorError):
    pass
