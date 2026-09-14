from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Iterable


class WebsiteAdapter(ABC):
    """Reusable website adapter for the existing browser automation stack."""

    name: str = "generic"
    keywords: tuple[str, ...] = ()
    capability: str = "browser"
    registry: ClassVar[list[type["WebsiteAdapter"]]] = []

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.registry.append(cls)

    def initialize(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"adapter": self.name, "status": "initialized", "payload": payload or {}}

    def login(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"adapter": self.name, "status": "login_skipped", "payload": payload or {}}

    def check_login(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"adapter": self.name, "status": "logged_in", "payload": payload or {}}

    def navigate(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"adapter": self.name, "status": "navigated", "payload": payload or {}}

    def execute_action(self, operation: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        return [
            {"type": "goto", "url": payload.get("url") or "https://example.com"},
            {"type": "wait", "seconds": 0.1},
            {"type": "verify", "check": "page_loaded"},
        ]

    def verify(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"adapter": self.name, "verified": True, "checks": [{"name": "default", "status": "passed", "details": "Verification complete"}]}

    def capture_artifacts(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"adapter": self.name, "artifacts": []}

    def cleanup(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"adapter": self.name, "status": "cleaned_up", "payload": payload or {}}

    def requires_approval(self, operation: str, payload: dict[str, Any] | None = None) -> bool:
        return False

    def detect_operation(self, goal: str, payload: dict[str, Any] | None = None) -> str:
        return "browse"

    def matches(self, goal: str) -> bool:
        normalized = (goal or "").casefold()
        return any(keyword in normalized for keyword in self.keywords)

    def build_actions(self, goal: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        operation = self.detect_operation(goal, payload)
        return self.execute_action(operation, payload or {})


class FormEngine:
    """Reusable form automation engine with no website-specific selectors."""

    def analyze_form(self, fields: Iterable[dict[str, Any]] | dict[str, Any] | None) -> list[dict[str, Any]]:
        if isinstance(fields, dict):
            return [{"name": key, "type": self._infer_type(key, value)} for key, value in fields.items()]
        return [{"name": str(field.get("name") or field.get("id") or "field"), "type": self._infer_type(field.get("name") or field.get("id") or "", field.get("value"))} for field in fields or []]

    def infer_field_purpose(self, field_name: str) -> str:
        lowered = field_name.casefold()
        if "email" in lowered:
            return "email"
        if "name" in lowered:
            return "name"
        if "phone" in lowered or "mobile" in lowered:
            return "phone"
        if "address" in lowered:
            return "address"
        if "file" in lowered or "resume" in lowered or "cover" in lowered:
            return "file"
        if "message" in lowered or "comment" in lowered:
            return "message"
        if "date" in lowered:
            return "date"
        return "text"

    def map_fields(self, fields: Iterable[dict[str, Any]] | dict[str, Any] | None, values: dict[str, Any]) -> list[dict[str, Any]]:
        analyzed = self.analyze_form(fields)
        return [{"name": field["name"], "purpose": self.infer_field_purpose(field["name"]), "value": values.get(field["name"], ""), "type": field["type"]} for field in analyzed]

    def fill_form(self, fields: Iterable[dict[str, Any]] | dict[str, Any] | None, values: dict[str, Any]) -> list[dict[str, Any]]:
        mapped = self.map_fields(fields, values)
        actions: list[dict[str, Any]] = []
        for field in mapped:
            if field["type"] == "file":
                actions.append({"type": "upload", "selector": f"input[name={field['name']}]", "file_path": str(field.get("value") or "")})
            else:
                actions.append({"type": "fill", "selector": f"input[name={field['name']}]", "value": str(field.get("value") or "")})
        return actions

    def validate(self, fields: Iterable[dict[str, Any]] | dict[str, Any] | None, values: dict[str, Any]) -> bool:
        return bool(self.map_fields(fields, values))

    def submit(self) -> list[dict[str, Any]]:
        return [{"type": "click", "selector": "button[type=submit]"}, {"type": "verify", "check": "page_loaded"}]

    def _infer_type(self, field_name: str, value: Any) -> str:
        lowered = (field_name or "").casefold()
        if "file" in lowered or "resume" in lowered or "cover" in lowered:
            return "file"
        if isinstance(value, bool):
            return "checkbox"
        return "text"


class WebsiteAdapterRegistry:
    def __init__(self) -> None:
        self.adapters: list[WebsiteAdapter] = []
        for adapter_cls in WebsiteAdapter.registry:
            self.register(adapter_cls())

    def register(self, adapter: WebsiteAdapter) -> WebsiteAdapter:
        if adapter not in self.adapters:
            self.adapters.append(adapter)
        return adapter

    def resolve(self, goal: str) -> WebsiteAdapter | None:
        normalized_goal = (goal or "").casefold()
        scored: list[tuple[tuple[int, int, int], WebsiteAdapter]] = []
        for adapter in self.adapters:
            score = sum(1 for keyword in adapter.keywords if keyword in normalized_goal)
            explicit_brand_bonus = 1 if adapter.name in normalized_goal else 0
            if score or explicit_brand_bonus:
                scored.append(((score, explicit_brand_bonus, 1), adapter))
        if not scored:
            return None
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]

    def resolve_by_name(self, name: str) -> WebsiteAdapter | None:
        for adapter in self.adapters:
            if adapter.name == name:
                return adapter
        return None


class IRCTCAdapter(WebsiteAdapter):
    name = "irctc"
    keywords = ("irctc", "train", "rail", "mumbai", "delhi")

    def detect_operation(self, goal: str, payload: dict[str, Any] | None = None) -> str:
        lowered = (goal or "").casefold()
        if any(keyword in lowered for keyword in ("find", "search", "availability", "check", "availability")):
            return "search_trains"
        return "book_train"

    def execute_action(self, operation: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        actions = [
            {"type": "goto", "url": "https://www.irctc.co.in/nget/train-search"},
            {"type": "wait_for_navigation"},
            {"type": "verify", "check": "text_exists", "text": "IRCTC"},
            {"type": "fill", "selector": "input[name=source]", "value": str(payload.get("source") or "")},
            {"type": "fill", "selector": "input[name=destination]", "value": str(payload.get("destination") or "")},
            {"type": "fill", "selector": "input[name=date]", "value": str(payload.get("date") or "")},
            {"type": "click", "selector": "button[type=submit]"},
            {"type": "verify", "check": "text_exists", "text": "Trains"},
        ]
        if operation in {"review_booking", "book_train"}:
            actions.append({"type": "verify", "check": "text_exists", "text": "Review"})
        return actions

    def requires_approval(self, operation: str, payload: dict[str, Any] | None = None) -> bool:
        return operation in {"book_train", "review_booking", "pay"}

    def capture_artifacts(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        return {"adapter": self.name, "artifacts": [{"type": "confirmation", "id": payload.get("pnr") or "ticket-1", "url": payload.get("url")}]}


class LinkedInAdapter(WebsiteAdapter):
    name = "linkedin"
    keywords = ("linkedin", "job", "apply")

    def detect_operation(self, goal: str, payload: dict[str, Any] | None = None) -> str:
        lowered = (goal or "").casefold()
        if "easy" in lowered:
            return "easy_apply"
        if any(keyword in lowered for keyword in ("search", "find", "browse", "look")):
            return "search_jobs"
        return "apply_job"

    def execute_action(self, operation: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        if operation == "search_jobs":
            return [
                {"type": "goto", "url": "https://www.linkedin.com/jobs"},
                {"type": "wait_for_navigation"},
                {"type": "verify", "check": "text_exists", "text": "Jobs"},
            ]
        return [
            {"type": "goto", "url": "https://www.linkedin.com/jobs"},
            {"type": "wait_for_navigation"},
            {"type": "verify", "check": "text_exists", "text": "Jobs"},
            {"type": "click", "selector": "button:has-text('Easy Apply')"},
            {"type": "upload", "selector": "input[type=file]", "file_path": str(payload.get("resume_path") or "resume.pdf")},
            {"type": "verify", "check": "text_exists", "text": "Review"},
        ]

    def requires_approval(self, operation: str, payload: dict[str, Any] | None = None) -> bool:
        return operation in {"apply_job", "easy_apply", "submit_application"}


class GitHubAdapter(WebsiteAdapter):
    name = "github"
    keywords = ("github", "repository", "issue", "pull request", "pr")

    def detect_operation(self, goal: str, payload: dict[str, Any] | None = None) -> str:
        if "issue" in (goal or "").casefold():
            return "create_issue"
        if "pull" in (goal or "").casefold() or "pr" in (goal or "").casefold():
            return "create_pull_request"
        if "repo" in (goal or "").casefold() or "repository" in (goal or "").casefold():
            return "create_repository"
        return "create_repository"

    def execute_action(self, operation: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        actions = [
            {"type": "goto", "url": "https://github.com"},
            {"type": "wait_for_navigation"},
            {"type": "verify", "check": "text_exists", "text": "GitHub"},
        ]
        if operation == "create_repository":
            actions.extend([
                {"type": "click", "selector": "a[href='/new' ]"},
                {"type": "fill", "selector": "input[name='repository[name]']", "value": str(payload.get("name") or "demo")},
                {"type": "click", "selector": "button[type=submit]"},
            ])
        elif operation == "create_issue":
            actions.extend([
                {"type": "fill", "selector": "input[name='title']", "value": str(payload.get("title") or "Issue")},
                {"type": "click", "selector": "button[type=submit]"},
            ])
        return actions

    def requires_approval(self, operation: str, payload: dict[str, Any] | None = None) -> bool:
        return operation in {"merge_pull_request", "delete_repository"}


class GmailWebAdapter(WebsiteAdapter):
    name = "gmail"
    keywords = ("gmail", "mail", "email", "reply")

    def detect_operation(self, goal: str, payload: dict[str, Any] | None = None) -> str:
        if "reply" in (goal or "").casefold() or "respond" in (goal or "").casefold():
            return "reply"
        return "open_inbox"

    def execute_action(self, operation: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        actions = [
            {"type": "goto", "url": "https://mail.google.com"},
            {"type": "wait_for_navigation"},
            {"type": "verify", "check": "text_exists", "text": "Gmail"},
        ]
        if operation == "reply":
            actions.extend([
                {"type": "click", "selector": "button[aria-label='Reply']"},
                {"type": "fill", "selector": "div[role='textbox']", "value": str(payload.get("body") or "")},
                {"type": "click", "selector": "div[aria-label='Send']"},
            ])
        return actions

    def requires_approval(self, operation: str, payload: dict[str, Any] | None = None) -> bool:
        return operation in {"reply", "send", "draft"}


class GoogleFormsAdapter(WebsiteAdapter):
    name = "google_forms"
    keywords = ("google form", "form", "forms")

    def __init__(self, form_engine: FormEngine | None = None) -> None:
        self.form_engine = form_engine or FormEngine()

    def detect_operation(self, goal: str, payload: dict[str, Any] | None = None) -> str:
        return "fill_form"

    def execute_action(self, operation: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        fields = payload.get("fields") or {}
        values = payload.get("values") or {}
        if hasattr(self.form_engine, "fill_form"):
            actions = self.form_engine.fill_form(fields, values)
        else:
            mapped = self.form_engine.map_fields(fields, values)
            actions = [
                {"type": "fill", "selector": f"input[name={field['name']}]", "value": str(field.get("value") or "")}
                for field in mapped
            ]
        if hasattr(self.form_engine, "submit"):
            submitted = self.form_engine.submit()
            if submitted:
                actions.extend(submitted)
        else:
            actions.append({"type": "submit"})
            actions.append({"type": "verify", "check": "page_loaded"})
        return actions


class IndeedAdapter(WebsiteAdapter):
    name = "indeed"
    keywords = ("indeed", "job")

    def detect_operation(self, goal: str, payload: dict[str, Any] | None = None) -> str:
        return "apply"

    def execute_action(self, operation: str, payload: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = payload or {}
        return [
            {"type": "goto", "url": "https://www.indeed.com"},
            {"type": "wait_for_navigation"},
            {"type": "verify", "check": "text_exists", "text": "Indeed"},
            {"type": "upload", "selector": "input[type=file]", "file_path": str(payload.get("resume_path") or "resume.pdf")},
            {"type": "click", "selector": "button[type=submit]"},
        ]

    def requires_approval(self, operation: str, payload: dict[str, Any] | None = None) -> bool:
        return operation in {"apply", "submit"}


default_registry = WebsiteAdapterRegistry()

__all__ = [
    "FormEngine",
    "WebsiteAdapter",
    "WebsiteAdapterRegistry",
    "IRCTCAdapter",
    "LinkedInAdapter",
    "GitHubAdapter",
    "GmailWebAdapter",
    "GoogleFormsAdapter",
    "IndeedAdapter",
    "default_registry",
]
