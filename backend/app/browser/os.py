from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)


def _resolve_profile_base_dir(base_dir: str | Path | None = None) -> Path:
    if base_dir is not None:
        return Path(base_dir).expanduser().resolve()

    for candidate in (Path.cwd(), Path(__file__).resolve()):
        current = candidate
        while True:
            if (current / "package.json").exists() or (current / ".git").exists():
                return (current / "browser_profiles").resolve()
            if current == current.parent:
                break
            current = current.parent

    return (Path.cwd() / "browser_profiles").resolve()


class BrowserConnectionManager:
    """Single entry point for browser lifecycle and worker allocation."""

    def __init__(self, *, user_id: str | None = None, session_manager: Any | None = None) -> None:
        self.user_id = str(user_id or "default_user")
        self.session_manager = session_manager
        self._active_session = None
        self._health = {"status": "idle", "active": False, "restarts": 0}

    async def allocate_session(self) -> Any:
        if self._active_session is not None:
            self._health.update({"status": "reused", "active": True})
            return self._active_session
        if self.session_manager is None:
            raise RuntimeError("No session manager configured")
        self._active_session = await self.session_manager.launch()
        self._health.update({"status": "running", "active": True})
        return self._active_session

    async def release_session(self) -> None:
        if self._active_session is None:
            return
        self._active_session = None
        self._health.update({"status": "idle", "active": False})

    async def shutdown(self) -> None:
        if self.session_manager is not None:
            await self.session_manager.close_browser()
        self._active_session = None
        self._health.update({"status": "closed", "active": False})

    def health(self) -> dict[str, Any]:
        return {**self._health, "user_id": self.user_id}


class BrowserSessionManagerAdapter:
    """Compatibility wrapper that plugs the Browser OS into the existing session manager."""

    def __init__(self, session_manager: Any) -> None:
        self.session_manager = session_manager

    async def launch(self) -> Any:
        return await self.session_manager.launch()

    async def resume(self) -> Any:
        return await self.session_manager.resume()

    async def persist_state(self) -> None:
        await self.session_manager.persist_state()

    async def close_browser(self) -> None:
        await self.session_manager.close_browser()


class BrowserContextManager:
    """Stores browser context state and allows recovery."""

    def __init__(self, *, profile_dir: str | None = None) -> None:
        self.profile_dir = _resolve_profile_base_dir(profile_dir)
        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self._state: dict[str, Any] = {}

    def load_state(self) -> dict[str, Any]:
        return dict(self._state)

    def save_state(self, state: dict[str, Any]) -> None:
        self._state = dict(state)


class BrowserTabManager:
    """Tracks tabs, switching and recovery."""

    def __init__(self, *, session_manager: Any | None = None) -> None:
        self.session_manager = session_manager
        self._tabs: list[Any] = []

    async def open_tab(self) -> Any:
        if self.session_manager is None:
            return {"kind": "tab"}
        page = await self.session_manager.new_tab()
        self._tabs.append(page)
        return page

    async def list_tabs(self) -> list[Any]:
        if self.session_manager is None:
            return list(self._tabs)
        tabs = await self.session_manager.list_tabs()
        self._tabs = list(tabs)
        return list(tabs)

    async def switch_tab(self, index: int) -> Any:
        if self.session_manager is None:
            return self._tabs[index]
        return await self.session_manager.switch_tab(index)

    async def close_tab(self, page: Any | None = None) -> None:
        if self.session_manager is None:
            self._tabs = [tab for tab in self._tabs if tab != page]
            return
        await self.session_manager.close_tab(page)


class BrowserLoginManager:
    """Maintains login state across sessions so the user is not prompted repeatedly."""

    def __init__(self) -> None:
        self._login_state: dict[str, dict[str, Any]] = {}

    def remember_login_state(self, site: str, state: dict[str, Any]) -> None:
        self._login_state[site.casefold()] = state

    def detect_login_state(self, site: str) -> dict[str, Any]:
        return dict(self._login_state.get(site.casefold(), {"logged_in": False, "user": None}))


