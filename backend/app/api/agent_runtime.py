from fastapi import APIRouter

from app.agents.runtime import AgentRuntime
from app.agents.models import AgentRuntimeState

router = APIRouter(prefix="/api/internal/agent-runtime")


@router.get("", response_model=list[AgentRuntimeState])
async def list_agents():
    return AgentRuntime().list_agents()


@router.get("/{agent_id}", response_model=AgentRuntimeState | None)
async def get_agent(agent_id: str):
    return AgentRuntime().get_agent(agent_id)


@router.post("/{agent_id}/plan")
async def plan(agent_id: str):
    return AgentRuntime().plan(agent_id)


@router.post("/{agent_id}/execute")
async def execute(agent_id: str, approved: bool = False):
    return AgentRuntime().execute(agent_id, approved=approved)


@router.post("/{agent_id}/monitor")
async def monitor_agent(agent_id: str):
    return AgentRuntime().monitor_agent(agent_id)


@router.post("/{agent_id}/progress")
async def progress(agent_id: str):
    return AgentRuntime().progress(agent_id)


@router.post("/{agent_id}/remember")
async def remember(agent_id: str, note: str):
    return AgentRuntime().remember(agent_id, note)
