from .models import PlanStep


class RiskAnalyzer:
    _approval_intents = {"booking", "purchasing", "communication"}
    _approval_terms = ("send", "book", "purchase", "buy", "delete", "cancel", "publish", "post", "submit", "transfer")

    def analyze(self, goal: str, intent: str, steps: list[PlanStep]) -> tuple[bool, str | None]:
        normalized = goal.casefold()
        requires_approval = intent in self._approval_intents or any(term in normalized for term in self._approval_terms)
        if not requires_approval:
            return False, None
        reason = "This request may create an external side effect. Synzept will pause before sending, booking, purchasing, or changing data."
        for step in steps:
            if step.title in {"Request approval", "Complete the booking"} or intent in self._approval_intents and step.id == "step_3":
                step.requires_approval = True
                step.status = "waiting_approval"
        return True, reason
