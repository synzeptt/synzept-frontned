import logging

from fastapi import APIRouter, Depends, Query
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.connected_apps import CalendarContextOut, CalendarSyncOut, CalendarWeeklyContextOut, ConnectedAppStatusOut, ConnectUrlOut
from app.services.connected_apps.google_calendar_service import GoogleCalendarService
from app.services.connected_apps.google_workspace_service import GoogleWorkspaceService
from app.services.connected_apps.microsoft_365_service import Microsoft365Service
from app.services.connected_apps.github_service import GitHubService
from app.services.connected_apps.slack_service import SlackService
from app.services.connected_apps.notion_service import NotionService
from app.core.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/connected-apps")


@router.get("/google-calendar", response_model=ConnectedAppStatusOut)
async def google_calendar_status(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoogleCalendarService(session).status(user.id)


@router.post("/google-calendar/connect", response_model=ConnectUrlOut)
async def google_calendar_connect(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoogleCalendarService(session).authorization_url(user)


@router.get("/google-calendar/callback")
async def google_calendar_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    if GoogleWorkspaceService.callback_provider(state):
        redirect_url = await GoogleWorkspaceService(session).handle_callback(code, state, error)
        return RedirectResponse(redirect_url)
    redirect_url = await GoogleCalendarService(session).handle_callback(code, state, error)
    return RedirectResponse(redirect_url)


@router.post("/google-calendar/sync", response_model=CalendarSyncOut)
async def google_calendar_sync(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoogleCalendarService(session).sync(user.id)


@router.delete("/google-calendar", response_model=ConnectedAppStatusOut)
async def google_calendar_disconnect(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoogleCalendarService(session).disconnect(user.id)


@router.get("/google-calendar/context", response_model=CalendarContextOut)
async def google_calendar_context(request: Request, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    try:
        return await GoogleCalendarService(session).calendar_context(user.id)
    except Exception:
        logger.exception("Google Calendar context request failed")
        return JSONResponse(
            status_code=500,
            content={"error": "calendar_context_unavailable", "message": "Synzept could not load Google Calendar context right now."},
            headers=_cors_headers_for_request(request),
        )


@router.get("/google-calendar/weekly-context", response_model=CalendarWeeklyContextOut)
async def google_calendar_weekly_context(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoogleCalendarService(session).weekly_context(user.id)


@router.get("/google-workspace", response_model=list[ConnectedAppStatusOut])
async def google_workspace_statuses(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await GoogleWorkspaceService(session).statuses(user.id)


@router.get("/microsoft-365", response_model=list[ConnectedAppStatusOut])
async def microsoft_365_statuses(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await Microsoft365Service(session).statuses(user.id)


@router.get("/microsoft/callback")
async def microsoft_365_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    redirect_url = await Microsoft365Service(session).handle_callback(code, state, error)
    return RedirectResponse(redirect_url)


@router.get("/microsoft-outlook-calendar/context", response_model=CalendarContextOut)
async def microsoft_calendar_context(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await Microsoft365Service(session).calendar_context(user.id)


def _cors_headers_for_request(request: Request) -> dict[str, str]:
    origin = request.headers.get("origin")
    if not origin or origin not in get_settings().cors_origin_list:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }


@router.get("/microsoft-outlook-calendar/weekly-context", response_model=CalendarWeeklyContextOut)
async def microsoft_calendar_weekly_context(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    return await Microsoft365Service(session).weekly_context(user.id)


@router.get("/github/callback")
async def github_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    redirect_url = await GitHubService(session).handle_callback(code, state, error)
    return RedirectResponse(redirect_url)


@router.get("/slack/callback")
async def slack_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    redirect_url = await SlackService(session).handle_callback(code, state, error)
    return RedirectResponse(redirect_url)


@router.get("/notion/callback")
async def notion_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
):
    redirect_url = await NotionService(session).handle_callback(code, state, error)
    return RedirectResponse(redirect_url)


@router.get("/{provider}", response_model=ConnectedAppStatusOut)
async def google_workspace_status(provider: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    if provider == "github":
        return await GitHubService(session).status(user.id)
    if provider == "slack":
        return await SlackService(session).status(user.id)
    if provider == "notion":
        return await NotionService(session).status(user.id)
    service = Microsoft365Service(session) if provider.startswith("microsoft_") else GoogleWorkspaceService(session)
    return await service.status(provider, user.id)


@router.post("/{provider}/connect", response_model=ConnectUrlOut)
async def google_workspace_connect(provider: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    if provider == "github":
        return await GitHubService(session).authorization_url(user)
    if provider == "slack":
        return await SlackService(session).authorization_url(user)
    if provider == "notion":
        return await NotionService(session).authorization_url(user)
    service = Microsoft365Service(session) if provider.startswith("microsoft_") else GoogleWorkspaceService(session)
    return await service.authorization_url(provider, user)


@router.post("/{provider}/sync", response_model=CalendarSyncOut)
async def google_workspace_sync(provider: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    if provider == "github":
        return await GitHubService(session).sync(user.id)
    if provider == "slack":
        return await SlackService(session).sync(user.id)
    if provider == "notion":
        return await NotionService(session).sync(user.id)
    service = Microsoft365Service(session) if provider.startswith("microsoft_") else GoogleWorkspaceService(session)
    return await service.sync(provider, user.id)


@router.delete("/{provider}", response_model=ConnectedAppStatusOut)
async def google_workspace_disconnect(provider: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_db)):
    if provider == "github":
        return await GitHubService(session).disconnect(user.id)
    if provider == "slack":
        return await SlackService(session).disconnect(user.id)
    if provider == "notion":
        return await NotionService(session).disconnect(user.id)
    service = Microsoft365Service(session) if provider.startswith("microsoft_") else GoogleWorkspaceService(session)
    return await service.disconnect(provider, user.id)
