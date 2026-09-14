from __future__ import annotations

from typing import Any


class ApprovalEngine:
    """Determines whether an action requires approval before execution continues."""

    def evaluate(self, *, goal: str | None = None, action_type: str | None = None, details: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized_goal = (goal or "").casefold()
        normalized_action = (action_type or "").casefold()
        operation = str((details or {}).get("operation") or "").casefold()
        requires_approval = False
        reason = None
        sensitive_operations = {"send", "reply", "reply_all", "forward", "delete", "purchase", "payment", "book", "share", "submit"}
        sensitive_keywords = ["pay", "payment", "purchase", "buy", "delete", "submit", "credential", "book", "share"]
        attendees = (details or {}).get("attendees") or []
        multi_attendee_change = operation in {"update", "move", "change", "reschedule"} and isinstance(attendees, list) and len(attendees) > 1
        if operation in sensitive_operations or any(keyword in normalized_goal or keyword in normalized_action for keyword in sensitive_keywords) or multi_attendee_change:
            requires_approval = True
            reason = "The requested action involves a sensitive or irreversible operation."
        if normalized_action in {"payment", "purchase", "delete", "submit", "signin", "send", "reply", "forward", "share"} or multi_attendee_change:
            requires_approval = True
            reason = "This action changes state and should be approved before it proceeds."
        return {"requires_approval": requires_approval, "reason": reason, "action_type": action_type, "goal": goal}
