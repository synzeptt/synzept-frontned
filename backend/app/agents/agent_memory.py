from __future__ import annotations

from app.agents.models import AgentRuntimeState


class AgentMemory:
    def __init__(self) -> None:
        self.notes: dict[str, list[str]] = {}

    def add_note(self, agent: AgentRuntimeState, note: str) -> dict:
        self.notes.setdefault(agent.id, []).append(note)
        return {
            "status": "saved",
            "agentId": agent.id,
            "note": note,
            "storedNotes": len(self.notes[agent.id]),
        }
