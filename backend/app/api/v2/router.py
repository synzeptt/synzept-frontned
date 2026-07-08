from fastapi import APIRouter

from app.api.v2 import (
    agent_memory,
    autonomous_workspace,
    continuity_assistant,
    continuity_mode,
    core,
    daily_brief,
    goals,
    learning_engine,
    memory,
    proactive_intelligence,
    project_intelligence,
    user_understanding,
    workspace,
)

api_router = APIRouter(prefix="/api/v2")
api_router.include_router(core.router, tags=["core-foundation"])
api_router.include_router(continuity_assistant.router, tags=["continuity-assistant"])
api_router.include_router(continuity_mode.router, tags=["continuity-mode"])
api_router.include_router(user_understanding.router, tags=["user-understanding"])
api_router.include_router(daily_brief.router, tags=["daily-brief"])
api_router.include_router(project_intelligence.router, tags=["project-intelligence"])
api_router.include_router(learning_engine.router, tags=["learning-engine"])
api_router.include_router(agent_memory.router, tags=["agent-memory"])
api_router.include_router(autonomous_workspace.router, tags=["autonomous-workspace"])
api_router.include_router(goals.router, tags=["goals"])
api_router.include_router(workspace.router, tags=["workspace"])
api_router.include_router(proactive_intelligence.router, tags=["proactive-intelligence"])
api_router.include_router(memory.router, tags=["memory"])
