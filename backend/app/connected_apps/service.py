from __future__ import annotations

from copy import deepcopy
from typing import Any


class UnifiedConnectedAppsService:
    def __init__(self, storage: dict[str, Any] | None = None) -> None:
        self.storage = storage if storage is not None else {}

    def connect_account(self, provider: str, credentials: dict[str, Any]) -> dict[str, Any]:
        self.storage[provider] = {
            "provider": provider,
            "connected": True,
            "access_token": credentials.get("access_token", ""),
            "refresh_token": credentials.get("refresh_token", ""),
            "expires_at": credentials.get("expires_at"),
            "scopes": credentials.get("scopes", []),
        }
        return self.get_connection(provider)

    def get_connection(self, provider: str) -> dict[str, Any]:
        connection = self.storage.get(provider)
        if not connection:
            return {"provider": provider, "connected": False}
        return deepcopy(connection)

    def disconnect_account(self, provider: str) -> dict[str, Any]:
        connection = self.get_connection(provider)
        connection["connected"] = False
        self.storage[provider] = connection
        return self.get_connection(provider)

    def refresh_connection(self, provider: str, new_credentials: dict[str, Any]) -> dict[str, Any]:
        connection = self.get_connection(provider)
        if not connection["connected"]:
            return self.connect_account(provider, new_credentials)
        connection.update({
            "access_token": new_credentials.get("access_token", connection.get("access_token", "")),
            "refresh_token": new_credentials.get("refresh_token", connection.get("refresh_token", "")),
            "expires_at": new_credentials.get("expires_at", connection.get("expires_at")),
        })
        self.storage[provider] = connection
        return self.get_connection(provider)

    def list_connections(self) -> list[dict[str, Any]]:
        return [self.get_connection(provider) for provider in sorted(self.storage)]

    def get_gmail_service(self) -> dict[str, Any]:
        return {"provider": "google", "service": "gmail", "connected": self.get_connection("google").get("connected", False)}

    def get_calendar_service(self) -> dict[str, Any]:
        return {"provider": "google", "service": "calendar", "connected": self.get_connection("google").get("connected", False)}

    def get_drive_service(self) -> dict[str, Any]:
        return {"provider": "google", "service": "drive", "connected": self.get_connection("google").get("connected", False)}
