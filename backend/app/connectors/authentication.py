from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from .result import AuthenticationResult


class AuthProvider(ABC):
    @abstractmethod
    def authenticate(self, config: Dict[str, Any]) -> AuthenticationResult:
        raise NotImplementedError()

    @abstractmethod
    def refresh(self, token: str) -> AuthenticationResult:
        raise NotImplementedError()


class APIKeyAuth(AuthProvider):
    def authenticate(self, config: Dict[str, Any]) -> AuthenticationResult:
        key = config.get("api_key")
        if key:
            return AuthenticationResult(authenticated=True, token=key)
        return AuthenticationResult(authenticated=False, message="missing api_key")

    def refresh(self, token: str) -> AuthenticationResult:
        # API keys don't refresh
        return AuthenticationResult(authenticated=True, token=token)
