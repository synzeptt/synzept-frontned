from fastapi import APIRouter, Query

from app.schemas.workspace_os import WorkspaceCommandOut, WorkspaceCommandRunIn, WorkspaceOSOut, WorkspaceSearchOut
from app.services.workspace_os import WorkspaceOSService

router = APIRouter(prefix="/api/internal/workspace-os")


@router.get("", response_model=WorkspaceOSOut)
async def workspace_os_snapshot():
    return WorkspaceOSService().snapshot()


@router.get("/search", response_model=WorkspaceSearchOut)
async def workspace_search(
    q: str = "",
    filters: list[str] = Query(default_factory=list),
):
    return WorkspaceOSService().search(query=q, filters=filters)


@router.get("/commands", response_model=list[WorkspaceCommandOut])
async def workspace_commands():
    return WorkspaceOSService().commands()


@router.post("/commands/run", response_model=dict)
async def run_workspace_command(body: WorkspaceCommandRunIn):
    return WorkspaceOSService().run_command(body)
