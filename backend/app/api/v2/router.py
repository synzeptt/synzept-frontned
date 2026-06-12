from fastapi import APIRouter

from app.api.v2 import continuity_assistant, core, daily_brief, learning_engine, project_intelligence, user_understanding

api_router = APIRouter(prefix="/api/v2")
api_router.include_router(core.router, tags=["core-foundation"])
api_router.include_router(continuity_assistant.router, tags=["continuity-assistant"])
api_router.include_router(user_understanding.router, tags=["user-understanding"])
api_router.include_router(daily_brief.router, tags=["daily-brief"])
api_router.include_router(project_intelligence.router, tags=["project-intelligence"])
api_router.include_router(learning_engine.router, tags=["learning-engine"])
