from fastapi import APIRouter

from app.api.v1 import auth, attachments, briefing, chat, continue_context, conversations, daily, dashboard, feedback, launch, memories, memory, notes, onboarding, projects, s1, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(launch.router, tags=["launch"])
api_router.include_router(onboarding.router, tags=["onboarding"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(continue_context.router, tags=["continue"])
api_router.include_router(conversations.router, tags=["conversations"])
api_router.include_router(memories.router, tags=["memories"])
api_router.include_router(memory.router, tags=["memory-intelligence"])
api_router.include_router(projects.router, tags=["projects"])
api_router.include_router(notes.router, tags=["notes"])
api_router.include_router(tasks.router, tags=["tasks"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(s1.router, tags=["s1"])
api_router.include_router(daily.router, tags=["daily"])
api_router.include_router(briefing.router, tags=["briefing"])
api_router.include_router(feedback.router, tags=["feedback"])
api_router.include_router(feedback.analytics_router, tags=["analytics"])
api_router.include_router(attachments.router, tags=["attachments"])
