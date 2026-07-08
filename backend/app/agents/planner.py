from __future__ import annotations

from app.agents.models import AgentRuntimeState


class Planner:
    def plan(self, agent: AgentRuntimeState) -> dict:
        return {
            "status": "planned",
            "objective": agent.objective,
            "milestones": agent.milestones,
            "effortEstimate": "Medium",
            "dependencies": ["Memory access", "Project context"],
            "risks": ["Scope drift", "Missing approvals"],
        }
