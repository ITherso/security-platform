from datetime import datetime

from sqlalchemy import select

from security_platform.auth.principals import OperatorPrincipal
from security_platform.models import Tenant, Principal, Membership, Device, ProductState
from security_platform.services.common import (DEFAULT_LIMITS, Unauthorized, NotFound,
    bounded_page, iso, require_membership, utc_now)


def list_tenants(session, operator, *, limit=50, offset=0, limits=DEFAULT_LIMITS):
    if not isinstance(operator, OperatorPrincipal):
        raise Unauthorized("Operator credential required")
    bounded_page(limit, offset, limits)
    rows = session.execute(select(Tenant, Membership.role).join(Membership, Membership.tenant_id == Tenant.id)
        .join(Principal, Principal.id == Membership.principal_id).where(Principal.issuer == operator.issuer,
            Principal.subject == operator.subject, Membership.revoked_at.is_(None)).order_by(Tenant.created_at, Tenant.id)
        .offset(offset).limit(limit + 1)).all()
    return {"items": [{"id": str(tenant.id), "name": tenant.name, "role": role} for tenant, role in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None}


def _age(observed_at, now):
    if observed_at is None:
        return {"age_seconds": None, "clock_state": "unknown"}
    if observed_at > now:
        return {"age_seconds": None, "clock_state": "future"}
    return {"age_seconds": int((now - observed_at).total_seconds()), "clock_state": "not_verified"}


def _device_view(row, now, limits):
    if row.last_received_at is None:
        connection = "never_seen"
    elif 0 <= (now - row.last_received_at).total_seconds() <= limits.stale_seconds:
        connection = "recent"
    else:
        connection = "stale"
    return {"id": str(row.id), "tenant_id": str(row.tenant_id), "label": row.label,
        "identity_status": "revoked" if row.revoked_at is not None else "active", "connection_status": connection,
        "created_at": iso(row.created_at), "revoked_at": iso(row.revoked_at),
        "last_sequence": row.last_sequence, "last_received_at": iso(row.last_received_at),
        "source_observed_at": iso(row.source_observed_at), "source_observation": _age(row.source_observed_at, now),
        "source": "self_reported", "producer_verification": "not_verified"}


def list_devices(session, operator, tenant_id, *, limit=50, offset=0, limits=DEFAULT_LIMITS, now=None):
    require_membership(session, operator, tenant_id)
    bounded_page(limit, offset, limits)
    now = utc_now(now)
    rows = session.scalars(select(Device).where(Device.tenant_id == tenant_id).order_by(
        Device.created_at, Device.id).offset(offset).limit(limit + 1)).all()
    return {"items": [_device_view(row, now, limits) for row in rows[:limit]],
            "next_offset": offset + limit if len(rows) > limit else None}


def get_device(session, operator, tenant_id, device_id, *, limits=DEFAULT_LIMITS, now=None):
    require_membership(session, operator, tenant_id)
    now = utc_now(now)
    row = session.scalar(select(Device).where(Device.tenant_id == tenant_id, Device.id == device_id))
    if row is None:
        raise NotFound("Resource not found")
    products = session.scalars(select(ProductState).where(ProductState.tenant_id == tenant_id,
        ProductState.device_id == device_id).order_by(ProductState.product_id)).all()
    product_views = []
    for product in products:
        payload = product.payload
        observed_text = payload.get("source_observed_at")
        observed = datetime.fromisoformat(observed_text.replace("Z", "+00:00")) if observed_text else None
        view = {"product_id": product.product_id, "snapshot_sequence": product.snapshot_sequence,
                "received_at": iso(product.received_at), "observation": _age(observed, now), "state": payload}
        if product.product_id == "termivar":
            report = payload.get("latest_report")
            imported = datetime.fromisoformat(report["imported_at"].replace("Z", "+00:00")) if report else None
            view["report_import_age"] = _age(imported, now)
        product_views.append(view)
    return {**_device_view(row, now, limits), "products": product_views,
            "missing_products": sorted({"hostbasedfirewall", "termivar", "antivirus"} - {p.product_id for p in products})}
