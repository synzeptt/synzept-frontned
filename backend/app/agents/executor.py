from __future__ import annotations

from app.agents.models import AgentRuntimeState


class Executor:
    def execute(self, agent: AgentRuntimeState) -> dict:
        return {
            "status": "executed",
            "agentId": agent.id,
            "actions": [
                "Create tasks",
                "Update project status",
                "Organize notes",
            ],
            "requiresApproval": agent.requiresApproval,
        }
