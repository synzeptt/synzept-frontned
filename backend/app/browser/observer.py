from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PageObserver:
    """Convert raw browser page state into a structured, goal-aware snapshot."""

    def __init__(self, browser_service: Any | None = None) -> None:
        self.browser_service = browser_service

    async def observe(self, page: Any, *, goal: str | None = None, include_screenshot: bool = False, screenshot_path: str | None = None) -> dict[str, Any]:
        if self.browser_service is not None and hasattr(self.browser_service, "observe_page"):
            snapshot = await self.browser_service.observe_page(page, goal=goal, include_screenshot=include_screenshot, screenshot_path=screenshot_path)
        else:
            snapshot = {
                "url": getattr(page, "url", None),
                "title": None,
                "visible_text": None,
                "buttons": [],
                "links": [],
                "forms": [],
                "inputs": [],
                "tables": [],
                "dialogs": [],
                "errors": [],
                "navigation_state": {"loaded": False},
                "screenshot": screenshot_path,
                "headings": [],
                "paragraphs": [],
                "lists": [],
                "metadata": {},
                "structure": {},
            }

        headings = list(snapshot.get("headings") or [])
        paragraphs = list(snapshot.get("paragraphs") or [])
        buttons = list(snapshot.get("buttons") or [])
        links = list(snapshot.get("links") or [])
        forms = list(snapshot.get("forms") or [])
        inputs = list(snapshot.get("inputs") or [])
        tables = list(snapshot.get("tables") or [])
        dialogs = list(snapshot.get("dialogs") or [])
        errors = list(snapshot.get("errors") or [])
        visible_text = snapshot.get("visible_text") or " ".join(paragraphs)

        primary_action = self._infer_primary_action(goal, buttons, links, inputs, headings, visible_text)
        secondary_actions = self._infer_secondary_actions(buttons, links, inputs, goal)
        detected_form = self._infer_form_name(forms, headings, inputs, goal)
        required_fields = self._infer_required_fields(inputs, goal)
        detected_results = self._infer_results(paragraphs, headings, visible_text, goal)
        navigation_menus = self._infer_navigation_menus(links)
        loading_state = self._infer_loading_state(snapshot, visible_text, errors)
        semantic_roles = self._infer_semantic_roles(buttons, links, inputs, goal)

        return {
            "current_url": snapshot.get("url"),
            "page_title": snapshot.get("title") or "Untitled page",
            "headings": headings,
            "main_content": paragraphs[:8],
            "buttons": buttons,
            "links": links,
            "forms": forms,
            "input_fields": inputs,
            "tables": tables,
            "navigation_menus": navigation_menus,
            "dialogs": dialogs,
            "error_messages": errors,
            "loading_state": loading_state,
            "current_screenshot": snapshot.get("screenshot"),
            "semantic_roles": semantic_roles,
            "summary": self._build_summary(
                goal=goal,
                primary_action=primary_action,
                secondary_actions=secondary_actions,
                detected_form=detected_form,
                required_fields=required_fields,
                detected_results=detected_results,
            ),
            "primary_action": primary_action,
            "secondary_actions": secondary_actions,
            "detected_form": detected_form,
            "required_fields": required_fields,
            "detected_results": detected_results,
            "metadata": snapshot.get("metadata") or {},
            "structure": snapshot.get("structure") or {},
            "raw": snapshot,
        }

    def _infer_primary_action(self, goal: str | None, buttons: list[Any], links: list[Any], inputs: list[Any], headings: list[str], visible_text: str) -> str:
        goal_text = (goal or "").casefold()
        candidates = []
        for button in buttons:
            text = str(button).casefold()
            if any(keyword in text for keyword in ["search", "find", "go", "continue", "submit", "login", "sign in", "register", "view"]):
                candidates.append(text)
        for link in links:
            text = str(link.get("text") if isinstance(link, dict) else link).casefold()
            if any(keyword in text for keyword in ["search", "find", "login", "register", "continue", "view"]):
                candidates.append(text)
        if candidates:
            return max(candidates, key=len).strip().title()
        if any(keyword in goal_text for keyword in ["search", "find", "train", "flight", "laptop"]):
            return "Search"
        if inputs:
            return "Fill form"
        return "Inspect page"

    def _infer_secondary_actions(self, buttons: list[Any], links: list[Any], inputs: list[Any], goal: str | None) -> list[str]:
        actions = []
        for button in buttons:
            text = str(button).strip()
            if text and text.casefold() not in {action.casefold() for action in actions}:
                actions.append(text)
        for link in links:
            text = str(link.get("text") if isinstance(link, dict) else link).strip()
            if text and text.casefold() not in {action.casefold() for action in actions}:
                actions.append(text)
        if inputs:
            actions.append("Enter input")
        if goal and "login" in goal.casefold():
            actions.append("Login")
        return actions[:6]

    def _infer_form_name(self, forms: list[Any], headings: list[str], inputs: list[Any], goal: str | None) -> str | None:
        if forms:
            return str(forms[0])
        if headings:
            return headings[0]
        if inputs and goal and any(keyword in goal.casefold() for keyword in ["train", "flight", "search", "form"]):
            return "Search form"
        return None

    def _infer_required_fields(self, inputs: list[Any], goal: str | None) -> list[str]:
        required = []
        for field in inputs:
            value = str(field).strip()
            if not value:
                continue
            lower = value.casefold()
            if any(keyword in lower for keyword in ["from", "to", "date", "time", "search", "query", "name", "email", "password"]):
                required.append(value)
        if goal and "train" in goal.casefold():
            required.extend(["From", "To", "Date"])
        return list(dict.fromkeys(required))[:6]

    def _infer_results(self, paragraphs: list[str], headings: list[str], visible_text: str, goal: str | None) -> list[str]:
        results = []
        for item in paragraphs[:3]:
            if item and len(item) > 5:
                results.append(item)
        if not results and visible_text:
            results.append(visible_text[:180])
        if not results and headings:
            results.extend(headings[:2])
        return results[:4]

    def _infer_navigation_menus(self, links: list[Any]) -> list[str]:
        menus = []
        for link in links:
            text = str(link.get("text") if isinstance(link, dict) else link).strip()
            if text and any(keyword in text.casefold() for keyword in ["home", "about", "contact", "pricing", "blog", "shop", "menu"]):
                menus.append(text)
        return menus[:6]

    def _infer_loading_state(self, snapshot: dict[str, Any], visible_text: str, errors: list[Any]) -> str:
        nav_state = snapshot.get("navigation_state") or {}
        loaded = nav_state.get("loaded") if isinstance(nav_state, dict) else False
        if errors:
            return "error"
        if loaded:
            return "ready"
        if visible_text:
            return "partial"
        return "loading"

    def _infer_semantic_roles(self, buttons: list[Any], links: list[Any], inputs: list[Any], goal: str | None) -> dict[str, list[str]]:
        roles = {"primary": [], "secondary": []}
        for button in buttons:
            text = str(button).strip()
            if text:
                roles["primary"].append(text)
        for link in links:
            text = str(link.get("text") if isinstance(link, dict) else link).strip()
            if text:
                roles["secondary"].append(text)
        if inputs:
            roles["secondary"].append("input")
        if goal and "login" in goal.casefold():
            roles["primary"].append("login")
        return roles

    def _build_summary(self, *, goal: str | None, primary_action: str, secondary_actions: list[str], detected_form: str | None, required_fields: list[str], detected_results: list[str]) -> str:
        lines = [f"Primary Action: {primary_action}", ""]
        if secondary_actions:
            lines.append("Secondary Actions:")
            lines.extend(f"- {action}" for action in secondary_actions[:4])
            lines.append("")
        if detected_form:
            lines.append(f"Detected Form: {detected_form}")
        if required_fields:
            lines.append("Required Fields:")
            lines.extend(f"- {field}" for field in required_fields)
        if detected_results:
            lines.append("Detected Results:")
            lines.extend(f"- {result}" for result in detected_results[:3])
        return "\n".join(lines)
