from __future__ import annotations

from app.agents.models import AgentStatus, AgentRuntimeState
from app.agents.planner import Planner
from app.agents.executor import Executor
from app.agents.monitor import Monitor
from app.agents.approval_manager import ApprovalManager
from app.agents.progress_tracker import ProgressTracker
from app.agents.agent_memory import AgentMemory
from app.agents.mock_data import MOCK_AGENTS


class AgentRuntime:
    def __init__(self) -> None:
        self.planner = Planner()
        self.executor = Executor()
        self.monitor = Monitor()
        self.approval_manager = ApprovalManager()
        self.progress_tracker = ProgressTracker()
        self.agent_memory = AgentMemory()
        self.agents = [AgentRuntimeState(**item) for item in MOCK_AGENTS]

    def list_agents(self) -> list[AgentRuntimeState]:
        return self.agents

    def get_agent(self, agent_id: str) -> AgentRuntimeState | None:
        return next((agent for agent in self.agents if agent.id == agent_id), None)

    def plan(self, agent_id: str) -> dict:
        agent = self.get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agent not found"}
        return self.planner.plan(agent)

    def execute(self, agent_id: str, approved: bool = False) -> dict:
        agent = self.get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agent not found"}
        if not approved and agent.requiresApproval:
            return self.approval_manager.request_approval(agent)
        return self.executor.execute(agent)

    def monitor_agent(self, agent_id: str) -> dict:
        agent = self.get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agent not found"}
        return self.monitor.evaluate(agent)

    def progress(self, agent_id: str) -> dict:
        agent = self.get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agent not found"}
        return self.progress_tracker.snapshot(agent)

    def remember(self, agent_id: str, note: str) -> dict:
        agent = self.get_agent(agent_id)
        if not agent:
            return {"status": "error", "message": "Agent not found"}
        return self.agent_memory.add_note(agent, note)