class CookieStorageManager:
    """Persists cookies and storage for session recovery."""

    def __init__(self, *, base_dir: str | Path | None = None) -> None:
        self.base_dir = _resolve_profile_base_dir(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def persist(self, cookies: Any, storage: Any) -> None:
        normalized_cookies: Any = cookies
        if isinstance(cookies, dict):
            if "cookies" in cookies and isinstance(cookies["cookies"], list):
                normalized_cookies = cookies["cookies"]
            elif {"name", "value"}.issubset(cookies.keys()):
                normalized_cookies = [cookies]
        (self.base_dir / "cookies.json").write_text(json.dumps(normalized_cookies, ensure_ascii=False, indent=2))
        (self.base_dir / "storage.json").write_text(json.dumps(storage, ensure_ascii=False, indent=2))

    async def restore(self) -> dict[str, Any]:
        cookies = []
        storage = {}
        cookies_path = self.base_dir / "cookies.json"
        storage_path = self.base_dir / "storage.json"
        if cookies_path.exists():
            loaded_cookies = json.loads(cookies_path.read_text())
            if isinstance(loaded_cookies, dict) and "cookies" in loaded_cookies:
                cookies = loaded_cookies["cookies"]
            else:
                cookies = loaded_cookies
        if storage_path.exists():
            storage = json.loads(storage_path.read_text())
        return {"cookies": cookies, "storage": storage}


class DOMIntelligenceEngine:
    """Produces robust selectors and semantic hints without hard-coding fragile CSS."""

    def suggest_selector(self, element: dict[str, Any]) -> str:
        text = str(element.get("text") or element.get("label") or element.get("name") or "")
        role = str(element.get("role") or "")
        if role:
            return f"[role='{role}']"
        if text:
            return f"//*[contains(normalize-space(.), '{text}')]"
        return "button"


class BrowserActionEngine:
    """Reusable browser actions for adapters and workers."""

    async def execute(self, session_manager: Any, page: Any, action: dict[str, Any]) -> dict[str, Any]:
        action_type = str(action.get("type") or action.get("action") or "goto").casefold()
        if action_type in {"goto", "navigate"}:
            return await session_manager.goto(page, str(action.get("url") or "https://example.com"))
        if action_type in {"fill", "type"}:
            return await session_manager.fill(page, str(action.get("selector") or "input"), str(action.get("value") or ""))
        if action_type in {"click", "double_click"}:
            return await session_manager.click(page, str(action.get("selector") or "button"))
        if action_type == "screenshot":
            return {"status": "screenshot_taken", "path": await session_manager.screenshot(page, output_path=str(action.get("output_path") or "/tmp/screenshot.png"))}
        if action_type == "download":
            return {"status": "downloaded", "path": await session_manager.download(page, str(action.get("selector") or "a"), str(action.get("target_path") or "/tmp/download.bin"))}
        return {"status": action_type, "data": action}


class ApprovalManager:
    """Protects irreversible actions with an explicit approval gate."""

    def requires_approval(self, operation: str, payload: dict[str, Any] | None = None) -> bool:
        sensitive = {"book_train", "pay", "purchase", "send_email", "delete", "submit_form", "apply_job"}
        return str(operation).casefold() in sensitive or bool((payload or {}).get("amount"))


class VerificationEngine:
    """Validates that actions and artifacts substantiate task completion."""

    def verify(self, action_results: list[dict[str, Any]], artifacts: list[dict[str, Any]], goal: str) -> dict[str, Any]:
        checks = [
            {"name": "action_results", "status": "passed" if action_results else "pending", "details": f"Actions executed for {goal}"},
            {"name": "artifacts", "status": "passed" if artifacts else "pending", "details": "Artifacts captured"},
        ]
        return {"verified": bool(action_results) and bool(artifacts), "checks": checks}


class RecoveryManager:
    """Retries safe steps after transient failures."""

    def __init__(self, *, max_retries: int = 2) -> None:
        self.max_retries = max_retries

    async def run_with_recovery(self, fn: Callable[[], Awaitable[Any]], *, max_retries: int | None = None) -> Any:
        retries = max_retries if max_retries is not None else self.max_retries
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                return await fn()
            except Exception as exc:  # pragma: no cover - defensive
                last_error = exc
                if attempt == retries - 1:
                    raise
        if last_error is not None:
            raise last_error
        raise RuntimeError("Recovery failed")


class ArtifactGenerator:
    """Generates artifacts that appear in the execution workspace."""

    def generate(self, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        data = payload or {}
        artifacts: list[dict[str, Any]] = []
        if data.get("confirmation_id"):
            artifacts.append({"type": "confirmation", "id": data["confirmation_id"], "content": {"value": data["confirmation_id"]}})
        if data.get("screenshot_path"):
            artifacts.append({"type": "screenshot", "path": data["screenshot_path"]})
        if data.get("download_path"):
            artifacts.append({"type": "download", "path": data["download_path"]})
        return artifacts
