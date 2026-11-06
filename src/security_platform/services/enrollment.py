"""Single-use enrollment and digest-only per-device credential lifecycle."""
from datetime import timedelta
import secrets

from sqlalchemy import delete, func, or_, select, update

from security_platform.auth.principals import EnrollmentPrincipal, DevicePrincipal
from security_platform.models import EnrollmentGrant, Device, DeviceCredential
from security_platform.services.audit import write_event
from security_platform.services.common import (DEFAULT_LIMITS, Unauthorized, NotFound, Conflict, CapacityError,
    ServiceError, iso, locked_tenant, locked_device_credential, require_membership, secret_digest, utc_now)


def _ttl(value, default, maximum):
    value = default if value is None else value
    if type(value) is not int or not 1 <= value <= maximum:
        raise ServiceError("Invalid credential lifetime")
    return value


def create_grant(session, operator, tenant_id, *, ttl_seconds=None, limits=DEFAULT_LIMITS, now=None):
    now = utc_now(now)
    ttl = _ttl(ttl_seconds, limits.grant_ttl_seconds, limits.max_grant_ttl_seconds)
    locked_tenant(session, tenant_id)
    principal, _ = require_membership(session, operator, tenant_id, admin=True, lock=True)
    active = session.scalar(select(func.count()).select_from(EnrollmentGrant).where(
        EnrollmentGrant.tenant_id == tenant_id, EnrollmentGrant.consumed_at.is_(None),
        EnrollmentGrant.revoked_at.is_(None), EnrollmentGrant.expires_at > now))
    if active >= limits.max_active_grants:
        raise CapacityError("Enrollment grant capacity reached")
    total = session.scalar(select(func.count()).select_from(EnrollmentGrant).where(EnrollmentGrant.tenant_id == tenant_id))
    if total >= limits.max_grant_records:
        obsolete = select(EnrollmentGrant.id).where(EnrollmentGrant.tenant_id == tenant_id,
            or_(EnrollmentGrant.consumed_at.is_not(None), EnrollmentGrant.revoked_at.is_not(None),
                EnrollmentGrant.expires_at <= now)).order_by(EnrollmentGrant.created_at, EnrollmentGrant.id).limit(
                    total - limits.max_grant_records + 1)
        session.execute(delete(EnrollmentGrant).where(EnrollmentGrant.tenant_id == tenant_id,
                                                     EnrollmentGrant.id.in_(obsolete)))
    secret = "spg_" + secrets.token_urlsafe(32)
    row = EnrollmentGrant(tenant_id=tenant_id, token_digest=secret_digest(secret, "spg_"), created_by=principal.id,
                          created_at=now, expires_at=now + timedelta(seconds=ttl))
    session.add(row)
    session.flush()
    write_event(session, tenant_id=tenant_id, actor_type="operator", actor_id=principal.id,
        action="enrollment_grant_created", object_type="enrollment_grant", object_id=row.id, now=now, limits=limits)
    return {"tenant_id": str(tenant_id), "grant_id": str(row.id), "enrollment_token": secret, "expires_at": iso(row.expires_at)}


