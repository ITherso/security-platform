from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field

from security_platform.auth.principals import OperatorPrincipal
from security_platform.contracts import MAX_SEQUENCE
from security_platform.services import alerts, audit, enrollment, events, inventory
from security_platform.services.common import ServiceError
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


@router.get("/tenants/{tenant_id}/alerts")
def alert_list(tenant_id: UUID, actor: OperatorDependency, session: SessionDependency, request: Request,
               status: Literal["open", "acknowledged", "closed"] | None = Query(None),
               device_id: UUID | None = Query(None),
               before_seen_at: str | None = Query(None, max_length=27, pattern=alerts.KEYSET_TIME_PATTERN),
               before_id: UUID | None = Query(None), limit: int = Query(50, ge=1, le=100)):
    try:
        alerts.parse_keyset(before_seen_at, before_id)
    except ServiceError:
        # Only one of the pair, or an impossible instant: refused like every
        # other invalid query value (422), never as a 400 request-boundary error.
        raise RequestValidationError([{"type": "value_error", "loc": ("query", "before_seen_at"),
                                       "msg": "Invalid pagination", "input": None}]) from None
    return alerts.list_alerts(session, actor, tenant_id, status=status, device_id=device_id,
                              before_seen_at=before_seen_at, before_id=before_id, limit=limit,
                              limits=request.app.state.limits)


@router.post("/tenants/{tenant_id}/alerts/{alert_id}/acknowledge")
def acknowledge_alert(tenant_id: UUID, alert_id: UUID, actor: OperatorDependency, session: SessionDependency,
                      request: Request, body: EmptyRequest = Body(default=EmptyRequest())):
    return alerts.acknowledge_alert(session, actor, tenant_id, alert_id, limits=request.app.state.limits)


@router.post("/tenants/{tenant_id}/alerts/{alert_id}/close")
def close_alert(tenant_id: UUID, alert_id: UUID, actor: OperatorDependency, session: SessionDependency,
                request: Request, body: EmptyRequest = Body(default=EmptyRequest())):
    return alerts.close_alert(session, actor, tenant_id, alert_id, limits=request.app.state.limits)
