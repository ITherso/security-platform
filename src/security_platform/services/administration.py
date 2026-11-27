"""Explicit local CLI administration, never called by public signup routes."""
from sqlalchemy import select

from security_platform.models import Tenant, Principal, Membership
from security_platform.services.audit import write_event
from security_platform.services.common import DEFAULT_LIMITS, NotFound, ServiceError, iso, locked_tenant, utc_now


def create_tenant(session, name, *, now=None, limits=DEFAULT_LIMITS):
    if not isinstance(name, str) or not name.strip() or len(name) > 120 or any(ord(c) < 32 for c in name):
        raise ServiceError("Invalid tenant name")
    now = utc_now(now)
    tenant = Tenant(name=name.strip(), created_at=now)
    session.add(tenant)
    session.flush()
    write_event(session, tenant_id=tenant.id, actor_type="local_admin", actor_id=None,
        action="tenant_created", object_type="tenant", object_id=tenant.id, now=now, limits=limits)
    return {"id": str(tenant.id), "name": tenant.name, "created_at": iso(tenant.created_at)}


def set_membership(session, tenant_id, issuer, subject, role, *, now=None, limits=DEFAULT_LIMITS):
    if (not isinstance(issuer, str) or not 1 <= len(issuer) <= 512
            or not isinstance(subject, str) or not 1 <= len(subject) <= 255
            or role not in {"tenant_admin", "viewer"}):
        raise ServiceError("Invalid membership")
    now = utc_now(now)
    locked_tenant(session, tenant_id)
    # Serialize this administrative identity upsert across different tenants too.
    # The unique issuer/subject constraint remains the final concurrent boundary.
    from sqlalchemy.dialects.postgresql import insert
    session.execute(insert(Principal).values(issuer=issuer, subject=subject, created_at=now)
                    .on_conflict_do_nothing(index_elements=[Principal.issuer, Principal.subject]))
    principal = session.scalar(select(Principal).where(Principal.issuer == issuer, Principal.subject == subject))
    membership = session.scalar(select(Membership).where(Membership.tenant_id == tenant_id,
        Membership.principal_id == principal.id).with_for_update())
    if membership is None:
        membership = Membership(tenant_id=tenant_id, principal_id=principal.id, role=role, created_at=now)
        session.add(membership)
    else:
        membership.role, membership.revoked_at = role, None
    write_event(session, tenant_id=tenant_id, actor_type="local_admin", actor_id=None,
        action="membership_set", object_type="membership", object_id=principal.id, now=now, limits=limits)
    return {"tenant_id": str(tenant_id), "principal_id": str(principal.id), "role": role}


def set_event_retention(session, tenant_id, days, *, now=None, limits=DEFAULT_LIMITS):
    """Days of server receive time that `events prune` keeps for this tenant."""
    if type(days) is not int or not 1 <= days <= 90:
        raise ServiceError("Invalid event retention")
    now = utc_now(now)
    tenant = locked_tenant(session, tenant_id)
    tenant.event_retention_days = days
    session.flush()
    write_event(session, tenant_id=tenant_id, actor_type="local_admin", actor_id=None,
        action="tenant_event_retention_set", object_type="tenant", object_id=tenant_id, now=now, limits=limits)
    return {"tenant_id": str(tenant_id), "event_retention_days": days}


def set_alert_retention(session, tenant_id, days, *, now=None, limits=DEFAULT_LIMITS):
    """Days after closed_at that `alerts prune` keeps a closed alert of this tenant."""
    if type(days) is not int or not 30 <= days <= 3650:
        raise ServiceError("Invalid alert retention")
    now = utc_now(now)
    tenant = locked_tenant(session, tenant_id)
    tenant.alert_retention_days = days
    session.flush()
    write_event(session, tenant_id=tenant_id, actor_type="local_admin", actor_id=None,
        action="tenant_alert_retention_set", object_type="tenant", object_id=tenant_id, now=now, limits=limits)
    return {"tenant_id": str(tenant_id), "alert_retention_days": days}


def revoke_membership(session, tenant_id, issuer, subject, *, now=None, limits=DEFAULT_LIMITS):
    now = utc_now(now)
    locked_tenant(session, tenant_id)
    membership = session.scalar(select(Membership).join(Principal, Principal.id == Membership.principal_id).where(
        Membership.tenant_id == tenant_id, Principal.issuer == issuer, Principal.subject == subject)
        .with_for_update(of=Membership))
    if membership is None:
        raise NotFound("Resource not found")
    if membership.revoked_at is None:
        membership.revoked_at = now
        write_event(session, tenant_id=tenant_id, actor_type="local_admin", actor_id=None,
            action="membership_revoked", object_type="membership", object_id=membership.principal_id, now=now, limits=limits)
    return {"tenant_id": str(tenant_id), "principal_id": str(membership.principal_id), "revoked": True}
