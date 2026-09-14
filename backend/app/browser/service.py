from __future__ import annotations

import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import urlopen

try:
    from playwright.async_api import Browser, Page, async_playwright
except ImportError:  # pragma: no cover - optional dependency fallback
    Browser = Any  # type: ignore[assignment]
    Page = Any  # type: ignore[assignment]
    async_playwright = None

logger = logging.getLogger(__name__)


class BrowserService:
    def __init__(self, headless: bool = True) -> None:
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._active_page = None
        self._session_state: dict[str, Any] = {
            "tabs": [],
            "history": [],
            "downloads": [],
            "screenshots": [],
            "cookies": [],
            "local_storage": {},
            "session_storage": {},
            "current_url": None,
            "current_title": None,
        }

    async def launch_browser(self) -> Browser:
        if async_playwright is None:
            raise RuntimeError("playwright is not installed")
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=self.headless)
        self._playwright = playwright
        self._browser = browser
        self._session_state["browser_started_at"] = datetime.now(timezone.utc).isoformat()
        return browser

    async def close_browser(self, browser: Browser | None = None) -> None:
        browser_to_close = browser or getattr(self, "_browser", None)
        if browser_to_close is None:
            return
        try:
            await browser_to_close.close()
        except Exception as exc:
            logger.warning("Failed to close browser: %s", exc)
        playwright = getattr(self, "_playwright", None)
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception as exc:
                logger.warning("Failed to stop playwright: %s", exc)
        self._browser = None
        self._active_page = None
        self._session_state["tabs"] = []
        self._session_state["history"] = []

    async def open_page(self, browser: Browser | None = None) -> Page:
        target_browser = browser or self._browser
        page = await target_browser.new_page()
        self._active_page = page
        self._session_state["tabs"].append({"id": id(page), "url": None, "title": None})
        return page

    async def navigate_to_url(self, page: Page, url: str, *, wait_for_load: bool = True) -> dict[str, Any]:
        if not self._looks_like_url(url):
            raise ValueError(f"Invalid URL: {url}")
        normalized_url = self._normalize_url(url)
        try:
            response = await page.goto(normalized_url, wait_until="domcontentloaded" if wait_for_load else "commit")
            if wait_for_load:
                await page.wait_for_load_state("networkidle", timeout=10000)
            status = getattr(response, "status", None) if response is not None else None
            canonical_url = self._canonicalize_url(normalized_url)
            self._record_navigation(canonical_url, page)
            return {"url": canonical_url, "status": status}
        except Exception:
            canonical_url = self._canonicalize_url(normalized_url)
            self._record_navigation(canonical_url, page)
            return {"url": canonical_url, "status": None, "error": "navigation_failed"}

    async def safe_navigate_to_url(self, page: Page, url: str, *, wait_for_load: bool = True) -> dict[str, Any]:
        try:
            return await self.navigate_to_url(page, url, wait_for_load=wait_for_load)
        except Exception as exc:
            logger.warning("Safe navigation failed for %s: %s", url, exc)
            return {"url": self._canonicalize_url(str(url)), "status": None, "error": str(exc)}

    async def search(self, page: Page, query: str) -> dict[str, Any]:
        try:
            await page.goto("https://www.google.com", wait_until="domcontentloaded")
            await page.fill('textarea[name="q"]', query)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle", timeout=10000)
            return {"query": query, "url": page.url}
        except Exception:
            return {"query": query, "url": page.url, "error": "search_failed"}

    async def click_element(self, page: Page, selector: str) -> None:
        await self._click(page, selector)

    async def click_by_text(self, page: Page, text: str) -> None:
        escaped_text = re.escape(text)
        try:
            await page.get_by_text(text, exact=False).click()
        except Exception:
            await page.locator(f"//*[contains(normalize-space(.), '{escaped_text}')]").click()

    async def fill_input(self, page: Page, selector: str, value: str) -> None:
        await page.locator(selector).fill(value)

    async def type_text(self, page: Page, selector: str, value: str) -> None:
        await self.fill_input(page, selector, value)

    async def clear_input(self, page: Page, selector: str) -> None:
        await page.locator(selector).clear()

    async def press_key(self, page: Page, key: str) -> None:
        await page.keyboard.press(key)

    async def select_option(self, page: Page, selector: str, value: str) -> None:
        await page.select_option(selector, value)

    async def scroll(self, page: Page, direction: str = "bottom") -> None:
        script = "window.scrollTo(0, document.body.scrollHeight)" if direction == "bottom" else "window.scrollTo(0, 0)"
        await page.evaluate(script)

    async def wait(self, page: Page, seconds: float = 1.0) -> None:
        await page.wait_for_timeout(int(seconds * 1000))

    async def hover(self, page: Page, selector: str) -> None:
        await page.hover(selector)

    async def drag_and_drop(self, page: Page, source_selector: str, target_selector: str) -> None:
        await page.locator(source_selector).drag_to(page.locator(target_selector))

    async def upload_file(self, page: Page, selector: str, file_path: str) -> None:
        await page.set_input_files(selector, file_path)

    async def wait_for_selector(self, page: Page, selector: str, *, timeout_ms: int = 10000) -> None:
        await page.wait_for_selector(selector, timeout=timeout_ms)

    async def evaluate_script(self, page: Page, script: str) -> Any:
        return await page.evaluate(script)

    async def analyze_page(self, page: Page, *, goal: str | None = None, include_screenshot: bool = False, screenshot_path: str | None = None) -> dict[str, Any]:
        snapshot = await self.observe_page(page, goal=goal, include_screenshot=include_screenshot, screenshot_path=screenshot_path)
        return {
            "goal": goal or "",
            "url": snapshot.get("url"),
            "title": snapshot.get("title"),
            "navigation": snapshot.get("navigation_state", {}),
            "buttons": snapshot.get("buttons", []),
            "forms": snapshot.get("forms", []),
            "inputs": snapshot.get("inputs", []),
            "links": snapshot.get("links", []),
            "tables": snapshot.get("tables", []),
            "dialogs": snapshot.get("dialogs", []),
            "visible_text": snapshot.get("visible_text"),
            "metadata": snapshot.get("metadata", {}),
            "structure": snapshot.get("structure", {}),
        }

    async def inspect_form(self, page: Page, *, goal: str | None = None) -> dict[str, Any]:
        analysis = await self.analyze_page(page, goal=goal)
        return {
            "fields": analysis.get("inputs", []),
            "buttons": analysis.get("buttons", []),
            "forms": analysis.get("forms", []),
            "labels": analysis.get("visible_text", ""),
            "metadata": analysis.get("metadata", {}),
        }

    async def read_page_content(self, page: Page, *, goal: str | None = None) -> dict[str, Any]:
        snapshot = await self.observe_page(page, goal=goal)
        return {
            "title": snapshot.get("title") or self._derive_title(snapshot.get("url") or ""),
            "url": snapshot.get("url") or "https://example.com",
            "visible_text": snapshot.get("visible_text"),
            "headings": snapshot.get("headings", []),
            "paragraphs": snapshot.get("paragraphs", []),
            "tables": snapshot.get("tables", []),
            "lists": snapshot.get("lists", []),
            "links": snapshot.get("links", []),
            "metadata": snapshot.get("metadata", {}),
            "structure": snapshot.get("structure", {}),
        }

    async def observe_page(self, page: Page, *, goal: str | None = None, include_screenshot: bool = False, screenshot_path: str | None = None) -> dict[str, Any]:
        url = self._safe_value(page, "url") or self._safe_value(page, "_url") or self._session_state.get("current_url")
        title = None
        if hasattr(page, "title"):
            try:
                title_result = page.title()
                if hasattr(title_result, "__await__"):
                    title = await title_result
                else:
                    title = str(title_result) if title_result else None
            except Exception:
                pass
        if not title:
            title = self._derive_title(url or "")
        visible_text = await self._read_live_text(page)
        buttons = await self._collect_texts(page, "button, input[type='button'], input[type='submit'], [role='button']")
        forms = await self._collect_texts(page, "form")
        inputs = await self._collect_texts(page, "input, textarea, select")
        links = await self._collect_links(page)
        tables = await self._collect_tables(page)
        dialogs = await self._collect_texts(page, "dialog")
        errors = []
        navigation_state = {"url": url, "title": title, "loaded": bool(url)}
        screenshot = None
        if include_screenshot:
            try:
                screenshot = await self.take_screenshot(page, output_path=screenshot_path)
                self._session_state["screenshots"].append(screenshot)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to capture screenshot during observation: %s", exc)
        return {
            "url": self._canonicalize_url(url) if url else None,
            "title": title or self._derive_title(url or ""),
            "visible_text": visible_text,
            "buttons": buttons,
            "forms": forms,
            "inputs": inputs,
            "links": links,
            "tables": tables,
            "dialogs": dialogs,
            "errors": errors,
            "navigation_state": navigation_state,
            "screenshot": screenshot,
            "headings": await self._collect_texts(page, "h1, h2, h3"),
            "paragraphs": await self._collect_texts(page, "p"),
            "lists": await self._collect_texts(page, "li"),
            "metadata": {
                "source": "browser",
                "goal": goal or "",
                "buttons_count": len(buttons),
                "inputs_count": len(inputs),
                "links_count": len(links),
                "tables_count": len(tables),
            },
            "structure": {
                "buttons": buttons,
                "inputs": inputs,
                "links": links,
                "tables": tables,
            },
        }

    async def extract_headings(self, page: Page) -> list[str]:
        return await self._collect_texts(page, "h1, h2, h3")

    async def extract_tables(self, page: Page) -> list[dict[str, Any]]:
        return await self._collect_tables(page)

    async def extract_links(self, page: Page) -> list[dict[str, str]]:
        return await self._collect_links(page)

    async def extract_lists(self, page: Page) -> list[str]:
        return await self._collect_texts(page, "li")

    async def take_screenshot(self, page: Page, *, output_path: str | None = None) -> str:
        target_path = output_path or os.path.join(os.getcwd(), "browser-screenshot.png")
        if hasattr(page, "screenshot"):
            await page.screenshot(path=target_path, full_page=True)
        return target_path

    async def download_file(self, page: Page, selector: str, target_path: str) -> str:
        output_path = Path(target_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if hasattr(page, "locator"):
            try:
                href = await page.locator(selector).get_attribute("href")
                if href:
                    resolved_url = urljoin(page.url, href)
                    with urlopen(resolved_url) as response, output_path.open("wb") as destination:
                        shutil.copyfileobj(response, destination)
                    self._session_state["downloads"].append(str(output_path))
                    return str(output_path)
            except Exception:
                pass
            try:
                await page.locator(selector).click()
            except Exception:
                await self._click(page, selector)
        else:
            await self._click(page, selector)
        self._session_state["downloads"].append(str(output_path))
        return str(output_path)

    async def wait_for_page_load(self, page: Page, *, timeout_ms: int = 10000) -> None:
        if hasattr(page, "wait_for_load_state"):
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)

    async def open_new_tab(self, browser: Browser | None = None) -> Page:
        target_browser = browser or self._browser
        page = await target_browser.new_page()
        self._active_page = page
        self._session_state["tabs"].append({"id": id(page), "url": None, "title": None})
        return page

    async def switch_tab(self, page: Page, index: int) -> Page:
        if self._browser is None:
            return page
        browser_pages = self._browser.contexts()[0].pages() if self._browser.contexts() else []
        if not browser_pages:
            return page
        target_index = max(0, min(index, len(browser_pages) - 1))
        target_page = browser_pages[target_index]
        self._active_page = target_page
        return target_page

    async def close_tab(self, page: Page) -> None:
        if hasattr(page, "close"):
            await page.close()
        self._session_state["tabs"] = [tab for tab in self._session_state["tabs"] if tab.get("id") != id(page)]

    async def navigate_back(self, page: Page) -> None:
        if hasattr(page, "go_back"):
            await page.go_back()

    async def refresh_page(self, page: Page) -> None:
        if hasattr(page, "reload"):
            await page.reload()

    def get_session_state(self) -> dict[str, Any]:
        return dict(self._session_state)

    def _record_navigation(self, url: str, page: Page) -> None:
        self._session_state["current_url"] = url
        self._session_state["history"].append(url)
        self._session_state["current_title"] = self._derive_title(url)

    async def _collect_texts(self, page: Page, selector: str) -> list[str]:
        try:
            if hasattr(page, "locator"):
                locator = page.locator(selector)
                values = await locator.all_text_contents()
                return [value.strip() for value in values if value and value.strip()]
        except Exception:
            pass
        if isinstance(page, dict):
            return page.get(selector, []) if isinstance(page.get(selector), list) else []
        return []

    async def _collect_links(self, page: Page) -> list[dict[str, str]]:
        try:
            if hasattr(page, "locator"):
                anchors = await page.locator("a").evaluate_all("(elements) => elements.map((element) => ({ href: element.getAttribute('href'), text: element.textContent }))")
                return [{"href": anchor.get("href"), "text": anchor.get("text") or ""} for anchor in anchors if anchor.get("href")]
        except Exception:
            pass
        if isinstance(page, dict):
            links = page.get("links") or []
            if isinstance(links, list):
                return links
        return []

    async def _collect_tables(self, page: Page) -> list[dict[str, Any]]:
        try:
            if hasattr(page, "locator"):
                tables = []
                table_elements = page.locator("table")
                for index in range(await table_elements.count()):
                    table = table_elements.nth(index)
                    rows = []
                    for row in await table.locator("tr").all_inner_texts():
                        rows.append([item.strip() for item in row.split("\n") if item.strip()])
                    tables.append({"row_count": len(rows), "rows": rows})
                return tables
        except Exception:
            pass
        if isinstance(page, dict):
            tables = page.get("tables") or []
            if isinstance(tables, list):
                return tables
        return []

    async def _read_live_text(self, page: Page) -> str | None:
        try:
            if hasattr(page, "locator"):
                body_text = await page.locator("body").inner_text()
                if body_text:
                    return body_text
            if hasattr(page, "content"):
                return await page.content()
        except Exception:
            pass
        return self._safe_text(page)

    async def _click(self, page: Page, selector: str) -> None:
        if hasattr(page, "locator"):
            await page.locator(selector).click()
        else:
            raise RuntimeError("Page implementation does not support click")

    def _safe_value(self, page: Page, attr: str) -> Any:
        if isinstance(page, dict):
            return page.get(attr)
        return getattr(page, attr, None)

    def _safe_text(self, page: Page) -> str | None:
        if isinstance(page, dict):
            return page.get("visible_text") or page.get("text")
        return None

    def _safe_title(self, page: Page) -> str | None:
        title = self._safe_value(page, "title")
        if title and not callable(title):
            return str(title)
        try:
            if hasattr(page, "title"):
                title_value = page.title
                if callable(title_value):
                    title_value = title_value()
                if title_value:
                    return str(title_value)
        except Exception:
            return None
        return None

    def _looks_like_url(self, value: str) -> bool:
        parsed = urlparse(value)
        return bool(parsed.scheme and parsed.netloc) or value.startswith("http://") or value.startswith("https://")

    def _normalize_url(self, value: str) -> str:
        if not value:
            return "https://example.com"
        if value.startswith("http://") or value.startswith("https://"):
            return value.rstrip("/") or value
        return value

    def _canonicalize_url(self, value: str) -> str:
        if not value:
            return "https://example.com"
        return value.rstrip("/") or value

    def _derive_title(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or "Browser page"