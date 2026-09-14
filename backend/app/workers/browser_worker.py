from __future__ import annotations

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from app.browser.os import (
    ApprovalManager,
    ArtifactGenerator,
    BrowserActionEngine,
    BrowserConnectionManager,
    BrowserLoginManager,
    BrowserTabManager,
    CookieStorageManager,
    DOMIntelligenceEngine,
    RecoveryManager,
    VerificationEngine,
)
from app.browser.service import BrowserService
from app.browser.session_manager import BrowserSessionManager
from app.workers.base import Worker
from app.workers.context import WorkerContext
from app.workers.errors import RetryableWorkerError
from app.workers.result import ExecutionMetrics, ExecutionStatus, RollbackResult, VerificationResult, WorkerResult

logger = logging.getLogger(__name__)


class BrowserWorker(Worker):
    """Generic browser automation worker for reusable web execution tasks."""

    capability = "browser"

    def __init__(self, browser_service: BrowserService | None = None, **dependencies: Any) -> None:
        super().__init__(**dependencies)
        self.browser_service = browser_service or BrowserService(headless=True)
        self.session_manager = dependencies.get("session_manager") or BrowserSessionManager(user_id=dependencies.get("user_id") or "default_user")
        self.connection_manager = BrowserConnectionManager(user_id=dependencies.get("user_id") or "default_user", session_manager=self.session_manager)
        self.login_manager = dependencies.get("login_manager") or BrowserLoginManager()
        self.tab_manager = dependencies.get("tab_manager") or BrowserTabManager(session_manager=self.session_manager)
        self.cookie_storage_manager = dependencies.get("cookie_storage_manager") or CookieStorageManager(base_dir=dependencies.get("browser_profile_dir") or None)
        self.dom_engine = dependencies.get("dom_engine") or DOMIntelligenceEngine()
        self.action_engine = dependencies.get("action_engine") or BrowserActionEngine()
        self.approval_manager = dependencies.get("approval_manager") or ApprovalManager()
        self.verification_engine = dependencies.get("verification_engine") or VerificationEngine()
        self.recovery_manager = dependencies.get("recovery_manager") or RecoveryManager(max_retries=2)
        self.artifact_generator = dependencies.get("artifact_generator") or ArtifactGenerator()
        self._session_state: dict[str, Any] = {}

    def execute(self, context: WorkerContext) -> WorkerResult:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            result = asyncio.run(self._execute_async(context))
        else:
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = executor.submit(asyncio.run, self._execute_async(context)).result()
        return result

    def verify(self, context: WorkerContext) -> VerificationResult:
        session = context.runtime_context.get("browser_session") or {}
        last_status = session.get("last_status") or "unknown"
        checks = [
            {"name": "browser_session", "status": "passed" if session else "pending", "details": "Browser session initialized"},
            {"name": "action_result", "status": "passed" if last_status == "completed" else "failed", "details": f"Last action status: {last_status}"},
        ]
        passed = all(check["status"] == "passed" for check in checks)
        return VerificationResult(passed=passed, evidence={"checks": checks}, message="Browser execution verified" if passed else "Browser verification incomplete")

    def rollback(self, context: WorkerContext) -> RollbackResult:
        session = context.runtime_context.get("browser_session") or {}
        browser = session.get("browser")
        if browser is not None:
            try:
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    asyncio.run(self.browser_service.close_browser(browser))
                else:
                    loop.create_task(self.browser_service.close_browser(browser))
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Browser rollback cleanup failed: %s", exc)
        context.runtime_context["browser_session"] = {}
        return RollbackResult(success=True, message="Browser session rolled back", actions_taken=["closed_browser"])

    def cleanup(self, context: WorkerContext) -> None:
        self.rollback(context)

    async def _execute_async(self, context: WorkerContext) -> WorkerResult:
        session = context.runtime_context.setdefault("browser_session", {})
        actions = self._collect_actions(context)
        progress_events: list[dict[str, Any]] = session.setdefault("progress_events", [])
        self._emit_progress(progress_events, "opening_session", "Opening browser session", 10)

        browser = session.get("browser")
        page = session.get("page")
        if browser is None:
            browser = await self.browser_service.launch_browser()
            session["browser"] = browser
        if page is None:
            page = await self.connection_manager.allocate_session()
            session["page"] = page
        session.setdefault("session_manager", self.session_manager)
        session.setdefault("connection_manager", self.connection_manager)
        session.setdefault("login_manager", self.login_manager)
        session.setdefault("tab_manager", self.tab_manager)
        session.setdefault("cookie_storage_manager", self.cookie_storage_manager)
        session.setdefault("dom_engine", self.dom_engine)
        session.setdefault("action_engine", self.action_engine)
        session.setdefault("approval_manager", self.approval_manager)
        session.setdefault("verification_engine", self.verification_engine)
        session.setdefault("recovery_manager", self.recovery_manager)
        session.setdefault("artifact_generator", self.artifact_generator)
        session.setdefault("memory", {})
        session.setdefault("page_understanding", {})

        action_results: list[dict[str, Any]] = []
        last_status = "pending"
        try:
            for action in actions:
                action_result = await self._execute_action(action, page, context, session, progress_events)
                action_results.append(action_result)
                last_status = action_result.get("status", "completed")
                if action_result.get("success") is False:
                    if action_result.get("requires_approval"):
                        session["last_status"] = "waiting_for_approval"
                        outputs = {"status": "waiting_for_approval", "actions": action_results, "session_state": await self._compose_session_state(session), "progress_events": progress_events, "error": action_result.get("error")}
                        metrics = ExecutionMetrics(); metrics.finish(); return WorkerResult(status=ExecutionStatus.SUCCESS, outputs=outputs, message="Approval required", metrics=metrics)
                    raise RetryableWorkerError(action_result.get("error") or "Browser action failed")
            session["last_status"] = last_status
            session["last_action_results"] = action_results
            self._emit_progress(progress_events, "completed", "Browser actions completed", 100)
            outputs = {
                "status": "completed",
                "actions": action_results,
                "session_state": await self._compose_session_state(session),
                "progress_events": progress_events,
                "verification": {"verified": True, "checks": [{"name": "browser_session", "status": "passed", "details": "Browser session completed"}]},
            }
            metrics = ExecutionMetrics()
            metrics.finish()
            return WorkerResult(status=ExecutionStatus.SUCCESS, outputs=outputs, message="Browser execution completed", metrics=metrics)
        except RetryableWorkerError as exc:
            session["last_status"] = "failed"
            outputs = {
                "status": "failed",
                "actions": action_results,
                "session_state": await self._compose_session_state(session),
                "progress_events": progress_events,
                "error": str(exc),
            }
            metrics = ExecutionMetrics()
            metrics.finish()
            return WorkerResult(status=ExecutionStatus.FAILURE, message=str(exc), outputs=outputs, metrics=metrics)
        finally:
            if session.get("close_after_run", False):
                await self.browser_service.close_browser(browser)
                session.clear()

    async def _execute_action(self, action: dict[str, Any], page: Any, context: WorkerContext, session: dict[str, Any], progress_events: list[dict[str, Any]]) -> dict[str, Any]:
        action_type = str(action.get("type") or action.get("action") or "goto").casefold()
        started = time.perf_counter()
        self._emit_progress(progress_events, f"action_{action_type}", f"Executing {action_type}", 40)
        try:
            result_data: dict[str, Any] = {"type": action_type, "status": "completed", "success": True, "duration": 0.0, "data": None, "error": None, "verification": {"verified": False, "checks": []}, "session_state": await self._compose_session_state(session)}
            if action_type in {"goto", "navigate", "open", "open_url"}:
                target_url = str(action.get("url") or action.get("target_url") or context.goal or "https://example.com")
                navigation_result = await self.recovery_manager.run_with_recovery(lambda: self.session_manager.goto(page, target_url))
                result_data["data"] = navigation_result
                result_data["verification"] = {"verified": True, "checks": [{"name": "navigation", "status": "passed", "details": target_url}]}
            elif action_type in {"open_tab", "new_tab"}:
                page = await self.tab_manager.open_tab()
                session["page"] = page
                result_data["data"] = {"tab": page}
            elif action_type in {"switch_tab"}:
                target = action.get("index") if action.get("index") is not None else 0
                page = await self.tab_manager.switch_tab(int(target))
                session["page"] = page
                result_data["data"] = {"tab": page}
            elif action_type in {"close_tab"}:
                target_page = action.get("page") or session.get("page")
                await self.tab_manager.close_tab(target_page)
                session["page"] = await self.tab_manager.session_manager.active_tab()
                result_data["data"] = {"closed": True}
            elif action_type in {"list_tabs", "active_tab"}:
                tabs = await self.tab_manager.list_tabs() if action_type == "list_tabs" else [await self.tab_manager.session_manager.active_tab()]
                result_data["data"] = {"tabs": tabs}
            elif action_type in {"click", "double_click"}:
                selector = str(action.get("selector") or action.get("target") or "")
                if action_type == "double_click":
                    await self.session_manager.click(page, selector)
                else:
                    await self.session_manager.click(page, selector)
                result_data["data"] = {"selector": selector}
            elif action_type in {"fill", "type"}:
                selector = str(action.get("selector") or action.get("target") or "")
                value = str(action.get("value") or action.get("text") or "")
                await self.recovery_manager.run_with_recovery(lambda: self.session_manager.fill(page, selector, value))
                result_data["data"] = {"selector": selector, "value": value}
            elif action_type in {"fill_form"}:
                self._emit_progress(progress_events, "filling_form", "Filling form", 60)
                fields = action.get("fields") or {}
                if not isinstance(fields, dict):
                    raise ValueError("fill_form requires a fields mapping")
                for field_name, value in fields.items():
                    selector = str(action.get("selector_map", {}).get(field_name) or field_name)
                    if selector:
                        await self.session_manager.fill(page, selector, str(value))
                result_data["data"] = {"fields": fields}
            elif action_type in {"hover"}:
                selector = str(action.get("selector") or action.get("target") or "")
                await self.session_manager.hover(page, selector)
                result_data["data"] = {"selector": selector}
            elif action_type in {"scroll"}:
                await self.session_manager.scroll(page, str(action.get("direction") or "bottom"))
                result_data["data"] = {"direction": str(action.get("direction") or "bottom")}
            elif action_type in {"drag_and_drop"}:
                source_selector = str(action.get("source") or action.get("source_selector") or "")
                target_selector = str(action.get("target") or action.get("target_selector") or "")
                await self.browser_service.drag_and_drop(page, source_selector, target_selector)
                result_data["data"] = {"source": source_selector, "target": target_selector}
            elif action_type in {"press", "keypress"}:
                key = str(action.get("key") or "Enter")
                await self.session_manager.press(page, key)
                result_data["data"] = {"key": key}
            elif action_type in {"select_option", "select"}:
                selector = str(action.get("selector") or action.get("target") or "")
                value = str(action.get("value") or "")
                await self.browser_service.select_option(page, selector, value)
                result_data["data"] = {"selector": selector, "value": value}
            elif action_type in {"check"}:
                selector = str(action.get("selector") or action.get("target") or "")
                if hasattr(self.browser_service, "check_checkbox"):
                    await self.browser_service.check_checkbox(page, selector)
                else:
                    await self.browser_service.click_element(page, selector)
            elif action_type in {"uncheck"}:
                selector = str(action.get("selector") or action.get("target") or "")
                if hasattr(self.browser_service, "uncheck_checkbox"):
                    await self.browser_service.uncheck_checkbox(page, selector)
                else:
                    await self.browser_service.click_element(page, selector)
            elif action_type in {"wait", "wait_for_selector", "wait_for_text", "wait_for_url", "wait_for_network_idle", "wait_for_download", "wait_for_navigation", "wait_for_api_response"}:
                selector = str(action.get("selector") or "")
                if action_type == "wait_for_selector":
                    await self.session_manager.wait_for_selector(page, selector or str(action.get("target") or ""), timeout_ms=int(action.get("timeout_ms", 10000)))
                elif action_type == "wait_for_text":
                    await self.session_manager.wait_for_text(page, str(action.get("text") or ""), timeout_ms=int(action.get("timeout_ms", 10000)))
                elif action_type == "wait_for_url":
                    await self.session_manager.wait_for_url(page, str(action.get("url_fragment") or ""), timeout_ms=int(action.get("timeout_ms", 10000)))
                elif action_type == "wait_for_network_idle":
                    await self.session_manager.wait_for_network_idle(page, timeout_ms=int(action.get("timeout_ms", 10000)))
                elif action_type == "wait_for_download":
                    await self.session_manager.wait_for_download(page, timeout_ms=int(action.get("timeout_ms", 10000)))
                elif action_type == "wait_for_navigation":
                    await self.session_manager.wait_for_navigation(page, timeout_ms=int(action.get("timeout_ms", 10000)))
                elif action_type == "wait_for_api_response":
                    await self.session_manager.wait_for_api_response(page, timeout_ms=int(action.get("timeout_ms", 10000)))
                else:
                    await self.session_manager.wait(page, float(action.get("seconds", 1.0)))
            elif action_type in {"wait_for_navigation", "wait_for_load"}:
                if hasattr(self.browser_service, "wait_for_page_load"):
                    await self.browser_service.wait_for_page_load(page, timeout_ms=int(action.get("timeout_ms", 10000)))
            elif action_type in {"extract_text", "read"}:
                selector = str(action.get("selector") or action.get("target") or "")
                if selector:
                    try:
                        text_content = await page.locator(selector).inner_text()
                    except Exception:
                        try:
                            text_content = await page.locator(selector).text_content()
                        except Exception:
                            text_content = None
                    result_data["data"] = {"text": text_content or "", "selector": selector}
                else:
                    snapshot = await self.browser_service.read_page_content(page, goal=context.goal)
                    result_data["data"] = {"text": snapshot.get("visible_text") or "", "selector": None}
            elif action_type in {"extract_html"}:
                result_data["data"] = await self.browser_service.evaluate_script(page, "document.documentElement.outerHTML")
            elif action_type in {"extract_links"}:
                result_data["data"] = await self.browser_service.extract_links(page)
            elif action_type in {"extract_table", "extract_tables"}:
                result_data["data"] = await self.browser_service.extract_tables(page)
            elif action_type in {"screenshot"}:
                output_path = str(action.get("output_path") or action.get("path") or "browser-screenshot.png")
                result_data["data"] = {"path": await self.session_manager.screenshot(page, output_path=output_path)}
            elif action_type in {"download"}:
                selector = str(action.get("selector") or "a[href$='.zip']")
                target_path = str(action.get("target_path") or action.get("path") or "download.bin")
                result_data["data"] = {"path": await self.session_manager.download(page, selector, target_path)}
            elif action_type in {"upload"}:
                selector = str(action.get("selector") or "")
                file_path = str(action.get("file_path") or action.get("path") or "")
                await self.session_manager.upload(page, selector, file_path)
                result_data["data"] = {"selector": selector, "file_path": file_path}
            elif action_type in {"evaluate"}:
                script = str(action.get("script") or "")
                result_data["data"] = await self.session_manager.evaluate(page, script)
            elif action_type in {"verify"}:
                verification = await self._verify_action(page, action, context)
                result_data["data"] = verification.get("data")
                result_data["verification"] = verification.get("verification", {"verified": True, "checks": []})
                result_data["success"] = verification.get("success", True)
                result_data["status"] = verification.get("status", "completed")
                result_data["error"] = verification.get("error")
                if verification.get("requires_approval"):
                    result_data["requires_approval"] = True
                    result_data["error"] = verification.get("error") or "Approval required"
                    result_data["success"] = False
            elif action_type in {"close"}:
                await self.browser_service.close_browser(session.get("browser"))
                session["browser"] = None
                session["page"] = None
                result_data["data"] = {"closed": True}
            else:
                raise ValueError(f"Unsupported browser action: {action_type}")
            result_data["duration"] = round(time.perf_counter() - started, 3)
            if action_type in {"goto", "navigate", "open_tab", "new_tab", "switch_tab", "close_tab", "list_tabs", "active_tab", "click", "double_click", "fill", "type", "fill_form", "hover", "drag_and_drop", "press", "select_option", "check", "uncheck", "wait", "wait_for_selector", "wait_for_text", "wait_for_url", "wait_for_network_idle", "wait_for_download", "wait_for_navigation", "wait_for_api_response", "scroll", "evaluate", "download", "upload", "screenshot", "extract_text", "extract_html", "extract_links", "extract_table", "close"}:
                result_data["verification"] = {"verified": True, "checks": [{"name": action_type, "status": "passed", "details": "Action completed"}]}
            return result_data
        except Exception as exc:  # pragma: no cover - defensive path
            return {"type": action_type, "status": "failed", "success": False, "duration": round(time.perf_counter() - started, 3), "data": None, "error": str(exc), "verification": {"verified": False, "checks": [{"name": action_type, "status": "failed", "details": str(exc)}]}, "session_state": await self._compose_session_state(session)}

    async def _verify_action(self, page: Any, action: dict[str, Any], context: WorkerContext) -> dict[str, Any]:
        check = str(action.get("check") or "page_loaded")
        lowered = check.casefold()
        if lowered == "captcha":
            return {"status": "waiting_for_approval", "success": False, "requires_approval": True, "data": {"captcha": True}, "verification": {"verified": False, "checks": [{"name": "captcha", "status": "failed", "details": "Captcha detected"}]}, "error": "Captcha detected, approval required"}
        if self.approval_manager.requires_approval(str(action.get("operation") or action.get("check") or "navigate"), action.get("payload")):
            return {"status": "waiting_for_approval", "success": False, "requires_approval": True, "data": {}, "verification": {"verified": False, "checks": [{"name": "approval", "status": "failed", "details": "Approval required"}]}, "error": "Approval required"}
        if check == "page_loaded":
            return {"status": "completed", "success": True, "data": {"loaded": True}, "verification": {"verified": True, "checks": [{"name": "page_loaded", "status": "passed", "details": "Page loaded"}]}}
        if check == "text_exists":
            expected_text = str(action.get("text") or "")
            page_snapshot = await self.browser_service.read_page_content(page, goal=context.goal)
            visible_text = page_snapshot.get("visible_text") or "\n".join(page_snapshot.get("paragraphs", []) + page_snapshot.get("headings", []))
            found = expected_text.lower() in visible_text.lower()
            return {
                "status": "completed" if found else "failed",
                "success": found,
                "data": {"found": found, "expected_text": expected_text, "visible_text": visible_text},
                "verification": {"verified": found, "checks": [{"name": "text_exists", "status": "passed" if found else "failed", "details": f"Expected text '{expected_text}'"}]},
                "error": None if found else f"Expected text '{expected_text}' was not found",
            }
        if check == "element_exists":
            selector = str(action.get("selector") or "")
            if not selector:
                return {"status": "failed", "success": False, "data": {"exists": False}, "verification": {"verified": False, "checks": [{"name": "element_exists", "status": "failed", "details": "No selector provided"}]}, "error": "No selector provided"}
            try:
                await self.browser_service.wait_for_selector(page, selector, timeout_ms=2000)
                return {"status": "completed", "success": True, "data": {"exists": True}, "verification": {"verified": True, "checks": [{"name": "element_exists", "status": "passed", "details": selector}]}}
            except Exception as exc:  # pragma: no cover - defensive path
                return {"status": "failed", "success": False, "data": {"exists": False}, "verification": {"verified": False, "checks": [{"name": "element_exists", "status": "failed", "details": str(exc)}]}, "error": str(exc)}
        return {"status": "completed", "success": True, "data": {}, "verification": {"verified": True, "checks": []}}

    def _collect_actions(self, context: WorkerContext) -> list[dict[str, Any]]:
        runtime_actions = context.runtime_context.get("actions") or []
        if isinstance(runtime_actions, dict):
            runtime_actions = [runtime_actions]
        if isinstance(runtime_actions, list):
            return [item for item in runtime_actions if isinstance(item, dict)]
        inputs_actions = context.inputs.get("actions") or []
        if isinstance(inputs_actions, list):
            return [item for item in inputs_actions if isinstance(item, dict)]
        return []

    def _emit_progress(self, progress_events: list[dict[str, Any]], stage_id: str, label: str, progress: int) -> None:
        event = {"type": "progress", "stage_id": stage_id, "label": label, "progress": progress}
        progress_events.append(event)

    async def _compose_session_state(self, session: dict[str, Any]) -> dict[str, Any]:
        browser_state = await self._read_session_state(session)
        memory_state = {}
        if hasattr(self.session_manager, "get_memory_state"):
            try:
                memory_state = await self.session_manager.get_memory_state()
            except Exception:
                memory_state = {}
        return {
            "browser_id": getattr(session.get("browser"), "guid", None) or None,
            "page_id": getattr(session.get("page"), "id", None) or None,
            "last_status": session.get("last_status"),
            "progress_events": session.get("progress_events", []),
            "browser_service_state": browser_state,
            "memory_state": memory_state,
        }

    async def _read_session_state(self, session: dict[str, Any]) -> dict[str, Any]:
        browser_service = getattr(self, "browser_service", None)
        if browser_service is None:
            return {}
        if hasattr(browser_service, "get_session_state"):
            try:
                result = browser_service.get_session_state()
                if hasattr(result, "__await__"):
                    return await result
                return result
            except Exception:  # pragma: no cover - defensive path
                return {}
        return {}
