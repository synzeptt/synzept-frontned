from fastapi import APIRouter

from app.schemas.synzept_protocol import (
    ProtocolAuditLogOut,
    ProtocolPermissionGrantOut,
    ProtocolPermissionRequestIn,
    ProtocolResourceOut,
    ProtocolSubscriptionIn,
    ProtocolSubscriptionOut,
    SynzeptProtocolOut,
)
from app.services.synzept_protocol import SynzeptProtocolService

router = APIRouter(prefix="/api/protocol/v1")


@router.get("", response_model=SynzeptProtocolOut)
async def protocol_manifest():
    return SynzeptProtocolService().manifest()


@router.get("/resources", response_model=list[ProtocolResourceOut])
async def list_resources(type: str | None = None):
    return SynzeptProtocolService().resources(resource_type=type)


@router.get("/resources/{resource_type}/{resource_id}", response_model=ProtocolResourceOut | None)
async def resource_detail(resource_type: str, resource_id: str):
    return SynzeptProtocolService().resource_detail(resource_type, resource_id)


@router.patch("/resources/{resource_type}/{resource_id}", response_model=dict)
async def update_resource(resource_type: str, resource_id: str, payload: dict):
    return SynzeptProtocolService().update_resource(resource_type, resource_id, payload)


@router.get("/permissions", response_model=list[ProtocolPermissionGrantOut])
async def permission_grants():
    return SynzeptProtocolService().permission_grants()


@router.post("/permissions/request", response_model=ProtocolPermissionGrantOut)
async def request_permission(body: ProtocolPermissionRequestIn):
    return SynzeptProtocolService().request_permission(body)


@router.post("/permissions/{grant_id}/revoke", response_model=dict)
async def revoke_permission(grant_id: str):
    return SynzeptProtocolService().revoke_permission(grant_id)


@router.get("/subscriptions", response_model=list[ProtocolSubscriptionOut])
async def list_subscriptions():
    return SynzeptProtocolService().subscriptions()


@router.post("/subscriptions", response_model=ProtocolSubscriptionOut)
async def create_subscription(body: ProtocolSubscriptionIn):
    return SynzeptProtocolService().create_subscription(body)


@router.get("/audit", response_model=list[ProtocolAuditLogOut])
async def audit_logs():
    return SynzeptProtocolService().audit_logs()
