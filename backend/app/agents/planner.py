from __future__ import annotations

import re

from app.agents.models import AgentRuntimeState
from app.skills.registry import default_registry


class Planner:
    def plan(self, agent: AgentRuntimeState) -> dict:
        objective = getattr(agent, "objective", "") or ""
        lowered = objective.casefold()

        candidates = [
            ("calendar", 0.0, "create_event", ["google_calendar"], {"title": "Meeting", "date": "tomorrow", "time": "3 PM", "attendees": ["rahul"]}, False),
            ("email", 0.0, "draft_email", ["gmail"], {"subject": "Re: message", "recipient": "customer"}, False),
            ("document", 0.0, "create_document", ["google_docs", "google_drive"], {"title": objective, "format": "doc"}, False),
            ("spreadsheet", 0.0, "create_spreadsheet", ["google_sheets", "google_drive"], {"title": objective, "dataset": "sales"}, False),
            ("presentation", 0.0, "create_presentation", ["google_slides", "google_drive"], {"title": objective, "slides": 8}, False),
            ("travel", 0.0, "book_train", ["browser"], {"destination": objective}, True),
            ("browser", 0.0, "browse", ["browser"], {"query": objective}, True),
            ("research", 0.0, "research", ["browser"], {"query": objective}, False),
        ]

        classification_scores = {skill: 0.0 for skill, _, _, _, _, _ in candidates}

        def add_score(skill: str, score: float) -> None:
            classification_scores[skill] = max(classification_scores.get(skill, 0.0), round(score, 2))

        def contains_any(*tokens: str) -> bool:
            return any(re.search(rf"\b{re.escape(token)}\b", lowered) for token in tokens)

        def extract_browser_plan() -> tuple[str, str, dict, bool]:
            website = "generic"
            intent = "browse"
            parameters: dict[str, object] = {"query": objective}
            approval_required = False

            if contains_any("linkedin"):
                website = "linkedin"
                intent = "search_linkedin" if contains_any("search", "find", "look") else "apply_job"
                parameters = {"query": objective}
                approval_required = False
            elif contains_any("github"):
                website = "github"
                intent = "create_repository"
                parameters = {"name": objective.split()[-1] if objective.split() else "demo"}
            elif contains_any("google form", "form"):
                website = "google_forms"
                intent = "fill_form"
                parameters = {"fields": {}, "values": {}}
                approval_required = False
            elif contains_any("indeed"):
                website = "indeed"
                intent = "apply_job"
                approval_required = True
            elif contains_any("gmail", "mail", "email"):
                website = "gmail"
                intent = "reply" if contains_any("reply", "respond") else "open_inbox"
                approval_required = False
            elif contains_any("train") and contains_any("book", "reserve", "buy"):
                website = "irctc"
                intent = "book_train"
                approval_required = True
                source_match = re.search(r"from\s+(.+?)\s+to\s+(.+?)(?=\s+(?:tomorrow|today|next|for|on|$))", objective, re.IGNORECASE)
                date_match = re.search(r"\b(tomorrow|today|next week|next monday|next tuesday|next wednesday|next thursday|next friday|next sunday|next saturday|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", objective, re.IGNORECASE)
                parameters = {
                    "source": source_match.group(1).strip() if source_match else "Mumbai",
                    "destination": source_match.group(2).strip() if source_match else "Delhi",
                    "date": date_match.group(1).strip().lower() if date_match else "tomorrow",
                }
            elif contains_any("upload", "download", "website", "open", "browser"):
                website = "generic"
                intent = "browse"
                parameters = {"query": objective}

            return website, intent, parameters, approval_required

        if contains_any("research", "compare", "analysis", "analyze", "findings", "latest ai models", "latest models", "model", "models"):
            add_score("research", 0.92)

        has_calendar_intent = (
            contains_any("calendar", "event", "appointment", "invite", "google meet", "standup", "conference", "video call")
            or (
                contains_any("schedule", "book", "arrange", "set up", "plan", "create")
                and contains_any("meeting", "call")
            )
        )
        has_travel_intent = contains_any("train", "ticket", "travel", "hotel", "flight", "itinerary", "trip")
        has_document_intent = contains_any("proposal", "document", "doc", "write report", "brief", "notes", "report", "proposal outline")
        has_spreadsheet_intent = contains_any("spreadsheet", "dashboard", "tracker", "kpi", "metrics", "financial", "pipeline", "sheet") or (
            contains_any("sales") and contains_any("spreadsheet", "sheet")
        )
        has_presentation_intent = contains_any("presentation", "deck", "slides", "pitch", "roadmap", "demo")
        has_email_intent = contains_any("email", "mail", "reply", "respond", "inbox", "message", "follow-up", "outreach", "customer")
        has_browser_intent = contains_any("fill", "form", "apply", "linkedin", "github", "login", "website", "browser", "upload", "download", "open") or (
            contains_any("train", "rail", "railway", "irctc") and contains_any("book", "reserve", "buy")
        ) or (
            contains_any("train", "rail", "railway", "irctc") and contains_any("availability", "find", "search", "look", "check")
        )

        if has_calendar_intent:
            add_score("calendar", 0.98)
        if contains_any("tomorrow", "today", "next monday", "next week", "monday", "tuesday", "wednesday", "thursday", "friday", "weekend", "afternoon", "morning", "pm", "am") and not has_travel_intent:
            add_score("calendar", 0.97)

        if has_email_intent and not has_presentation_intent and not has_spreadsheet_intent and not has_browser_intent:
            add_score("email", 0.95)
        if contains_any("draft") and not has_presentation_intent and not has_browser_intent:
            add_score("email", 0.78)

        if has_document_intent and not has_spreadsheet_intent and not has_presentation_intent and not has_browser_intent:
            add_score("document", 0.96)

        if has_spreadsheet_intent and not has_calendar_intent and not has_email_intent and not has_browser_intent:
            add_score("spreadsheet", 0.95)

        if has_presentation_intent and not has_spreadsheet_intent and not has_browser_intent:
            add_score("presentation", 0.94)

        if has_travel_intent and not has_calendar_intent and not has_email_intent and not has_browser_intent:
            add_score("travel", 0.95)

        if has_browser_intent:
            add_score("browser", 0.98)

        if contains_any("train", "rail", "railway", "irctc") and contains_any("book", "reserve", "buy"):
            add_score("browser", 0.99)
            add_score("travel", 0.1)

        if contains_any("calendar", "email", "document", "spreadsheet", "presentation") and not contains_any("browser", "form", "github", "linkedin", "apply", "login"):
            add_score("browser", 0.1)

        browser_website, browser_intent, browser_parameters, browser_approval = extract_browser_plan()
        browser_selection = (
            (contains_any("linkedin") or contains_any("github") or contains_any("google form", "form") or contains_any("indeed"))
            or (contains_any("train") and contains_any("book", "reserve", "buy"))
        )

        if browser_selection:
            selected_skill = "browser"
            action = "book_train" if browser_intent == "book_train" else browser_intent
            required_connectors = ["browser"]
            parameters = browser_parameters
            approval_required = browser_approval
            confidence = 0.99
        else:
            selected_skill = max(classification_scores, key=classification_scores.get)
            selected_entry = next(entry for entry in candidates if entry[0] == selected_skill)
            selected_skill, _, action, required_connectors, parameters, approval_required = selected_entry
            confidence = round(classification_scores[selected_skill], 2)

        if confidence < 0.6:
            selected_skill = "research"
            action = "research"
            required_connectors = ["browser"]
            parameters = {"query": objective}
            approval_required = False
            confidence = 0.75

        skill_cls = default_registry.get_skill_class(selected_skill)
        skill_identity = getattr(skill_cls(), "identity", selected_skill) if skill_cls else selected_skill
        plan_payload = {
            "status": "planned",
            "objective": objective,
            "goal": objective,
            "selected_skill": skill_identity,
            "skill": skill_identity,
            "capability": skill_identity,
            "action": action,
            "confidence": confidence,
            "parameters": parameters,
            "approval_required": approval_required,
            "required_connectors": required_connectors,
            "milestones": getattr(agent, "milestones", []) or [],
            "effortEstimate": "Medium",
            "dependencies": ["Memory access", "Project context"],
            "risks": ["Scope drift", "Missing approvals"],
            "classification_scores": classification_scores,
            "steps": [
                {"id": "understand", "runner": skill_identity, "action": "understand", "metadata": {"skill": skill_identity}},
                {"id": "execute", "runner": skill_identity, "action": "execute", "metadata": {"skill": skill_identity}},
                {"id": "verify", "runner": skill_identity, "action": "verify", "metadata": {"skill": skill_identity}},
                {"id": "deliver", "runner": skill_identity, "action": "deliver", "metadata": {"skill": skill_identity}},
            ],
        }
        if selected_skill == "browser":
            plan_payload["website"] = browser_website
            plan_payload["intent"] = browser_intent
        return plan_payload
