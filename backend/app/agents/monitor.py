from __future__ import annotations

from app.agents.models import AgentRuntimeState


class Monitor:
    def evaluate(self, agent: AgentRuntimeState) -> dict:
        return {
            "status": "monitored",
            "agentId": agent.id,
            "progress": "On track",
            "delays": [],
            "risks": ["Approval bottleneck"],
            "momentum": "Steady",
            "completionProbability": 0.83,
        }
