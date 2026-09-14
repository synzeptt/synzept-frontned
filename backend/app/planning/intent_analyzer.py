import re


class IntentAnalyzer:
    _rules = (
        ("booking", r"\b(book|reserve|ticket|hotel|flight|bus|travel)\b"),
        ("purchasing", r"\b(buy|purchase|order|shop|price|protein powder|laptop)\b"),
        ("communication", r"\b(reply|respond|email|message|send|inbox)\b"),
        ("scheduling", r"\b(schedule|calendar|meeting|appointment|prepare tomorrow)\b"),
        ("coding", r"\b(code|coding|implement|build|debug|refactor|function|api)\b"),
        ("research", r"\b(research|investigate|compare|competitor|find out|look into)\b"),
        ("analysis", r"\b(analy[sz]e|analysis|evaluate|assess|review)\b"),
        ("planning", r"\b(plan|roadmap|break down|study week|checklist)\b"),
        ("reminders", r"\b(remind|reminder|remember|alert)\b"),
        ("writing", r"\b(write|draft|prepare|generate|report|proposal|summary|summarize)\b"),
        ("automation", r"\b(automate|automation|organize|sort|clean up)\b"),
    )

    def classify(self, goal: str) -> str:
        normalized = goal.casefold()
        for intent, pattern in self._rules:
            if re.search(pattern, normalized):
                return intent
        return "general_execution"
