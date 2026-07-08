from __future__ import annotations

from app.agents.models import AgentRuntimeState


class ProgressTracker:
    def snapshot(self, agent: AgentRuntimeState) -> dict:
        return {
            "status": "tracked",
            "agentId": agent.id,
            "completionProbability": 0.83,
            "nextMilestone": agent.milestones[0] if agent.milestones else "No milestone defined",
            "health": agent.health,
        }
