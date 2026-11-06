"""One last state per device; retries never manufacture a fresh heartbeat."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete

from security_platform.contracts import SnapshotEnvelope, canonical_json, snapshot_digest
from security_platform.models import ProductState
from security_platform.services.common import Conflict, ServiceError, iso, locked_device_credential, utc_now


def _acceptance(device):
    return {"accepted": True, "message_id": str(device.last_message_id), "sequence": device.last_sequence,
            "received_at": iso(device.last_received_at)}


def ingest_snapshot(session, device_principal, snapshot, *, now=None):
    try:
        supplied = snapshot.model_dump(mode="json") if isinstance(snapshot, SnapshotEnvelope) else snapshot
        snapshot = SnapshotEnvelope.model_validate(supplied)
        canonical_json(snapshot)
        digest = snapshot_digest(snapshot)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ServiceError("Invalid snapshot") from exc
    device, _ = locked_device_credential(session, device_principal, now)
    received_at = utc_now(now)
    message_id = UUID(snapshot.message_id)
    if device.last_sequence is not None:
        if snapshot.sequence == device.last_sequence or message_id == device.last_message_id:
            if (snapshot.sequence == device.last_sequence and message_id == device.last_message_id
                    and digest == device.last_content_digest):
                return _acceptance(device)
            raise Conflict("Snapshot identity or sequence conflicts with current state")
        if snapshot.sequence < device.last_sequence:
            raise Conflict("Snapshot sequence is stale")
    session.execute(delete(ProductState).where(ProductState.tenant_id == device.tenant_id,
                                               ProductState.device_id == device.id))
    for product in snapshot.products:
        session.add(ProductState(tenant_id=device.tenant_id, device_id=device.id, product_id=product.product_id,
            snapshot_sequence=snapshot.sequence, received_at=received_at, payload=product.model_dump(mode="json")))
    device.last_sequence = snapshot.sequence
    device.last_message_id = message_id
    device.last_content_digest = digest
    device.last_received_at = received_at
    device.source_observed_at = (datetime.fromisoformat(snapshot.source_observed_at.replace("Z", "+00:00"))
                                 if snapshot.source_observed_at is not None else None)
    session.flush()
    return _acceptance(device)
