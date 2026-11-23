from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from security_platform.auth.principals import OperatorPrincipal
from security_platform.contracts import MAX_SEQUENCE
from security_platform.services import audit, enrollment, events, inventory
from .dependencies import SessionDependency, operator_principal

router = APIRouter(prefix="/api/v1", tags=["operator"])
OperatorDependency = Annotated[OperatorPrincipal, Depends(operator_principal)]


class GrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    ttl_seconds: int | None = Field(default=None, ge=1, le=3600)


class EmptyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


@router.get("/tenants")
def tenants(actor: OperatorDependency, session: SessionDependency, request: Request,
            limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10000)):
    return inventory.list_tenants(session, actor, limit=limit, offset=offset, limits=request.app.state.limits)


@router.post("/tenants/{tenant_id}/enrollment-grants", status_code=201)
def create_grant(tenant_id: UUID, body: GrantRequest, actor: OperatorDependency,
                 session: SessionDependency, request: Request):
    return enrollment.create_grant(session, actor, tenant_id, ttl_seconds=body.ttl_seconds, limits=request.app.state.limits)


@router.post("/tenants/{tenant_id}/enrollment-grants/{grant_id}/revoke")
def revoke_grant(tenant_id: UUID, grant_id: UUID, actor: OperatorDependency, session: SessionDependency,
                 request: Request, body: EmptyRequest = Body(default=EmptyRequest())):
    return enrollment.revoke_grant(session, actor, tenant_id, grant_id, limits=request.app.state.limits)


@router.get("/tenants/{tenant_id}/devices")
def devices(tenant_id: UUID, actor: OperatorDependency, session: SessionDependency, request: Request,
            limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10000)):
    return inventory.list_devices(session, actor, tenant_id, limit=limit, offset=offset, limits=request.app.state.limits)


@router.get("/tenants/{tenant_id}/devices/{device_id}")
def device(tenant_id: UUID, device_id: UUID, actor: OperatorDependency, session: SessionDependency, request: Request):
    return inventory.get_device(session, actor, tenant_id, device_id, limits=request.app.state.limits)


@router.get("/tenants/{tenant_id}/devices/{device_id}/events")
def device_events(tenant_id: UUID, device_id: UUID, actor: OperatorDependency, session: SessionDependency,
                  request: Request, before_seq: int | None = Query(None, ge=1, le=MAX_SEQUENCE),
                  limit: int = Query(50, ge=1, le=100)):
    return events.list_device_events(session, actor, tenant_id, device_id, before_seq=before_seq, limit=limit,
                                     limits=request.app.state.limits)


@router.post("/tenants/{tenant_id}/devices/{device_id}/revoke")
def revoke_device(tenant_id: UUID, device_id: UUID, actor: OperatorDependency, session: SessionDependency,
                  request: Request, body: EmptyRequest = Body(default=EmptyRequest())):
    return enrollment.revoke_device(session, actor, tenant_id, device_id, limits=request.app.state.limits)


@router.get("/tenants/{tenant_id}/audit")
def audit_log(tenant_id: UUID, actor: OperatorDependency, session: SessionDependency, request: Request,
              limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0, le=10000)):
    return audit.list_audit(session, actor, tenant_id, limit=limit, offset=offset, limits=request.app.state.limits)
