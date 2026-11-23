from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re

from sqlalchemy import select

from security_platform.auth.principals import OperatorPrincipal, DevicePrincipal, EnrollmentPrincipal
from security_platform.models import Tenant, Principal, Membership, Device, DeviceCredential


class ServiceError(ValueError):
    status_code = 400


class Unauthorized(ServiceError):
    status_code = 401


class Forbidden(ServiceError):
    status_code = 403


class NotFound(ServiceError):
    status_code = 404


class Conflict(ServiceError):
    status_code = 409


class EventCursorConflict(Conflict):
    """An event batch conflict that reports the device's accepted position.

    The two numbers are diagnostic: the agent keeps the pending batch on a 409
    and recovers by re-enrollment. Only event ingestion raises this, so every
    other 409 keeps its plain body.
    """

    def __init__(self, message, *, last_batch_sequence, last_event_seq):
        super().__init__(message)
        self.last_batch_sequence = last_batch_sequence
        self.last_event_seq = last_event_seq


class ContentTooLarge(ServiceError):
    status_code = 413


class UnprocessableContent(ServiceError):
    status_code = 422


class CapacityError(ServiceError):
    status_code = 429


@dataclass(frozen=True)
class ServiceLimits:
    max_devices: int = 1000
    max_active_grants: int = 1000
    max_grant_records: int = 2000
    max_credential_records: int = 16
    max_audits: int = 10000
    max_page_size: int = 100
    stale_seconds: int = 300
    grant_ttl_seconds: int = 600
    max_grant_ttl_seconds: int = 3600
    credential_ttl_seconds: int = 86400
    max_credential_ttl_seconds: int = 2592000
    max_events_per_device: int = 250000

    def __post_init__(self):
        if any(type(value) is not int or value < 1 or value > 10000000 for value in vars(self).values()):
            raise ValueError("Invalid service limits")
        if (self.grant_ttl_seconds > self.max_grant_ttl_seconds
                or self.credential_ttl_seconds > self.max_credential_ttl_seconds
                or self.max_grant_records < self.max_active_grants or self.max_credential_records < 2):
            raise ValueError("Inconsistent service limits")


DEFAULT_LIMITS = ServiceLimits()


def utc_now(now=None):
    now = datetime.now(timezone.utc) if now is None else now
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Server time must be timezone-aware")
    return now.astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value is not None else None


def secret_digest(token, prefix):
    if not isinstance(token, str) or re.fullmatch(re.escape(prefix) + r"[A-Za-z0-9_-]{43}", token) is None:
        raise Unauthorized("Invalid credential")
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def locked_tenant(session, tenant_id):
    tenant = session.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update())
    if tenant is None:
        raise NotFound("Resource not found")
    return tenant


def require_membership(session, operator, tenant_id, *, admin=False, lock=False):
    if not isinstance(operator, OperatorPrincipal):
        raise Unauthorized("Operator credential required")
    principal = session.scalar(select(Principal).where(Principal.issuer == operator.issuer,
                                                     Principal.subject == operator.subject))
    if principal is None:
        raise NotFound("Resource not found")
    query = select(Membership).where(Membership.tenant_id == tenant_id,
        Membership.principal_id == principal.id, Membership.revoked_at.is_(None))
    # Administrative mutations already hold the tenant row lock, shared with
    # local membership changes. Runtime membership access needs SELECT only.
    membership = session.scalar(query.execution_options(populate_existing=True))
    if membership is None:
        raise NotFound("Resource not found")
    if admin and membership.role != "tenant_admin":
        raise Forbidden("Tenant administrator role required")
    return principal, membership


def locked_device_credential(session, principal, now=None):
    if not isinstance(principal, DevicePrincipal):
        raise Unauthorized("Device credential required")
    device = session.scalar(select(Device).where(Device.tenant_id == principal.tenant_id,
        Device.id == principal.device_id).with_for_update().execution_options(populate_existing=True))
    if device is None or device.revoked_at is not None:
        raise Unauthorized("Invalid credential")
    credential = session.scalar(select(DeviceCredential).where(DeviceCredential.tenant_id == principal.tenant_id,
        DeviceCredential.device_id == principal.device_id, DeviceCredential.id == principal.credential_id)
        .with_for_update().execution_options(populate_existing=True))
    now = utc_now(now)
    if credential is None or credential.revoked_at is not None or credential.expires_at <= now:
        raise Unauthorized("Invalid credential")
    return device, credential


def bounded_page(limit, offset, limits):
    if type(limit) is not int or not 1 <= limit <= limits.max_page_size or type(offset) is not int or not 0 <= offset <= 10000:
        raise ServiceError("Invalid pagination")
