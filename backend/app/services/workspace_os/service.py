from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas.workspace_os import (
    WorkspaceCommandRunIn,
    WorkspaceOSOut,
    WorkspaceSearchOut,
)
from app.services.workspace_os.mock_data import MOCK_WORKSPACE_OS


class WorkspaceOSService:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self.data = deepcopy(data or MOCK_WORKSPACE_OS)

    def snapshot(self) -> WorkspaceOSOut:
        return WorkspaceOSOut(**self.data)

    def search(self, query: str = "", filters: list[str] | None = None) -> WorkspaceSearchOut:
        filters = filters or []
        normalized_query = query.strip().lower()
        normalized_filters = {item.strip().lower() for item in filters if item.strip()}
        results = []
        for item in self.data["searchIndex"]:
            haystack = " ".join([item["title"], item["snippet"], item["source"], *item.get("tags", [])]).lower()
            matches_query = not normalized_query or normalized_query in haystack
            matches_filter = not normalized_filters or item["type"].lower() in normalized_filters
            if matches_query and matches_filter:
                results.append(item)
        return WorkspaceSearchOut(query=query, filters=filters, results=results[:8])

    def commands(self) -> list[dict[str, Any]]:
        return list(self.data["commands"])

    def run_command(self, body: WorkspaceCommandRunIn) -> dict[str, str | bool | None]:
        command = next((item for item in self.data["commands"] if item["id"] == body.commandId), None)
        if not command:
            return {"status": "not_found", "commandId": body.commandId, "executed": False, "message": "Command not found."}
        return {
            "status": "queued_mock",
            "commandId": body.commandId,
            "executed": False,
            "message": f"Mock command queued: {command['title']}. No production action was executed.",
            "input": body.input,
        }
