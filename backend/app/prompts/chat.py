CONTINUITY_INSTRUCTION = """## Continue where you left off
Continue from this summary without repeating it:
{summary}
Be concise, action-oriented, and avoid extra recap."""

INTENT_INSTRUCTIONS = {
    "general_conversation": "## Mode: Conversation\nReply plainly and briefly unless the user asks for depth.",
    "planning": "## Mode: Planning\nGive a short plan with the next 3-5 steps.",
    "writing": "## Mode: Writing\nReturn a tight, ready-to-use draft.",
    "brainstorming": "## Mode: Brainstorming\nOffer a few focused ideas. Skip filler.",
    "task_management": "## Mode: Tasks\nClarify, prioritize, and keep it lightweight.",
    "project_continuation": "## Mode: Project continuation\nResume the thread and name the next action.",
    "summarization": "## Mode: Summarization\nSummarize decisions, open items, and the next step.",
    "decision_support": "## Mode: Decision support\nCompare options briefly and recommend one.",
    "organization": "## Mode: Organization\nStructure the information simply.",
    "note_generation": "## Mode: Notes\nCapture only the useful core.",
    "briefing": "## Mode: Briefing\nGive a short daily read: priorities, context, next action.",
    "continue": "## Mode: Continue\nResume without repeating captured context.",
}
