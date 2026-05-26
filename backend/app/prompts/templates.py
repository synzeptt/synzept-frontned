from app.prompts.base import SYNZEPT_SYSTEM
from app.prompts.chat import CONTINUITY_INSTRUCTION, INTENT_INSTRUCTIONS

INTENT_CLASSIFICATION = """Classify the user's intent. Return JSON only:
{
  "intent": "general_conversation|planning|writing|brainstorming|task_management|project_continuation|summarization|decision_support|organization|note_generation",
  "confidence": 0.0-1.0
}

Choose the single best fit. project_continuation if they reference ongoing project work."""

MEMORY_EXTRACT = """Analyze if this exchange contains durable information worth remembering long-term.

Return JSON only:
{
  "keep": boolean,
  "category": "identity|work|projects|preferences|goals|routines|relationships|productivity|decisions|other",
  "content": "single declarative sentence",
  "importance": 0.0-1.0,
  "action": "create|update|skip"
}

Store ONLY meaningful facts. Do NOT store greetings, small talk, or transient Q&A."""

CONVERSATION_SUMMARY = """Summarize this conversation in 2-3 sentences for future continuity.
Include: decisions made, open threads, commitments, and what to continue next."""

PROJECT_SUMMARY = """Create a concise project context summary (max 150 words).
Include: current status, key decisions, open items, and what to continue next."""

INTENT_ANALYSIS = INTENT_CLASSIFICATION
