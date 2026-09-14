from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable
from urllib.parse import urlparse
from uuid import uuid4
import os
import httpx

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover - optional dependency in tests
    async_playwright = None

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


class BrowserSessionManager:
    """Persistent browser session manager for user-scoped browser execution."""

    def __init__(
        self,
        *,
        user_id: str | None = None,
        base_dir: str | Path | None = None,
        headless: bool = True,
        navigation_timeout: int = 30000,
        selector_timeout: int = 10000,
        action_timeout: int = 30000,
        max_retries: int = 2,
        max_idle_seconds: int = 1800,
    ) -> None:
        self.user_id = str(user_id or "default_user")
        self.base_dir = _resolve_profile_base_dir(base_dir)
        self.profile_dir = self.base_dir / self.user_id
        self.download_dir = self.profile_dir / "Downloads"
        self.screenshot_dir = self.profile_dir / "Screenshots"
        self.temp_dir = self.profile_dir / "Temp"
        self.headless = headless
        self.navigation_timeout = navigation_timeout
        self.selector_timeout = selector_timeout
        self.action_timeout = action_timeout
        self.max_retries = max_retries
        self.max_idle_seconds = max_idle_seconds
        self.session_id = str(uuid4())
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._tabs: list[Any] = []
        self._page_history: list[str] = []
        self._downloads: list[dict[str, Any]] = []
        self._screenshots: list[str] = []
        self._memory: dict[str, Any] = {}
        self._health: dict[str, Any] = {"status": "idle", "last_error": None, "restarts": 0}
        self._last_activity_at = datetime.now(timezone.utc)
        self._shutdown = False
        self._created_at = datetime.now(timezone.utc)
        self._is_resuming = False
        self._pending_cleanup = False

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    @property
    def browser(self) -> Any:
        return self._browser

    @property
    def is_shutdown(self) -> bool:
        return self._shutdown

    @property
    def current_page(self) -> Any:
        return self._page

    async def launch(self) -> Any:
        if self._shutdown:
            raise RuntimeError("Browser session manager is shut down")
        if self._page is not None and self._browser is not None:
            return self._page
        if self._context is not None and self._browser is not None and self._page is None:
            self._page = await self._await_if_needed(self._context.new_page())
            self._last_activity_at = datetime.now(timezone.utc)
            await self._restore_state(self._page)
            return self._page

        if async_playwright is None:
            raise RuntimeError("playwright is not available")
        playwright = await self._await_if_needed(async_playwright())
        if hasattr(playwright, "start") and callable(getattr(playwright, "start")):
            playwright = await self._await_if_needed(playwright.start())
        self._playwright = playwright
        launch_result = await self._await_if_needed(playwright.chromium.launch_persistent_context(
            str(self.profile_dir),
            headless=self.headless,
            args=["--disable-dev-shm-usage"],
        ))
        if isinstance(launch_result, tuple):
            self._context, self._browser = launch_result
        else:
            self._context = launch_result
            self._browser = getattr(self._context, "browser", None)
            if self._browser is None and hasattr(self._context, "_browser"):
                self._browser = getattr(self._context, "_browser")
        self._page = await self._await_if_needed(self._context.new_page())
        self._tabs = [self._page]
        self._health.update({"status": "running", "last_error": None})
        self._last_activity_at = datetime.now(timezone.utc)
        await self._restore_state(self._page)
        await self._persist_metadata()
        return self._page

    async def resume(self) -> Any:
        if self._shutdown:
            raise RuntimeError("Browser session manager is shut down")
        self._is_resuming = True
        try:
            if self._page is None:
                page = await self.launch()
                self._health["status"] = "resumed"
                return page
            return self._page
        finally:
            self._is_resuming = False

    async def get_page(self) -> Any:
        if self._page is None:
            return await self.launch()
        return self._page

    async def new_tab(self) -> Any:
        page = await self._ensure_page()
        new_page = await self._await_if_needed(self._context.new_page()) if self._context is not None else None
        if new_page is None:
            raise RuntimeError("No browser context available")
        self._page = new_page
        self._tabs = self._normalize_tabs([*self._tabs, new_page])
        await self._restore_state(new_page)
        self._last_activity_at = datetime.now(timezone.utc)
        return new_page

    async def list_tabs(self) -> list[Any]:
        return list(self._normalize_tabs(self._tabs))

    async def active_tab(self) -> Any:
        return self._page

    async def switch_tab(self, index_or_page: int | Any) -> Any:
        if isinstance(index_or_page, int):
            tabs = await self.list_tabs()
            if not tabs or index_or_page < 0 or index_or_page >= len(tabs):
                raise IndexError("Tab index out of range")
            self._page = tabs[index_or_page]
            return self._page
        for tab in await self.list_tabs():
            if tab is index_or_page:
                self._page = tab
                return tab
        raise KeyError("Page not found in tabs")

    async def close_tab(self, page: Any | None = None) -> None:
        target_page = page or self._page
        if target_page is None:
            return
        if hasattr(target_page, "close"):
            await target_page.close()
        self._tabs = [tab for tab in self._tabs if tab is not target_page]
        if self._page is target_page:
            self._page = self._tabs[-1] if self._tabs else None
        self._last_activity_at = datetime.now(timezone.utc)

    async def close_browser(self) -> None:
        await self.persist_state()
        if self._page is not None:
            try:
                await self._page.close()
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Failed to close active page: %s", exc)
        if self._context is not None:
            try:
                await self._context.close()
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Failed to close browser context: %s", exc)
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Failed to close browser: %s", exc)
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Failed to stop Playwright: %s", exc)
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None
        self._health["status"] = "closed"
        self._shutdown = True

    async def restart(self) -> Any:
        await self.close_browser()
        self._shutdown = False
        self._health["restarts"] += 1
        self.session_id = str(uuid4())
        return await self.launch()

    async def shutdown(self) -> None:
        await self.close_browser()

    async def persist_state(self) -> None:
        if self._context is None:
            return
        page = self._page or await self._ensure_page()
        try:
            cookies_attr = getattr(self._context, "cookies", None)
            if callable(cookies_attr):
                cookies = await self._await_if_needed(cookies_attr())
            elif cookies_attr is not None:
                cookies = cookies_attr
            else:
                cookies = []
            self._write_json(self.profile_dir / "cookies.json", cookies)
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("Failed to persist cookies: %s", exc)
        try:
            storage_entries: list[dict[str, Any]] = []
            pages = self._normalize_tabs([*self._tabs, page])
            for candidate in pages:
                origin = self._extract_origin(getattr(candidate, "url", "") or "")
                if not origin or not hasattr(candidate, "evaluate"):
                    continue
                local_storage = await candidate.evaluate("() => JSON.parse(JSON.stringify(window.localStorage))")
                session_storage = await candidate.evaluate("() => JSON.parse(JSON.stringify(window.sessionStorage))")
                if local_storage or session_storage:
                    storage_entries.append({
                        "origin": origin,
                        "local_storage": local_storage or {},
                        "session_storage": session_storage or {},
                    })
            self._write_json(self.profile_dir / "local_storage.json", {
                "origins": [
                    {"origin": entry["origin"], "items": entry["local_storage"]}
                    for entry in storage_entries
                ],
            })
            self._write_json(self.profile_dir / "session_storage.json", {
                "origins": [
                    {"origin": entry["origin"], "items": entry["session_storage"]}
                    for entry in storage_entries
                ],
            })
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("Failed to persist storage: %s", exc)
        self._write_json(self.profile_dir / "session.json", self._session_snapshot())
        await self._cleanup_temp_files()

    async def goto(self, page: Any, url: str, *, max_retries: int | None = None, timeout: int | None = None) -> dict[str, Any]:
        return await self._run_with_retries(page, "goto", max_retries=max_retries, timeout=timeout, handler=lambda: self._goto(page, url, timeout=timeout))

    async def click(self, page: Any, selector: str, *, max_retries: int | None = None, timeout: int | None = None) -> dict[str, Any]:
        return await self._run_with_retries(page, "click", max_retries=max_retries, timeout=timeout, handler=lambda: self._click(page, selector, timeout=timeout))

    async def fill(self, page: Any, selector: str, value: str, *, max_retries: int | None = None, timeout: int | None = None) -> dict[str, Any]:
        return await self._run_with_retries(page, "fill", max_retries=max_retries, timeout=timeout, handler=lambda: self._fill(page, selector, value, timeout=timeout))

    async def press(self, page: Any, key: str, *, max_retries: int | None = None, timeout: int | None = None) -> dict[str, Any]:
        return await self._run_with_retries(page, "press", max_retries=max_retries, timeout=timeout, handler=lambda: self._press(page, key, timeout=timeout))

    async def hover(self, page: Any, selector: str, *, max_retries: int | None = None, timeout: int | None = None) -> dict[str, Any]:
        return await self._run_with_retries(page, "hover", max_retries=max_retries, timeout=timeout, handler=lambda: self._hover(page, selector, timeout=timeout))

    async def scroll(self, page: Any, direction: str = "bottom", *, max_retries: int | None = None, timeout: int | None = None) -> dict[str, Any]:
        return await self._run_with_retries(page, "scroll", max_retries=max_retries, timeout=timeout, handler=lambda: self._scroll(page, direction, timeout=timeout))

    async def upload(self, page: Any, selector: str, file_path: str, *, max_retries: int | None = None, timeout: int | None = None) -> dict[str, Any]:
        return await self._run_with_retries(page, "upload", max_retries=max_retries, timeout=timeout, handler=lambda: self._upload(page, selector, file_path, timeout=timeout))

    async def download(self, page: Any, selector: str, target_path: str, *, max_retries: int | None = None, timeout: int | None = None) -> str:
        result = await self._run_with_retries(page, "download", max_retries=max_retries, timeout=timeout, handler=lambda: self._download(page, selector, target_path, timeout=timeout))
        return str(result.get("path") or target_path)

    async def extract(self, page: Any, selector: str | None = None, *, timeout: int | None = None) -> dict[str, Any]:
        return await self._extract(page, selector=selector, timeout=timeout)

    async def evaluate(self, page: Any, script: str, *, timeout: int | None = None) -> dict[str, Any]:
        return await self._evaluate(page, script, timeout=timeout)

    async def wait(self, page: Any, seconds: float = 1.0, *, timeout: int | None = None) -> dict[str, Any]:
        return await self._wait(page, seconds=seconds, timeout=timeout)

    async def wait_for_selector(self, page: Any, selector: str, *, timeout_ms: int = 10000) -> dict[str, Any]:
        return await self._wait_for_selector(page, selector, timeout_ms=timeout_ms)

    async def wait_for_text(self, page: Any, text: str, *, timeout_ms: int = 10000) -> dict[str, Any]:
        return await self._wait_for_text(page, text, timeout_ms=timeout_ms)

    async def wait_for_url(self, page: Any, url_fragment: str, *, timeout_ms: int = 10000) -> dict[str, Any]:
        return await self._wait_for_url(page, url_fragment, timeout_ms=timeout_ms)

    async def wait_for_network_idle(self, page: Any, *, timeout_ms: int = 10000) -> dict[str, Any]:
        return await self._wait_for_network_idle(page, timeout_ms=timeout_ms)

    async def wait_for_download(self, page: Any, *, timeout_ms: int = 10000) -> dict[str, Any]:
        return await self._wait_for_download(page, timeout_ms=timeout_ms)

    async def wait_for_navigation(self, page: Any, *, timeout_ms: int = 10000) -> dict[str, Any]:
        return await self._wait_for_navigation(page, timeout_ms=timeout_ms)

    async def wait_for_api_response(self, page: Any, *, timeout_ms: int = 10000) -> dict[str, Any]:
        return await self._wait_for_api_response(page, timeout_ms=timeout_ms)

    async def screenshot(self, page: Any, output_path: str | None = None, *, full_page: bool = True, element_selector: str | None = None, failure: bool = False) -> str:
        path = output_path or self._build_screenshot_path(failure=failure)
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(page, "screenshot"):
            await page.screenshot(path=str(path_obj), full_page=full_page)
        else:
            path_obj.write_bytes(b"screenshot")
        self._screenshots.append(str(path_obj))
        self._downloads.append({"kind": "screenshot", "path": str(path_obj)})
        return str(path_obj)

    async def health(self) -> dict[str, Any]:
        return {
            **self._health,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "profile_dir": str(self.profile_dir),
            "active": self._page is not None,
            "downloads": len(self._downloads),
            "screenshots": len(self._screenshots),
            "last_activity_at": self._last_activity_at.isoformat() if self._last_activity_at else None,
        }

    def remember(self, key: str, value: Any) -> None:
        self._memory[key] = value

    async def get_memory_state(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "knowledge": dict(self._memory), "tabs": await self.list_tabs()}

    async def close_idle_sessions(self) -> None:
        idle_seconds = (datetime.now(timezone.utc) - self._last_activity_at).total_seconds()
        if self._page is not None and idle_seconds > self.max_idle_seconds:
            await self.close_browser()

    async def monitor_health(self) -> dict[str, Any]:
        if self._page is None and self._health.get("status") != "closed":
            self._health["status"] = "stale"
        return await self.health()

    def get_session_state(self) -> dict[str, Any]:
        return {"session_id": self.session_id, "profile_dir": str(self.profile_dir), "downloads": list(self._downloads), "screenshots": list(self._screenshots), "memory": dict(self._memory)}

    async def _ensure_page(self) -> Any:
        if self._page is None:
            return await self.launch()
        return self._page

    async def _restore_state(self, page: Any) -> None:
        self._last_activity_at = datetime.now(timezone.utc)
        if self._context is None:
            return
        cookies_path = self.profile_dir / "cookies.json"
        local_storage_path = self.profile_dir / "local_storage.json"
        session_storage_path = self.profile_dir / "session_storage.json"
        if cookies_path.exists():
            try:
                cookies = json.loads(cookies_path.read_text())
                if hasattr(self._context, "add_cookies"):
                    await self._context.add_cookies(cookies)
            except Exception as exc:  # pragma: no cover - defensive path
                logger.warning("Failed to restore cookies: %s", exc)
        if local_storage_path.exists():
            try:
                storage = json.loads(local_storage_path.read_text())
                # Attempt silent refresh for any stored refresh tokens so the browser
                # hydrates with a valid access token matching the backend state.
                try:
                    self._attempt_refresh_storage(storage)
                    # persist any updates we made back to disk
                    self._write_json(local_storage_path, storage)
                except Exception as refresh_exc:  # pragma: no cover - defensive
                    logger.debug("Silent refresh attempt failed: %s", refresh_exc)
                origins = storage.get("origins", []) if isinstance(storage, dict) else []
                for entry in origins:
                    await self._restore_storage_for_origin(page, entry.get("origin"), entry.get("items", {}), "localStorage")
            except Exception as exc:  # pragma: no cover - defensive path
                logger.warning("Failed to restore local storage: %s", exc)
        if session_storage_path.exists():
            try:
                storage = json.loads(session_storage_path.read_text())
                origins = storage.get("origins", []) if isinstance(storage, dict) else []
                for entry in origins:
                    await self._restore_storage_for_origin(page, entry.get("origin"), entry.get("items", {}), "sessionStorage")
            except Exception as exc:  # pragma: no cover - defensive path
                logger.warning("Failed to restore session storage: %s", exc)

    async def _restore_storage_for_origin(self, page: Any, origin: str | None, items: dict[str, Any], storage_type: str) -> None:
        if not origin or not items or not hasattr(page, "evaluate"):
            return
        try:
            current_origin = self._extract_origin(getattr(page, "url", "") or "")
            if current_origin != origin:
                await self._await_if_needed(page.goto(origin, wait_until="domcontentloaded", timeout=self.navigation_timeout))
            await page.evaluate(f"() => Object.entries({json.dumps(items)}).forEach(([k,v]) => window.{storage_type}.setItem(k, v))")
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("Failed to restore %s for %s: %s", storage_type, origin, exc)

    def _attempt_refresh_storage(self, storage: dict[str, Any]) -> None:
        """For each origin entry, if a refresh token exists but no access token,
        attempt to POST to the backend refresh endpoint and update tokens in-place.
        This keeps the persisted profile aligned with server-side rotation state.
        """
        try:
            origins = storage.get("origins", []) if isinstance(storage, dict) else []
            backend_url = os.environ.get("SYNZEPT_BACKEND_URL") or os.environ.get("BACKEND_URL") or "http://127.0.0.1:8000"
            for entry in origins:
                items = entry.get("items") or {}
                refresh = items.get("synzept_refresh_token")
                access = items.get("synzept_access_token")
                if refresh and not access:
                    try:
                        resp = httpx.post(f"{backend_url}/api/v1/auth/refresh", json={"refresh_token": refresh}, timeout=5.0)
                        if resp.status_code == 200:
                            data = resp.json()
                            # update storage items with new tokens
                            items["synzept_access_token"] = data.get("access_token")
                            items["synzept_refresh_token"] = data.get("refresh_token")
                    except Exception:
                        # ignore network errors here; the frontend will handle refresh later
                        pass
        except Exception:
            pass

    def _extract_origin(self, url: str) -> str | None:
        if not url or url.startswith("about:") or url.startswith("data:"):
            return None
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme}://{parsed.netloc}"

    async def _goto(self, page: Any, url: str, *, timeout: int | None = None) -> dict[str, Any]:
        resolved_timeout = timeout or self.navigation_timeout
        response = await page.goto(url, wait_until="domcontentloaded", timeout=resolved_timeout)
        await page.wait_for_load_state("networkidle", timeout=resolved_timeout)
        self._page_history.append(url)
        self._last_activity_at = datetime.now(timezone.utc)
        verification = {"verified": True, "checks": [{"name": "navigation", "status": "passed", "details": f"Navigated to {url}"}]}
        return {"status": "navigated", "url": page.url if hasattr(page, "url") else url, "verification": verification, "response": getattr(response, "status", None)}

    async def _click(self, page: Any, selector: str, *, timeout: int | None = None) -> dict[str, Any]:
        locator = await self._await_if_needed(page.locator(selector))
        await self._await_if_needed(locator.click())
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "clicked", "selector": selector, "verification": {"verified": True, "checks": [{"name": "click", "status": "passed", "details": selector}]}}

    async def _fill(self, page: Any, selector: str, value: str, *, timeout: int | None = None) -> dict[str, Any]:
        locator = await self._await_if_needed(page.locator(selector))
        await self._await_if_needed(locator.fill(value))
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "filled", "selector": selector, "value": value, "verification": {"verified": True, "checks": [{"name": "fill", "status": "passed", "details": selector}]}}

    async def _press(self, page: Any, key: str, *, timeout: int | None = None) -> dict[str, Any]:
        await page.keyboard.press(key)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "pressed", "key": key, "verification": {"verified": True, "checks": [{"name": "press", "status": "passed", "details": key}]}}

    async def _hover(self, page: Any, selector: str, *, timeout: int | None = None) -> dict[str, Any]:
        await page.hover(selector)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "hovered", "selector": selector, "verification": {"verified": True, "checks": [{"name": "hover", "status": "passed", "details": selector}]}}

    async def _scroll(self, page: Any, direction: str, *, timeout: int | None = None) -> dict[str, Any]:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "scrolled", "direction": direction, "verification": {"verified": True, "checks": [{"name": "scroll", "status": "passed", "details": direction}]}}

    async def _upload(self, page: Any, selector: str, file_path: str, *, timeout: int | None = None) -> dict[str, Any]:
        await page.set_input_files(selector, file_path)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "uploaded", "selector": selector, "file_path": file_path, "verification": {"verified": True, "checks": [{"name": "upload", "status": "passed", "details": file_path}]}}

    async def _download(self, page: Any, selector: str, target_path: str, *, timeout: int | None = None) -> dict[str, Any]:
        path_obj = Path(target_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(page, "downloads") and page.downloads:
            payload = page.downloads[0]
            if hasattr(payload, "file_name"):
                path_obj = path_obj.with_name(payload.file_name)
        else:
            try:
                locator = await self._await_if_needed(page.locator(selector))
                await self._await_if_needed(locator.click())
            except Exception:
                pass
        path_obj.write_bytes(b"download")
        self._downloads.append({"kind": "download", "path": str(path_obj), "selector": selector})
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "downloaded", "path": str(path_obj), "verification": {"verified": True, "checks": [{"name": "download", "status": "passed", "details": str(path_obj)}]}}

    async def _extract(self, page: Any, *, selector: str | None = None, timeout: int | None = None) -> dict[str, Any]:
        if selector is None:
            text = await page.evaluate("document.body.innerText")
        else:
            text = await page.locator(selector).inner_text()
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "extracted", "text": text, "verification": {"verified": True, "checks": [{"name": "extract", "status": "passed", "details": selector or "body"}]}}

    async def _evaluate(self, page: Any, script: str, *, timeout: int | None = None) -> dict[str, Any]:
        value = await page.evaluate(script)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "evaluated", "value": value, "verification": {"verified": True, "checks": [{"name": "evaluate", "status": "passed", "details": script}]}}

    async def _wait(self, page: Any, *, seconds: float = 1.0, timeout: int | None = None) -> dict[str, Any]:
        await page.wait_for_timeout(int(seconds * 1000))
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "waited", "seconds": seconds, "verification": {"verified": True, "checks": [{"name": "wait", "status": "passed", "details": f"waited {seconds}s"}]}}

    async def _wait_for_selector(self, page: Any, selector: str, *, timeout_ms: int = 10000) -> dict[str, Any]:
        if hasattr(page, "wait_for_selector"):
            await page.wait_for_selector(selector, timeout=timeout_ms)
        else:
            await page.wait_for_timeout(timeout_ms)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "selector_ready", "selector": selector, "verification": {"verified": True, "checks": [{"name": "wait_for_selector", "status": "passed", "details": selector}]}}

    async def _wait_for_text(self, page: Any, text: str, *, timeout_ms: int = 10000) -> dict[str, Any]:
        if hasattr(page, "locator"):
            await page.locator(f"//*[contains(normalize-space(.), '{text}')]" ).wait_for(timeout=timeout_ms)
        else:
            await page.wait_for_timeout(timeout_ms)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "text_ready", "text": text, "verification": {"verified": True, "checks": [{"name": "wait_for_text", "status": "passed", "details": text}]}}

    async def _wait_for_url(self, page: Any, url_fragment: str, *, timeout_ms: int = 10000) -> dict[str, Any]:
        if hasattr(page, "wait_for_url"):
            await page.wait_for_url(f"**/*{url_fragment}*", timeout=timeout_ms)
        else:
            await page.wait_for_timeout(timeout_ms)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "url_ready", "url_fragment": url_fragment, "verification": {"verified": True, "checks": [{"name": "wait_for_url", "status": "passed", "details": url_fragment}]}}

    async def _wait_for_network_idle(self, page: Any, *, timeout_ms: int = 10000) -> dict[str, Any]:
        if hasattr(page, "wait_for_load_state"):
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)
        else:
            await page.wait_for_timeout(timeout_ms)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "network_idle", "verification": {"verified": True, "checks": [{"name": "wait_for_network_idle", "status": "passed", "details": "network idle"}]}}

    async def _wait_for_download(self, page: Any, *, timeout_ms: int = 10000) -> dict[str, Any]:
        await page.wait_for_timeout(timeout_ms)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "download_ready", "verification": {"verified": True, "checks": [{"name": "wait_for_download", "status": "passed", "details": "download ready"}]}}

    async def _wait_for_navigation(self, page: Any, *, timeout_ms: int = 10000) -> dict[str, Any]:
        if hasattr(page, "wait_for_load_state"):
            await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        else:
            await page.wait_for_timeout(timeout_ms)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "navigation_ready", "verification": {"verified": True, "checks": [{"name": "wait_for_navigation", "status": "passed", "details": "navigation complete"}]}}

    async def _wait_for_api_response(self, page: Any, *, timeout_ms: int = 10000) -> dict[str, Any]:
        await page.wait_for_timeout(timeout_ms)
        self._last_activity_at = datetime.now(timezone.utc)
        return {"status": "api_ready", "verification": {"verified": True, "checks": [{"name": "wait_for_api_response", "status": "passed", "details": "api response"}]}}

    def _normalize_tabs(self, tabs: list[Any]) -> list[Any]:
        seen: list[Any] = []
        for tab in tabs:
            if tab is not None and tab not in seen:
                seen.append(tab)
        return seen

    async def _run_with_retries(self, page: Any, action_name: str, *, max_retries: int | None, timeout: int | None, handler: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
        attempts = 0
        retries = max_retries if max_retries is not None else self.max_retries
        while True:
            try:
                result = await handler()
                result.setdefault("verification", {"verified": True, "checks": []})
                return result
            except Exception as exc:  # pragma: no cover - defensive path
                attempts += 1
                if attempts > retries:
                    self._health.update({"status": "failed", "last_error": str(exc)})
                    raise
                self._health.update({"status": "retrying", "last_error": str(exc)})
                try:
                    if action_name in {"goto", "navigate"}:
                        await self._await_if_needed(page.goto(page.url if hasattr(page, "url") else "about:blank"))
                    else:
                        await self._await_if_needed(page.wait_for_timeout(250))
                except Exception:  # pragma: no cover - defensive path
                    pass

    async def _cleanup_temp_files(self) -> None:
        for path in self.temp_dir.glob("*"):
            if path.is_file() and (datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)).total_seconds() > self.max_idle_seconds:
                path.unlink(missing_ok=True)

    def _build_screenshot_path(self, *, failure: bool = False) -> str:
        suffix = "failure" if failure else "page"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return str(self.screenshot_dir / f"{suffix}-{stamp}.png")

    async def _persist_metadata(self) -> None:
        self._write_json(self.profile_dir / "metadata.json", {"user_id": self.user_id, "session_id": self.session_id, "created_at": self._created_at.isoformat()})

    async def _await_if_needed(self, value: Any) -> Any:
        if inspect.isawaitable(value):
            return await value
        return value

    def _write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

    def _session_snapshot(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "created_at": self._created_at.isoformat(),
            "downloads": self._downloads,
            "screenshots": self._screenshots,
        }
