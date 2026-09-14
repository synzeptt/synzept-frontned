from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import UUID

from app.browser.decision_engine import LLMDecisionEngine
from app.browser.observer import PageObserver
from app.browser.service import BrowserService
from app.execution.artifacts import Artifact, ArtifactService
from app.execution.engine import ExecutionContext

logger = logging.getLogger(__name__)


class BrowserWorker:
    def __init__(
        self,
        browser_service: BrowserService | None = None,
        artifact_service: ArtifactService | None = None,
        session_manager: Any | None = None,
    ) -> None:
        self.browser_service = browser_service or BrowserService(headless=True)
        self.artifact_service = artifact_service
        self.session_manager = session_manager
        self.observer = PageObserver(browser_service=self.browser_service)
        self.decision_engine = LLMDecisionEngine()

    async def _navigate(self, page: Any, url: str) -> Any:
        navigate = getattr(self.browser_service, "safe_navigate_to_url", None)
        navigation_result = None
        if callable(navigate):
            navigation_result = await navigate(page, url)
        else:
            navigation_result = await self.browser_service.navigate_to_url(page, url)
        if isinstance(page, dict) and isinstance(navigation_result, dict):
            page["url"] = navigation_result.get("url", page.get("url"))
        return navigation_result

    async def run(
        self,
        *,
        goal: str,
        metadata: dict[str, Any],
        context: ExecutionContext,
        user_id: UUID | None = None,
        action_id: UUID | None = None,
        task_id: UUID | None = None,
    ) -> dict[str, Any]:
        requires_approval = bool(metadata.get("requires_approval") or metadata.get("worker_requires_approval"))
        if requires_approval and not bool(metadata.get("approved")):
            return {
                "status": "waiting_for_approval",
                "output": "Approval is required before executing this browser workflow.",
                "metadata": {"requires_approval": True, "approval_reason": metadata.get("approval_reason") or "This browser workflow requires explicit approval before continuing."},
            }

        await self._emit_progress(context, "planning", "Planning browser workflow", 10)
        browser = await self.browser_service.launch_browser()
        state: dict[str, Any] = {
            "goal": goal,
            "target_url": str(metadata.get("target_url") or metadata.get("url") or self._infer_target_url(goal)),
            "activity": "Preparing browser session",
            "current_url": str(metadata.get("target_url") or metadata.get("url") or self._infer_target_url(goal)),
            "current_step": "planning",
            "next_step": "launch_browser",
            "progress": 10,
            "action_history": [],
            "timeline": [],
            "logs": [],
            "latest_screenshot": None,
            "session_state": {},
            "browser_health": {
                "successes": 0,
                "failures": 0,
                "retries": 0,
                "recovery_success": 0,
                "average_action_duration": 0.0,
                "download_success": 0,
                "navigation_success": 0,
                "timeout_frequency": 0,
            },
            "memory": {
                "visited_urls": [],
                "completed_actions": [],
                "previous_screenshots": [],
                "extracted_information": [],
                "downloaded_files": [],
                "filled_forms": [],
                "open_tabs": [],
                "structured_facts": [],
            },
        }
        try:
            page = await self.browser_service.open_page(browser)
            self._update_state(context, state, "launching_browser", "Launching browser", 15, current_url=None)
            await self._emit_progress(context, "launching_browser", "Launching browser", 15)

            actions = metadata.get("actions") if isinstance(metadata.get("actions"), list) else []
            target_url = state["target_url"]
            page_states: list[dict[str, Any]] = []
            action_logs: list[dict[str, Any]] = []
            pages: list[dict[str, Any]] = []
            sources: list[str] = []
            downloads: list[dict[str, Any]] = []

            if actions:
                await self._emit_progress(context, "executing_actions", "Executing browser actions", 30)
                for action in actions:
                    action_result = await self._execute_action(page, action, goal, context, state)
                    action_logs.append({"action": action, "result": action_result})
                    snapshot = action_result.get("snapshot")
                    if snapshot:
                        page_states.append(snapshot)
                        pages.append(self._build_page_record(snapshot, action_result.get("navigation") or {}, goal))
                        sources.append(snapshot.get("url") or target_url)
                    if action_result.get("download_path"):
                        downloads.append({"name": action_result.get("download_name") or "download", "path": action_result.get("download_path")})
                    page_state = await self.browser_service.read_page_content(page, goal=goal)
                    page_states.append(page_state)
            else:
                await self._emit_progress(context, "navigating", "Navigating to target URL", 25)
                self._update_state(context, state, "navigating", f"Navigating to {target_url}", 25, current_url=target_url)
                navigation_result = await self._navigate(page, target_url)
                await self._emit_progress(context, "reading_page", "Reading page content", 45)
                snapshot = await self.browser_service.read_page_content(page, goal=goal)
                pages.append(self._build_page_record(snapshot, navigation_result, goal))
                sources.append(snapshot.get("url") or target_url)
                page_states.append(snapshot)
                self._remember_page(state, snapshot)
                reasoning = await self._run_reasoning_loop(page, goal, context, state, target_url)
                page_states.extend(reasoning.get("observations", []))
                pages.extend(reasoning.get("pages", []))
                sources.extend(reasoning.get("sources", []))
                action_logs.extend(reasoning.get("action_logs", []))
                downloads.extend(reasoning.get("downloads", []))
                if reasoning.get("latest_snapshot"):
                    state["current_url"] = reasoning["latest_snapshot"].get("url") or state["current_url"]
                if reasoning.get("decision"):
                    self._update_state(context, state, "reasoning", reasoning["decision"].get("reason") or "Reasoning over page state", 70, current_url=state.get("current_url"))

            await self._emit_progress(context, "extracting_information", "Extracting browser information", 70)
            screenshot_path = None
            try:
                screenshot_path = await self.browser_service.take_screenshot(page)
                state["latest_screenshot"] = screenshot_path
            except Exception as exc:  # noqa: BLE001
                logger.warning("Screenshot failed: %s", exc)
            if metadata.get("allow_downloads", True) and hasattr(self.browser_service, "download_file"):
                await self._emit_progress(context, "downloading", "Downloading files if available", 75)
                download_selector = metadata.get("download_selector", "a[href$='.zip']")
                download_target = str(metadata.get("download_target") or "downloads.zip")
                try:
                    download_path = await self.browser_service.download_file(page, download_selector, download_target)
                    downloads.append({"name": Path(download_path).name, "path": download_path})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Download failed: %s", exc)

            await self._emit_progress(context, "generating_report", "Generating report", 85)
            report = self._build_report(goal, pages, sources, page_states, action_logs)
            metadata_payload = self._build_metadata(goal, target_url, pages, sources, downloads, screenshot_path, page_states, action_logs)
            metadata_payload["reasoning"] = {
                "enabled": bool(metadata.get("allow_dynamic_reasoning", True)),
                "observations": state.get("reasoning_observations", []),
                "decisions": state.get("reasoning_decisions", []),
                "recovery_attempts": state.get("recovery_attempts", []),
            }
            metadata_payload["memory"] = state.get("memory", {})
            metadata_payload["browser_health"] = self._build_browser_health(state, action_logs)
            metadata_payload["reliability_metrics"] = self._build_reliability_metrics(state, pages, action_logs)
            metadata_payload["timeline"] = state["timeline"]
            metadata_payload["session_state"] = state["session_state"]
            metadata_payload["execution_logs"] = state["logs"]
            metadata_payload["current_activity"] = state["activity"]
            metadata_payload["current_url"] = state["current_url"]
            metadata_payload["current_step"] = state["current_step"]
            metadata_payload["next_step"] = state["next_step"]

            artifacts: list[Artifact] = [Artifact(artifact_type="markdown", title="browser-report.md", content=report)]
            if screenshot_path:
                artifacts.append(Artifact(artifact_type="image", title="page-screenshot.png", content=screenshot_path))
            if downloads:
                artifacts.append(Artifact(artifact_type="archive", title="downloads.zip", content=downloads[0]["path"]))
            artifacts.append(Artifact(artifact_type="json", title="metadata.json", content=json.dumps(metadata_payload)))

            if self.artifact_service is not None and user_id is not None:
                await self.artifact_service.save(
                    user_id=UUID(str(user_id)),
                    action_id=UUID(str(action_id)) if action_id is not None else None,
                    task_id=UUID(str(task_id)) if task_id is not None else None,
                    artifacts=artifacts,
                )

            self._update_state(context, state, "completed", "Completed", 100, current_url=state.get("current_url"))
            await self._emit_progress(context, "saving_artifacts", "Saving artifacts", 95)
            await self._emit_progress(context, "completed", "Completed", 100)
            return {
                "status": "completed",
                "output": report,
                "summary": report[:400],
                "artifacts": artifacts,
                "metadata": metadata_payload,
                "execution_statistics": {"pages": len(pages), "actions": len(action_logs), "downloads": len(downloads)},
                "execution_duration": 1,
                "source_references": sources,
                "result": {"report": report, "metadata": metadata_payload},
            }
        finally:
            await self.browser_service.close_browser(browser)

    async def _execute_action(self, page: Any, action: dict[str, Any], goal: str, context: ExecutionContext, state: dict[str, Any]) -> dict[str, Any]:
        action_type = str(action.get("type", "navigate")).casefold()
        label = action.get("label") or action_type
        self._update_state(context, state, f"action_{action_type}", f"Executing {label}", 30, current_url=state.get("current_url"))
        await self._emit_progress(context, f"action_{action_type}", f"Executing {label}", 30)

        if self._requires_approval(action, state):
            result = {"type": action_type, "label": label, "status": "waiting_for_approval", "success": False, "duration": 0.0, "current_url": state.get("current_url"), "page_title": None, "screenshot": None, "error": "Approval required before this action can run.", "state": self._empty_page_state(), "recovery_attempts": [], "verification": {"verified": False, "checks": [{"name": "approval", "status": "pending", "details": "Approval required"}]}}
            self._append_timeline(state, action, result, None, 0.0)
            self._update_browser_health(state, result, action_type)
            return result

        started_at = perf_counter()
        result = {"type": action_type, "label": label, "status": "skipped", "success": False, "duration": 0.0, "current_url": state.get("current_url"), "page_title": None, "screenshot": None, "error": None, "state": self._empty_page_state(), "recovery_attempts": [], "verification": {"verified": False, "checks": []}}
        try:
            action_result = await self._perform_action_once(page, action, goal)
            result.update(action_result)
            result.setdefault("success", True)
            result.setdefault("status", "completed")
            result["duration"] = round(perf_counter() - started_at, 3)
            if result.get("status") in {"completed", "navigated", "clicked", "filled", "cleared", "pressed", "selected", "scrolled", "waited", "hovered", "dragged", "uploaded", "downloaded", "new_tab", "switched_tab", "closed_tab", "navigated_back", "refreshed", "read", "screenshot_taken", "observed", "evaluated"}:
                result["success"] = True
                result["error"] = None
        except Exception as exc:  # noqa: BLE001
            result["status"] = "failed"
            result["success"] = False
            result["error"] = str(exc)
            logger.warning("Browser action failed (%s): %s", action_type, exc)
            if self._should_retry(action, action_type, exc):
                recovery_result = await self._attempt_recovery(page, action, goal, context, state, exc)
                result.update(recovery_result)
                result["recovery_attempts"] = recovery_result.get("recovery_attempts", [])
                result["duration"] = round(perf_counter() - started_at, 3)
                if recovery_result.get("success"):
                    result["success"] = True
                    result["status"] = "recovered"

        if action.get("capture_snapshot"):
            result["snapshot"] = await self._safe_read_snapshot(page, goal)
        if action_type == "observe" and not result.get("snapshot"):
            result["snapshot"] = await self._safe_read_snapshot(page, goal)

        snapshot = result.get("snapshot")
        try:
            page_state = await self._inspect_page_state(page, snapshot, goal)
        except Exception:  # noqa: BLE001
            page_state = self._empty_page_state()
        result["state"] = {"page_state": page_state}
        if isinstance(snapshot, dict):
            result["current_url"] = snapshot.get("url") or result.get("current_url") or state.get("current_url")
            result["page_title"] = snapshot.get("title") or result.get("page_title")
            if not result.get("screenshot"):
                result["screenshot"] = self._take_screenshot_reference(snapshot)
        elif isinstance(result.get("navigation"), dict):
            result["current_url"] = result["navigation"].get("url") or result.get("current_url") or state.get("current_url")
        if isinstance(snapshot, dict) and snapshot.get("url"):
            state["current_url"] = snapshot["url"]
        elif isinstance(result.get("navigation"), dict) and result["navigation"].get("url"):
            state["current_url"] = result["navigation"]["url"]
        result["verification"] = self._verify_action_result(action_type, result, snapshot, page_state)
        self._update_browser_health(state, result, action_type)
        self._append_timeline(state, action, result, snapshot, result.get("duration", 0.0))
        return result

    async def _perform_action_once(self, page: Any, action: dict[str, Any], goal: str) -> dict[str, Any]:
        action_type = str(action.get("type", "navigate")).casefold()
        result: dict[str, Any] = {"status": "completed", "success": True}
        if action_type in {"open", "open_url", "navigate"}:
            target_url = str(action.get("url") or action.get("target_url") or self._infer_target_url(goal))
            result["navigation"] = await self._navigate(page, target_url)
            result["status"] = "navigated"
        elif action_type in {"click", "double_click", "right_click"}:
            selector = str(action.get("selector") or action.get("target") or "")
            if selector:
                if action_type == "double_click":
                    if hasattr(self.browser_service, "double_click"):
                        await self.browser_service.double_click(page, selector)
                    else:
                        await self.browser_service.click_element(page, selector)
                elif action_type == "right_click":
                    if hasattr(self.browser_service, "right_click"):
                        await self.browser_service.right_click(page, selector)
                    else:
                        await self.browser_service.click_element(page, selector)
                else:
                    await self.browser_service.click_element(page, selector)
            else:
                await self.browser_service.click_by_text(page, str(action.get("text") or ""))
            result["status"] = "clicked"
        elif action_type in {"fill", "type"}:
            selector = str(action.get("selector") or action.get("target") or "")
            await self.browser_service.fill_input(page, selector, str(action.get("value") or ""))
            result["status"] = "filled"
        elif action_type in {"clear_input", "clear"}:
            selector = str(action.get("selector") or action.get("target") or "")
            await self.browser_service.clear_input(page, selector)
            result["status"] = "cleared"
        elif action_type == "keypress":
            await self.browser_service.press_key(page, str(action.get("key") or "Enter"))
            result["status"] = "pressed"
        elif action_type in {"select", "select_dropdown"}:
            selector = str(action.get("selector") or action.get("target") or "")
            await self.browser_service.select_option(page, selector, str(action.get("value") or ""))
            result["status"] = "selected"
        elif action_type in {"check", "check_checkbox"}:
            selector = str(action.get("selector") or action.get("target") or "")
            if hasattr(self.browser_service, "check_checkbox"):
                await self.browser_service.check_checkbox(page, selector)
            else:
                await self.browser_service.click_element(page, selector)
            result["status"] = "checked"
        elif action_type in {"uncheck", "uncheck_checkbox"}:
            selector = str(action.get("selector") or action.get("target") or "")
            if hasattr(self.browser_service, "uncheck_checkbox"):
                await self.browser_service.uncheck_checkbox(page, selector)
            else:
                await self.browser_service.click_element(page, selector)
            result["status"] = "unchecked"
        elif action_type == "scroll":
            await self.browser_service.scroll(page, str(action.get("direction") or "bottom"))
            result["status"] = "scrolled"
        elif action_type == "wait":
            if hasattr(self.browser_service, "wait_for_selector") and action.get("selector"):
                await self.browser_service.wait_for_selector(page, str(action.get("selector") or ""), timeout_ms=int(action.get("timeout_ms", 10000)))
            elif hasattr(self.browser_service, "wait"):
                await self.browser_service.wait(page, float(action.get("seconds", 1.0)))
            result["status"] = "waited"
        elif action_type == "hover":
            selector = str(action.get("selector") or action.get("target") or "")
            await self.browser_service.hover(page, selector)
            result["status"] = "hovered"
        elif action_type == "drag_and_drop":
            await self.browser_service.drag_and_drop(page, str(action.get("source_selector") or ""), str(action.get("target_selector") or ""))
            result["status"] = "dragged"
        elif action_type == "upload":
            await self.browser_service.upload_file(page, str(action.get("selector") or ""), str(action.get("file_path") or ""))
            result["status"] = "uploaded"
        elif action_type == "download":
            selector = str(action.get("selector") or "a[href$='.zip']")
            target_path = str(action.get("target_path") or action.get("download_target") or "downloads.zip")
            result["download_path"] = await self.browser_service.download_file(page, selector, target_path)
            result["download_name"] = Path(result["download_path"]).name
            result["status"] = "downloaded"
        elif action_type in {"new_tab", "open_tab"}:
            await self.browser_service.open_new_tab()
            result["status"] = "new_tab"
        elif action_type == "switch_tab":
            await self.browser_service.switch_tab(page, int(action.get("index", 0)))
            result["status"] = "switched_tab"
        elif action_type == "close_tab":
            await self.browser_service.close_tab(page)
            result["status"] = "closed_tab"
        elif action_type == "back":
            await self.browser_service.navigate_back(page)
            result["status"] = "navigated_back"
        elif action_type == "forward":
            if hasattr(self.browser_service, "navigate_forward"):
                await self.browser_service.navigate_forward(page)
            else:
                await self.browser_service.navigate_back(page)
            result["status"] = "navigated_forward"
        elif action_type == "refresh":
            await self.browser_service.refresh_page(page)
            result["status"] = "refreshed"
        elif action_type == "read":
            result["snapshot"] = await self._safe_read_snapshot(page, goal)
            result["status"] = "read"
        elif action_type == "screenshot":
            result["screenshot_path"] = await self.browser_service.take_screenshot(page, output_path=str(action.get("output_path") or "browser-screenshot.png"))
            result["status"] = "screenshot_taken"
        elif action_type == "observe":
            result["snapshot"] = await self._safe_observe_page(page, goal)
            result["status"] = "observed"
        elif action_type == "evaluate":
            result["value"] = await self.browser_service.evaluate_script(page, str(action.get("script") or ""))
            result["status"] = "evaluated"
        else:
            result["status"] = "unsupported"
            result["success"] = False
            result["error"] = f"Unsupported browser action type: {action_type}"
            raise RuntimeError(result["error"])
        return result

    async def _attempt_recovery(self, page: Any, action: dict[str, Any], goal: str, context: ExecutionContext, state: dict[str, Any], error: Exception) -> dict[str, Any]:
        action_type = str(action.get("type", "navigate")).casefold()
        recovery_attempts = []
        if action_type in {"click", "double_click", "right_click"}:
            selector = str(action.get("selector") or action.get("target") or "")
            recovery_attempts.append({"type": "scroll_then_retry", "message": "Retrying after scrolling to the target area"})
            if hasattr(self.browser_service, "scroll"):
                await self.browser_service.scroll(page, "bottom")
            if hasattr(self.browser_service, "wait"):
                await self.browser_service.wait(page, 0.1)
            if selector:
                try:
                    await self.browser_service.click_element(page, selector)
                    recovery_attempts.append({"type": "retry", "message": "Recovered by repeating the click"})
                    snapshot = await self._safe_read_snapshot(page, goal)
                    return {"status": "recovered", "success": True, "snapshot": snapshot, "recovery_attempts": recovery_attempts, "state": {"page_state": self._empty_page_state()}}
                except Exception as retry_exc:  # noqa: BLE001
                    recovery_attempts.append({"type": "retry_failed", "message": str(retry_exc)})
        elif action_type in {"open", "open_url", "navigate"}:
            recovery_attempts.append({"type": "refresh_and_retry", "message": "Retrying navigation after a refresh"})
            if hasattr(self.browser_service, "refresh_page"):
                await self.browser_service.refresh_page(page)
            target_url = str(action.get("url") or action.get("target_url") or self._infer_target_url(goal))
            try:
                await self._navigate(page, target_url)
                recovery_attempts.append({"type": "retry", "message": "Recovered by re-navigating to the target URL"})
                snapshot = await self._safe_read_snapshot(page, goal)
                return {"status": "recovered", "success": True, "snapshot": snapshot, "recovery_attempts": recovery_attempts, "state": {"page_state": self._empty_page_state()}}
            except Exception as retry_exc:  # noqa: BLE001
                recovery_attempts.append({"type": "retry_failed", "message": str(retry_exc)})
        elif action_type in {"fill", "type"}:
            recovery_attempts.append({"type": "retry", "message": "Retrying the form input after an initial failure"})
            try:
                await self.browser_service.fill_input(page, str(action.get("selector") or action.get("target") or ""), str(action.get("value") or ""))
                snapshot = await self._safe_read_snapshot(page, goal)
                return {"status": "recovered", "success": True, "snapshot": snapshot, "recovery_attempts": recovery_attempts, "state": {"page_state": self._empty_page_state()}}
            except Exception as retry_exc:  # noqa: BLE001
                recovery_attempts.append({"type": "retry_failed", "message": str(retry_exc)})
        snapshot = await self._safe_read_snapshot(page, goal)
        return {"status": "failed", "success": False, "snapshot": snapshot, "recovery_attempts": recovery_attempts, "error": str(error), "state": {"page_state": self._empty_page_state()}}

    async def _safe_read_snapshot(self, page: Any, goal: str) -> dict[str, Any]:
        try:
            return await self.browser_service.read_page_content(page, goal=goal)
        except Exception:  # noqa: BLE001
            try:
                return await self.browser_service.observe_page(page, goal=goal)
            except Exception:  # noqa: BLE001
                return {"title": "Unavailable", "url": getattr(page, "url", None) if hasattr(page, "url") else None, "metadata": {}}

    async def _safe_observe_page(self, page: Any, goal: str) -> dict[str, Any]:
        if hasattr(self.browser_service, "observe_page"):
            return await self.browser_service.observe_page(page, goal=goal)
        return await self._safe_read_snapshot(page, goal)

    async def _inspect_page_state(self, page: Any, snapshot: dict[str, Any] | None, goal: str) -> dict[str, Any]:
        observed = await self._safe_observe_page(page, goal) if hasattr(self.browser_service, "observe_page") else None
        snapshot_payload = snapshot or {}
        observed_payload = observed or {}
        url = snapshot_payload.get("url") or observed_payload.get("url") or getattr(page, "url", None) if hasattr(page, "url") else None
        visible_text = snapshot_payload.get("paragraphs") or observed_payload.get("visible_text") or ""
        text = " ".join(str(item) for item in visible_text if isinstance(item, str)) if isinstance(visible_text, list) else str(visible_text or "")
        lowered = " ".join([str(url or ""), text, snapshot_payload.get("title") or "", observed_payload.get("title") or ""]).casefold()
        loading_state = "idle"
        if "loading" in lowered or "spinner" in lowered:
            loading_state = "loading"
        if "captcha" in lowered:
            loading_state = "captcha"
        if "login" in lowered or "sign in" in lowered:
            loading_state = "login"
        return {
            "loading_state": loading_state,
            "navigation_completed": bool(url),
            "redirect_occurred": "redirect" in lowered,
            "login_page": "login" in lowered or "sign in" in lowered,
            "error_page": any(term in lowered for term in ["error", "not found", "404", "500", "access denied"]),
            "popup": bool(observed_payload.get("dialogs")) or "popup" in lowered,
            "modal_dialog": bool(observed_payload.get("dialogs")) or "modal" in lowered,
            "cookie_banner": "cookie" in lowered,
            "file_download": "download" in lowered and "file" in lowered,
            "empty_results": "no results" in lowered or "0 results" in lowered,
            "validation_error": "invalid" in lowered or "required" in lowered or "validation" in lowered,
            "rate_limiting": "rate limit" in lowered or "too many requests" in lowered,
            "captcha": "captcha" in lowered,
            "network_failure": "network" in lowered or "timeout" in lowered,
            "unexpected_page": "unexpected" in lowered,
            "url": url,
            "title": snapshot_payload.get("title") or observed_payload.get("title"),
        }

    def _verify_action_result(self, action_type: str, result: dict[str, Any], snapshot: dict[str, Any] | None, page_state: dict[str, Any]) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        verified = bool(result.get("success"))
        if action_type in {"navigate", "open", "open_url"}:
            checks.append({"name": "navigation", "status": "passed" if verified else "failed", "details": "Navigation completed"})
        elif action_type in {"click", "double_click", "right_click"}:
            checks.append({"name": "click", "status": "passed" if verified else "failed", "details": "Target action completed"})
        elif action_type in {"fill", "type"}:
            checks.append({"name": "input", "status": "passed" if verified else "failed", "details": "Input value applied"})
        elif action_type == "download":
            checks.append({"name": "download", "status": "passed" if result.get("download_path") else "failed", "details": "Download path generated"})
        else:
            checks.append({"name": "basic", "status": "passed" if verified else "failed", "details": "Action completed without an exception"})
        if page_state.get("error_page"):
            verified = False
            checks.append({"name": "page_error", "status": "failed", "details": "The page appears to be an error state"})
        elif page_state.get("loading_state") == "captcha":
            verified = False
            checks.append({"name": "captcha", "status": "failed", "details": "Captcha detected"})
        return {"verified": verified, "checks": checks}

    def _should_retry(self, action: dict[str, Any], action_type: str, error: Exception) -> bool:
        lowered = str(error).lower()
        return action_type in {"click", "double_click", "right_click", "navigate", "open", "open_url", "fill", "type", "select", "scroll"} and any(term in lowered for term in ["not found", "timeout", "failed", "error", "blocked", "navigation"])

    def _take_screenshot_reference(self, snapshot: dict[str, Any] | None) -> str | None:
        if isinstance(snapshot, dict):
            screenshot = snapshot.get("screenshot")
            if isinstance(screenshot, str) and screenshot:
                return screenshot
        return None

    def _empty_page_state(self) -> dict[str, Any]:
        return {"loading_state": "idle", "navigation_completed": False, "redirect_occurred": False, "login_page": False, "error_page": False, "popup": False, "modal_dialog": False, "cookie_banner": False, "file_download": False, "empty_results": False, "validation_error": False, "rate_limiting": False, "captcha": False, "network_failure": False, "unexpected_page": False, "url": None, "title": None}

    def _build_browser_health(self, state: dict[str, Any], action_logs: list[dict[str, Any]]) -> dict[str, Any]:
        health = state.get("browser_health", {})
        total_actions = len(action_logs)
        successes = health.get("successes", 0)
        failures = health.get("failures", 0)
        retries = health.get("retries", 0)
        recovery_success = health.get("recovery_success", 0)
        if total_actions:
            success_rate = round(successes / total_actions, 2)
            failure_rate = round(failures / total_actions, 2)
        else:
            success_rate = 1.0
            failure_rate = 0.0
        return {
            "success_rate": success_rate,
            "failure_rate": failure_rate,
            "retries": retries,
            "recovery_success": recovery_success,
            "average_action_duration": round(health.get("average_action_duration", 0.0), 3),
            "download_success": health.get("download_success", 0),
            "navigation_success": health.get("navigation_success", 0),
            "timeout_frequency": health.get("timeout_frequency", 0),
        }

    def _update_browser_health(self, state: dict[str, Any], result: dict[str, Any], action_type: str) -> None:
        health = state.setdefault("browser_health", {
            "successes": 0,
            "failures": 0,
            "retries": 0,
            "recovery_success": 0,
            "average_action_duration": 0.0,
            "download_success": 0,
            "navigation_success": 0,
            "timeout_frequency": 0,
        })
        total_actions = max(1, len(state.get("action_history", [])) + 1)
        if result.get("success"):
            health["successes"] += 1
        else:
            health["failures"] += 1
        if result.get("recovery_attempts"):
            health["retries"] += len(result.get("recovery_attempts", []))
            if result.get("status") == "recovered":
                health["recovery_success"] += 1
        if action_type in {"navigate", "open", "open_url"}:
            if result.get("success"):
                health["navigation_success"] += 1
        if action_type == "download" and result.get("success"):
            health["download_success"] += 1
        if "timeout" in str(result.get("error") or "").lower():
            health["timeout_frequency"] += 1
        duration = float(result.get("duration", 0.0) or 0.0)
        health["average_action_duration"] = round(((health.get("average_action_duration", 0.0) * max(0, total_actions - 1)) + duration) / total_actions, 3)

    async def _run_reasoning_loop(self, page: Any, goal: str, context: ExecutionContext, state: dict[str, Any], target_url: str) -> dict[str, Any]:
        if not bool(state.get("goal")):
            return {"observations": [], "pages": [], "sources": [], "action_logs": [], "downloads": [], "latest_snapshot": None, "decision": None}
        observations: list[dict[str, Any]] = []
        pages: list[dict[str, Any]] = []
        sources: list[str] = []
        action_logs: list[dict[str, Any]] = []
        downloads: list[dict[str, Any]] = []
        latest_snapshot = None
        decisions: list[dict[str, Any]] = []
        recovery_attempts: list[dict[str, Any]] = []
        for index in range(2):
            observation = await self.observer.observe(page, goal=goal, include_screenshot=True, screenshot_path=f"browser-observation-{index + 1}.png")
            latest_snapshot = observation
            observations.append(observation)
            pages.append(self._build_page_record(observation.get("raw", {}), {"status": "observed", "url": observation.get("current_url") or target_url}, goal))
            sources.append(observation.get("current_url") or target_url)
            decision = self._choose_next_action(observation, goal, state)
            structured_decision = self.decision_engine.decide(
                goal=goal,
                observation=observation,
                memory=state.get("memory", {}),
                previous_actions=state.get("action_history", []),
                progress={"phase": state.get("current_step", "reasoning"), "step": index + 1},
            )
            decision = {
                **decision,
                "structured_decision": structured_decision,
                "confidence": structured_decision.get("confidence_score", decision.get("confidence", 0.8)),
                "reason": structured_decision.get("reasoning") or decision.get("reason"),
            }
            decisions.append(decision)
            if decision.get("action") in {"stop", "wait"}:
                break
            if decision.get("action") == "recover":
                recovery_attempts.append({"step": index + 1, "issue": decision.get("reason"), "action": "retry"})
            candidate_urls = [target_url]
            links = []
            if hasattr(self.browser_service, "extract_links"):
                try:
                    links = await self.browser_service.extract_links(page)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("Failed to extract links from page: %s", exc)
            candidate_urls.extend(self._rank_links(goal, links, target_url))
            for candidate_url in candidate_urls[1:3]:
                normalized_candidate = str(candidate_url)
                if normalized_candidate in sources:
                    continue
                navigation_result = await self._navigate(page, normalized_candidate)
                action_result = await self._execute_action(page, {"type": "observe", "label": "Observe page", "capture_snapshot": True}, goal, context, state)
                action_logs.append({"action": {"type": "observe", "label": "Observe page"}, "result": action_result})
                if action_result.get("download_path"):
                    downloads.append({"name": action_result.get("download_name") or "download", "path": action_result.get("download_path")})
                if action_result.get("snapshot"):
                    latest_snapshot = action_result["snapshot"]
                    pages.append(self._build_page_record(action_result["snapshot"], navigation_result, goal))
                    sources.append(action_result["snapshot"].get("url") or normalized_candidate)
                    self._remember_page(state, action_result["snapshot"])
                break
            self._remember_page(state, observation)
        state["reasoning_observations"] = observations
        state["reasoning_decisions"] = decisions
        state["recovery_attempts"] = recovery_attempts
        return {"observations": observations, "pages": pages, "sources": sources, "action_logs": action_logs, "downloads": downloads, "latest_snapshot": latest_snapshot, "decision": decisions[-1] if decisions else None}

    def _choose_next_action(self, observation: dict[str, Any], goal: str, state: dict[str, Any]) -> dict[str, Any]:
        primary_action = observation.get("primary_action") or "Inspect page"
        goal_text = (goal or "").casefold()
        confidence = 0.9
        reason = "Observed a clear primary action that aligns with the current goal."
        if goal_text and any(keyword in goal_text for keyword in ["train", "flight", "search", "find"]):
            confidence = 0.95
            reason = "The page exposes a likely search flow and relevant form fields."
        if observation.get("error_messages"):
            confidence = 0.7
            reason = "The page surfaced an error state, so recovery is the next step."
            return {"action": "recover", "confidence": confidence, "reason": reason, "action_payload": {"type": "refresh", "label": "Refresh page"}}
        if observation.get("primary_action") == "Search":
            return {"action": "observe", "confidence": confidence, "reason": reason, "action_payload": {"type": "observe", "label": "Observe search results", "capture_snapshot": True}}
        if observation.get("semantic_roles", {}).get("primary"):
            return {"action": "observe", "confidence": confidence, "reason": reason, "action_payload": {"type": "observe", "label": "Inspect page elements", "capture_snapshot": True}}
        return {"action": "stop", "confidence": confidence, "reason": "The page no longer offers a productive next step.", "action_payload": {"type": "observe", "label": "Finish observation", "capture_snapshot": True}}

    def _remember_page(self, state: dict[str, Any], snapshot: dict[str, Any] | None) -> None:
        memory = state.setdefault("memory", {})
        if not isinstance(snapshot, dict):
            return
        current_url = snapshot.get("current_url") or snapshot.get("url")
        if current_url:
            memory.setdefault("visited_urls", [])
            if current_url not in memory["visited_urls"]:
                memory["visited_urls"].append(current_url)
        if snapshot.get("main_content"):
            memory.setdefault("extracted_information", [])
            memory["extracted_information"].append({"url": current_url, "content": snapshot.get("main_content")[:3]})
        if snapshot.get("current_screenshot"):
            memory.setdefault("previous_screenshots", [])
            memory["previous_screenshots"].append(snapshot["current_screenshot"])
        headings = snapshot.get("headings") or []
        paragraphs = snapshot.get("main_content") or []
        if headings or paragraphs:
            memory.setdefault("structured_facts", [])
            fact = {
                "url": current_url,
                "headings": headings[:3],
                "summary": " ".join(str(item) for item in paragraphs[:3]),
            }
            if fact not in memory["structured_facts"]:
                memory["structured_facts"].append(fact)

    def _build_metadata(
        self,
        goal: str,
        target_url: str,
        pages: list[dict[str, Any]],
        sources: list[str],
        downloads: list[dict[str, Any]],
        screenshot_path: str | None,
        page_states: list[dict[str, Any]],
        action_logs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "goal": goal,
            "report_type": "browser",
            "target_url": target_url,
            "pages": pages,
            "sources": sources,
            "downloads": downloads,
            "screenshot_path": screenshot_path,
            "page_states": page_states,
            "actions_executed": action_logs,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _build_reliability_metrics(self, state: dict[str, Any], pages: list[dict[str, Any]], action_logs: list[dict[str, Any]]) -> dict[str, Any]:
        memory = state.get("memory", {})
        visited_urls = len(memory.get("visited_urls", [])) if isinstance(memory.get("visited_urls"), list) else 0
        completed_actions = len([item for item in action_logs if item.get("result", {}).get("status") not in {"skipped", "unsupported"}])
        return {
            "pages_visited": visited_urls,
            "browser_actions": completed_actions,
            "observation_rounds": len(state.get("reasoning_observations", [])),
            "download_count": len(state.get("memory", {}).get("downloaded_files", [])),
        }

    def _build_page_record(self, snapshot: dict[str, Any], navigation_result: dict[str, Any], goal: str) -> dict[str, Any]:
        url = snapshot.get("url") or snapshot.get("current_url") or navigation_result.get("url") or self._infer_target_url(goal)
        title = snapshot.get("title") or snapshot.get("page_title") or self._derive_title(url)
        if not title and isinstance(snapshot.get("raw"), dict):
            title = snapshot["raw"].get("title") or snapshot["raw"].get("page_title") or self._derive_title(url)
        if not title:
            headings = snapshot.get("headings") or []
            if headings:
                title = headings[0]
        return {
            "title": title,
            "url": url,
            "domain": snapshot.get("domain") or self._derive_domain(url),
            "headings": snapshot.get("headings") or [],
            "paragraphs": snapshot.get("paragraphs") or snapshot.get("main_content") or [],
            "tables": snapshot.get("tables") or [],
            "lists": snapshot.get("lists") or [],
            "links": snapshot.get("links") or [],
            "metadata": snapshot.get("metadata") or {},
            "navigation_status": navigation_result.get("status"),
        }

    def _build_report(
        self,
        goal: str,
        pages: list[dict[str, Any]],
        sources: list[str],
        page_states: list[dict[str, Any]],
        action_logs: list[dict[str, Any]],
    ) -> str:
        lines = [f"# Browser Report: {goal}", "", "## Browser Report", "", "## Summary", "This browser worker inspected the target pages and collected a structured snapshot.", ""]
        if page_states:
            lines.append("## Page snapshots")
            for index, page in enumerate(page_states[:3], start=1):
                lines.append(f"### Snapshot {index}: {page.get('title')}")
                lines.append(f"- URL: {page.get('url')}")
                lines.append(f"- Headings: {', '.join(page.get('headings', [])[:3]) or 'None'}")
                lines.append(f"- Paragraph count: {len(page.get('paragraphs', []))}")
                lines.append("")
        if action_logs:
            lines.append("## Action log")
            for action in action_logs:
                lines.append(f"- {action['action'].get('label') or action['action'].get('type')}: {action['result'].get('status')}")
            lines.append("")
        if sources:
            lines.append("## Sources")
            for source in sources[:5]:
                lines.append(f"- {source}")
            lines.append("")
        return "\n".join(lines)

    def _infer_target_url(self, goal: str) -> str:
        normalized = (goal or "").casefold()
        if "pricing" in normalized or "compare" in normalized:
            return "https://example.com"
        return "https://example.com"

    def _rank_links(self, goal: str, links: list[dict[str, str]], primary_url: str) -> list[str]:
        normalized_goal = (goal or "").casefold()
        scored: list[tuple[int, str]] = []
        for link in links:
            href = link.get("href") or ""
            if not href:
                continue
            score = 0
            if any(term in href.casefold() for term in ["pricing", "features", "compare", "report"]):
                score += 30
            if any(term in normalized_goal for term in ["pricing", "compare", "features"]):
                score += 20
            if href.casefold() != primary_url.casefold():
                score += 10
            scored.append((score, href))
        scored.sort(key=lambda item: item[0], reverse=True)
        unique_urls: list[str] = []
        seen: set[str] = set()
        for _, href in scored:
            if href in seen:
                continue
            seen.add(href)
            unique_urls.append(href)
        return unique_urls[:3]

    async def _emit_progress(self, context: ExecutionContext, stage_id: str, label: str, progress: int) -> None:
        event = {"type": "progress", "stage_id": stage_id, "label": label, "progress": progress}
        event_bus = context.metadata.get("event_bus") if isinstance(context.metadata, dict) else None
        if event_bus is not None and hasattr(event_bus, "publish"):
            event_bus.publish(context.session.id, event)
        callback = context.metadata.get("progress_callback") if isinstance(context.metadata, dict) else None
        if callable(callback):
            result = callback(event)
            if hasattr(result, "__await__"):
                await result

    def _update_state(self, context: ExecutionContext, state: dict[str, Any], current_step: str, activity: str, progress: int, *, current_url: str | None = None) -> None:
        state["current_step"] = current_step
        state["activity"] = activity
        state["progress"] = progress
        if current_url is not None:
            state["current_url"] = current_url
        state["session_state"] = self.browser_service.get_session_state()
        state["logs"].append({"step": current_step, "activity": activity, "progress": progress, "timestamp": datetime.now(timezone.utc).isoformat()})
        context.session.metadata["browser_state"] = state
        context.metadata["browser_state"] = state

    def _append_timeline(self, state: dict[str, Any], action: dict[str, Any], result: dict[str, Any], snapshot: dict[str, Any] | None, duration: float) -> None:
        state["timeline"].append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "result": result,
                "url": (snapshot or {}).get("url") if isinstance(snapshot, dict) else state.get("current_url"),
                "screenshot": state.get("latest_screenshot"),
                "duration": duration,
            }
        )
        state["action_history"].append({"action": action.get("type"), "status": result.get("status")})

    def _requires_approval(self, action: dict[str, Any], state: dict[str, Any]) -> bool:
        if bool(action.get("requires_approval")):
            return True
        dangerous_actions = {"purchase", "payment", "delete", "send_email", "submit", "account_change"}
        action_type = str(action.get("type", "")).casefold()
        if action_type in dangerous_actions:
            return True
        if action.get("dangerous"):
            return True
        return False

    def _derive_domain(self, url: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc or "example.com"

    def _derive_title(self, url: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return parsed.netloc or "Browser page"