def revoke_grant(session, operator, tenant_id, grant_id, *, limits=DEFAULT_LIMITS, now=None):
    now = utc_now(now)
    locked_tenant(session, tenant_id)
    principal, _ = require_membership(session, operator, tenant_id, admin=True, lock=True)
    row = session.scalar(select(EnrollmentGrant).where(EnrollmentGrant.tenant_id == tenant_id,
        EnrollmentGrant.id == grant_id).with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise NotFound("Resource not found")
    if row.consumed_at is not None:
        raise Conflict("Enrollment grant already consumed")
    if row.revoked_at is None:
        row.revoked_at = now
        write_event(session, tenant_id=tenant_id, actor_type="operator", actor_id=principal.id,
            action="enrollment_grant_revoked", object_type="enrollment_grant", object_id=row.id, now=now, limits=limits)
    return {"grant_id": str(row.id), "revoked": True}


def authenticate_grant(session, token, *, now=None):
    now = utc_now(now)
    digest = secret_digest(token, "spg_")
    row = session.scalar(select(EnrollmentGrant).where(EnrollmentGrant.token_digest == digest,
        EnrollmentGrant.consumed_at.is_(None), EnrollmentGrant.revoked_at.is_(None), EnrollmentGrant.expires_at > now))
    if row is None:
        raise Unauthorized("Invalid credential")
    return EnrollmentPrincipal(tenant_id=row.tenant_id, grant_id=row.id)


def _new_credential(session, tenant_id, device_id, now, ttl):
    secret = "spd_" + secrets.token_urlsafe(32)
    row = DeviceCredential(tenant_id=tenant_id, device_id=device_id, token_digest=secret_digest(secret, "spd_"),
                           created_at=now, expires_at=now + timedelta(seconds=ttl))
    session.add(row)
    session.flush()
    return row, secret


def _credential_reply(device, credential, secret):
    return {"tenant_id": str(device.tenant_id), "device_id": str(device.id), "credential_id": str(credential.id),
            "credential_secret": secret, "credential_expires_at": iso(credential.expires_at)}


def enroll_device(session, grant_principal, *, label, limits=DEFAULT_LIMITS, now=None):
    if not isinstance(grant_principal, EnrollmentPrincipal):
        raise Unauthorized("Enrollment credential required")
    if not isinstance(label, str) or not label.strip() or len(label) > 80 or any(ord(c) < 32 for c in label):
        raise ServiceError("Invalid device label")
    supplied_time = now
    now = utc_now(now)
    locked_tenant(session, grant_principal.tenant_id)
    grant = session.scalar(select(EnrollmentGrant).where(EnrollmentGrant.tenant_id == grant_principal.tenant_id,
        EnrollmentGrant.id == grant_principal.grant_id).with_for_update().execution_options(populate_existing=True))
    now = utc_now(supplied_time)
    if (grant is None or grant.consumed_at is not None or grant.revoked_at is not None or grant.expires_at <= now):
        raise Unauthorized("Invalid credential")
    count = session.scalar(select(func.count()).select_from(Device).where(Device.tenant_id == grant.tenant_id))
    if count >= limits.max_devices:
        raise CapacityError("Device capacity reached")
    device = Device(tenant_id=grant.tenant_id, label=label.strip(), created_at=now)
    session.add(device)
    session.flush()
    credential, secret = _new_credential(session, grant.tenant_id, device.id, now, limits.credential_ttl_seconds)
    grant.consumed_at = now
    write_event(session, tenant_id=grant.tenant_id, actor_type="device", actor_id=device.id,
        action="device_enrolled", object_type="device", object_id=device.id, now=now, limits=limits)
    session.flush()
    return _credential_reply(device, credential, secret)


def authenticate_device(session, token, *, now=None):
    now = utc_now(now)
    digest = secret_digest(token, "spd_")
    row = session.scalar(select(DeviceCredential).join(Device,
        (Device.tenant_id == DeviceCredential.tenant_id) & (Device.id == DeviceCredential.device_id)).where(
        DeviceCredential.token_digest == digest, DeviceCredential.revoked_at.is_(None), DeviceCredential.expires_at > now,
        Device.revoked_at.is_(None)))
    if row is None:
        raise Unauthorized("Invalid credential")
    return DevicePrincipal(tenant_id=row.tenant_id, device_id=row.device_id, credential_id=row.id)


def rotate_credential(session, device_principal, *, ttl_seconds=None, limits=DEFAULT_LIMITS, now=None):
    supplied_time = now
    now = utc_now(now)
    if not isinstance(device_principal, DevicePrincipal):
        raise Unauthorized("Device credential required")
    ttl = _ttl(ttl_seconds, limits.credential_ttl_seconds, limits.max_credential_ttl_seconds)
    locked_tenant(session, device_principal.tenant_id)
    device, old = locked_device_credential(session, device_principal, supplied_time)
    now = utc_now(supplied_time)
    old.revoked_at = now
    session.flush()
    new, secret = _new_credential(session, device.tenant_id, device.id, now, ttl)
    total = session.scalar(select(func.count()).select_from(DeviceCredential).where(
        DeviceCredential.tenant_id == device.tenant_id, DeviceCredential.device_id == device.id))
    if total > limits.max_credential_records:
        obsolete = select(DeviceCredential.id).where(DeviceCredential.tenant_id == device.tenant_id,
            DeviceCredential.device_id == device.id, DeviceCredential.revoked_at.is_not(None)).order_by(
                DeviceCredential.created_at, DeviceCredential.id).limit(total - limits.max_credential_records)
        session.execute(delete(DeviceCredential).where(DeviceCredential.tenant_id == device.tenant_id,
            DeviceCredential.device_id == device.id, DeviceCredential.id.in_(obsolete)))
    write_event(session, tenant_id=device.tenant_id, actor_type="device", actor_id=device.id,
        action="device_credential_rotated", object_type="device_credential", object_id=new.id, now=now, limits=limits)
    return _credential_reply(device, new, secret)


def revoke_device(session, operator, tenant_id, device_id, *, limits=DEFAULT_LIMITS, now=None):
    now = utc_now(now)
    locked_tenant(session, tenant_id)
    principal, _ = require_membership(session, operator, tenant_id, admin=True, lock=True)
    device = session.scalar(select(Device).where(Device.tenant_id == tenant_id, Device.id == device_id)
        .with_for_update().execution_options(populate_existing=True))
    if device is None:
        raise NotFound("Resource not found")
    if device.revoked_at is None:
        device.revoked_at = now
        session.execute(update(DeviceCredential).where(DeviceCredential.tenant_id == tenant_id,
            DeviceCredential.device_id == device_id, DeviceCredential.revoked_at.is_(None)).values(revoked_at=now))
        write_event(session, tenant_id=tenant_id, actor_type="operator", actor_id=principal.id,
            action="device_revoked", object_type="device", object_id=device.id, now=now, limits=limits)
    return {"device_id": str(device.id), "revoked": True}
