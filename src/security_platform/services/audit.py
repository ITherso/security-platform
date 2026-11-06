from sqlalchemy import delete, func, select

from security_platform.models import AuditEvent
from security_platform.services.common import DEFAULT_LIMITS, bounded_page, iso, require_membership, utc_now


ACTIONS = {"tenant_created", "membership_set", "membership_revoked", "enrollment_grant_created",
           "enrollment_grant_revoked", "device_enrolled", "device_revoked", "device_credential_rotated"}
OBJECTS = {"tenant", "membership", "enrollment_grant", "device", "device_credential"}


def write_event(session, *, tenant_id, actor_type, actor_id, action, object_type, object_id,
                now=None, limits=DEFAULT_LIMITS):
    """Caller holds tenant row lock. Retain bounded newest events in this transaction."""
    if action not in ACTIONS or object_type not in OBJECTS or actor_type not in {"operator", "device", "local_admin"}:
        raise ValueError("Unsupported audit event")
    count = session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == tenant_id))
    if count >= limits.max_audits:
        obsolete = select(AuditEvent.id).where(AuditEvent.tenant_id == tenant_id).order_by(
            AuditEvent.created_at, AuditEvent.id).limit(count - limits.max_audits + 1)
        session.execute(delete(AuditEvent).where(AuditEvent.tenant_id == tenant_id, AuditEvent.id.in_(obsolete)))
    event = AuditEvent(tenant_id=tenant_id, actor_type=actor_type, actor_id=actor_id,
        action=action, object_type=object_type, object_id=object_id, outcome="success", created_at=utc_now(now))
    session.add(event)
    session.flush()
    return event


def list_audit(session, operator, tenant_id, *, limit=50, offset=0, limits=DEFAULT_LIMITS):
    require_membership(session, operator, tenant_id, admin=True)
    bounded_page(limit, offset, limits)
    rows = session.scalars(select(AuditEvent).where(AuditEvent.tenant_id == tenant_id).order_by(
        AuditEvent.created_at.desc(), AuditEvent.id.desc()).offset(offset).limit(limit + 1)).all()
    return {"items": [{"id": str(row.id), "tenant_id": str(row.tenant_id), "actor_type": row.actor_type,
        "actor_id": str(row.actor_id) if row.actor_id else None, "action": row.action, "object_type": row.object_type,
        "object_id": str(row.object_id), "outcome": row.outcome, "created_at": iso(row.created_at)} for row in rows[:limit]],
        "next_offset": offset + limit if len(rows) > limit else None}
