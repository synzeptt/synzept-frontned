from __future__ import annotations

from app.agents.models import AgentRuntimeState


class ApprovalManager:
    def request_approval(self, agent: AgentRuntimeState) -> dict:
        return {
            "status": "awaiting-approval",
            "agentId": agent.id,
            "message": "This action requires explicit approval before execution.",
            "recommendedAction": "Ask the user to approve the workflow",
        }
