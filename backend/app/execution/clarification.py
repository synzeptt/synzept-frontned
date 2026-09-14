from __future__ import annotations

import re
from typing import Any


class ClarificationEngine:
    """Detects missing input for a goal and asks only the next best question."""

    def analyze(self, *, goal: str | None = None, existing_answers: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = (goal or "").strip().casefold()
        answers = dict(existing_answers or {})
        missing_fields: list[str] = []

        if "train" in normalized:
            departure_city = self._extract_departure_city(goal)
            destination = self._extract_destination(goal)
            if departure_city:
                answers["departure_city"] = departure_city
            if destination:
                answers["destination"] = destination
            if "date" not in answers:
                date = self._extract_date(goal)
                if date:
                    answers["date"] = date

            if "destination" not in answers and re.search(r"\bto\b", goal or "", re.IGNORECASE):
                answers["destination"] = "destination"
            if "departure_city" not in answers and re.search(r"\bfrom\b", goal or "", re.IGNORECASE):
                answers["departure_city"] = "departure city"

            if "destination" not in answers:
                missing_fields.append("destination")

        if "meeting" in normalized or "schedule" in normalized or "calendar" in normalized:
            time_value = self._extract_time(goal)
            if time_value:
                answers["time"] = time_value
            if "date" not in answers:
                date = self._extract_date(goal)
                if date:
                    answers["date"] = date

        if "book" in normalized and "date" not in answers and "tomorrow" not in normalized and "today" not in normalized and "next" not in normalized:
            missing_fields.append("date")
        if "meeting" in normalized and "time" not in answers and "time" not in normalized and "next tuesday" in normalized and "time" not in missing_fields:
            missing_fields.append("time")
        if "schedule" in normalized and "time" not in answers and "time" not in normalized and any(phrase in normalized for phrase in ["next tuesday", "tomorrow", "this afternoon", "this morning", "tonight", "this evening", "today"]) and "time" not in missing_fields:
            missing_fields.append("time")

        next_question = None
        if missing_fields:
            field = missing_fields[0]
            next_question = self._question_for(field)

        return {
            "goal": goal,
            "needs_clarification": bool(missing_fields),
            "missing_fields": missing_fields,
            "existing_answers": answers,
            "next_question": next_question,
            "resume_after_answer": True,
        }

    def _question_for(self, field: str) -> str:
        prompts = {
            "destination": "Destination: Where are you travelling to?",
            "departure_city": "Departure city: Which city are you departing from?",
            "departure city": "Departure city: Which city are you departing from?",
            "date": "Date: What date should I use?",
            "passenger": "Passenger count: How many passengers should I include?",
        }
        return prompts.get(field, prompts.get(field.replace("_", " "), f"Can you provide the missing value for {field}?"))

    def _extract_departure_city(self, goal: str | None) -> str | None:
        if not goal:
            return None
        match = re.search(r"from\s+([a-zA-Z][a-zA-Z\s]+?)(?=\s+to\s+)", goal, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_destination(self, goal: str | None) -> str | None:
        if not goal:
            return None
        match = re.search(r"to\s+([a-zA-Z][a-zA-Z\s]+?)(?=\s+(?:tomorrow|today|next|for|on|$))", goal, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _extract_date(self, goal: str | None) -> str | None:
        if not goal:
            return None
        normalized = goal.casefold()
        if "tomorrow" in normalized:
            return "tomorrow"
        if "today" in normalized:
            return "today"
        if "next week" in normalized:
            return "next week"
        return None

    def _extract_time(self, goal: str | None) -> str | None:
        if not goal:
            return None
        match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", goal, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = match.group(2) or "00"
            suffix = match.group(3).lower()
            return f"{hour}:{minute} {suffix}"
        return None
