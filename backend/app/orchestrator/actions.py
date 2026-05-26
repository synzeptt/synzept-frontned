"""Action suggestions — supportive, never autonomous."""

import re

from app.orchestrator.types import ActionSuggestion, ClassifiedIntent, IntentCategory


class ActionAdvisor:
    """Suggest optional next steps after a response. User must confirm any action."""

    @staticmethod
    def suggest(
        intent: ClassifiedIntent,
        user_message: str,
        assistant_reply: str,
    ) -> list[ActionSuggestion]:
        suggestions: list[ActionSuggestion] = []
        lower = user_message.lower()

        if intent.category == IntentCategory.PLANNING:
            suggestions.append(
                ActionSuggestion(
                    type="task",
                    label="Turn plan into tasks",
                    description="I can help break this into actionable tasks if you'd like.",
                )
            )

        if intent.category == IntentCategory.DECISION_SUPPORT:
            suggestions.append(
                ActionSuggestion(
                    type="prioritize",
                    label="Compare options",
                    description="Say if you want a structured comparison or recommendation.",
                )
            )

        if intent.category == IntentCategory.ORGANIZATION:
            suggestions.append(
                ActionSuggestion(
                    type="prioritize",
                    label="Review priorities",
                    description="Ask for a priority review of your current tasks.",
                )
            )

        if intent.category == IntentCategory.BRAINSTORMING and len(assistant_reply) > 400:
            suggestions.append(
                ActionSuggestion(
                    type="note",
                    label="Save key ideas",
                    description="Say 'save a note' to capture the best ideas from this thread.",
                )
            )

        if intent.category == IntentCategory.PROJECT_CONTINUE:
            suggestions.append(
                ActionSuggestion(
                    type="plan",
                    label="Update project plan",
                    description="Continue refining this project or add tasks for next steps.",
                )
            )

        # Proactive but light — only when reply mentions open items
        if re.search(r"\b(next step|follow up|unfinished|pending|should)\b", assistant_reply.lower()):
            if not suggestions:
                suggestions.append(
                    ActionSuggestion(
                        type="review",
                        label="Review open work",
                        description="Ask for a briefing or priority check when ready.",
                    )
                )

        return suggestions[:2]

    @staticmethod
    def explicit_task_requested(message: str) -> bool:
        lower = message.lower()
        return any(
            p in lower
            for p in ("create task", "add task", "new task", "todo:", "remind me to")
        )
