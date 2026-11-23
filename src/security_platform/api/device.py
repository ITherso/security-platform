from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from security_platform.auth.principals import DevicePrincipal, EnrollmentPrincipal
from security_platform.contracts import SnapshotEnvelope
from security_platform.event_contracts import EventBatch
from security_platform.services import enrollment, events, snapshots
from .dependencies import SessionDependency, device_principal, enrollment_principal

router = APIRouter(prefix="/api/v1", tags=["device"])
DeviceDependency = Annotated[DevicePrincipal, Depends(device_principal)]
EnrollmentDependency = Annotated[EnrollmentPrincipal, Depends(enrollment_principal)]


class EnrollRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    label: str = Field(min_length=1, max_length=80, pattern=r"^[^\x00-\x1f\x7f]+$")


class RotateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    ttl_seconds: int | None = Field(default=None, ge=60, le=2592000)


@router.post("/enroll", status_code=201)
def enroll(body: EnrollRequest, actor: EnrollmentDependency, session: SessionDependency, request: Request):
    return enrollment.enroll_device(session, actor, label=body.label, limits=request.app.state.limits)


@router.put("/device/snapshot")
def snapshot(body: SnapshotEnvelope, actor: DeviceDependency, session: SessionDependency):
    return snapshots.ingest_snapshot(session, actor, body)


@router.post("/device/events")
def event_batch(body: EventBatch, actor: DeviceDependency, session: SessionDependency, request: Request):
    return events.ingest_events(session, actor, body, limits=request.app.state.limits)


@router.post("/device/credentials/rotate")
def rotate(actor: DeviceDependency, session: SessionDependency, request: Request,
            body: RotateRequest = Body(default=RotateRequest())):
    return enrollment.rotate_credential(session, actor, ttl_seconds=body.ttl_seconds, limits=request.app.state.limits)
