"""Self-reported endpoint events: ordered ingestion, timeline reads and retention.

Ingestion follows the snapshot rules. The device row lock serialises one
device, an exact retry of the last batch returns the stored acceptance, and any
other reuse of the last batch identity or an older position is a conflict that
reports the device's accepted position. Events are never upgraded beyond
self_reported/not_verified and, like snapshot ingestion, write no audit row.
The alert rules (services/alerts.py) run on a newly accepted batch only, in
the same transaction, so events and their alerts commit together.
"""
from collections import Counter
from datetime import datetime, timedelta
import hashlib
from uuid import UUID

from sqlalchemy import BigInteger, Uuid, column, delete, insert, select, tuple_, values
from sqlalchemy.exc import SQLAlchemyError

from security_platform.contracts import MAX_SEQUENCE
from security_platform.event_contracts import EVENT_FIELDS, EventBatch, EventBatchTooLarge, canonical_event_batch
from security_platform.models import Device, DeviceEventCursor, EndpointEvent, Tenant
from security_platform.services.alerts import raise_alerts
from security_platform.services.common import (DEFAULT_LIMITS, ContentTooLarge, EventCursorConflict, NotFound,
    ServiceError, UnprocessableContent, iso, locked_device_credential, require_membership, utc_now)


PRUNE_BATCH_ROWS = 5000
# Above the batch's own size, the most rows one ingestion deletes for the cap.
CAP_DELETE_CHUNK = 5000


def _acceptance(cursor):
    return {"accepted": True, "batch_id": str(cursor.last_batch_id), "batch_sequence": cursor.last_batch_sequence,
            "last_event_seq": cursor.last_event_seq, "received_at": iso(cursor.last_received_at)}


def _conflict(cursor, message):
    return EventCursorConflict(message, last_batch_sequence=cursor.last_batch_sequence,
                               last_event_seq=cursor.last_event_seq)


def _device_rows(tenant_id, device_id):
    return EndpointEvent.tenant_id == tenant_id, EndpointEvent.device_id == device_id


def _trim_to_cap(session, device, stored, batch_events, limits):
    """Delete the device's oldest rows above the cap; return how many were deleted.

    A DELETE ... IN (SELECT ... LIMIT n) could become a nested loop that reran
    the subquery for every row of the device once PostgreSQL used the prepared
    statement's generic plan. Two statements replace it: read the event_seq of
    the last row to delete, then delete the key range up to it. Neither has a
    subquery or join to loop over. With current statistics of a table that
    holds several devices, the generic plans of both are primary-key range
    scans. While the table holds a single device, a sequential scan can be the
    cheaper generic plan; the default plan_cache_mode=auto then keeps using
    custom plans for the actual key range. At most batch_events +
    CAP_DELETE_CHUNK rows go per ingestion, so a request stays short after the
    cap was lowered and stored_events converges over later batches. The
    configured cap is at least 1000 and a batch holds at most 200 events, so
    the current batch's rows are never among the deleted ones.
    """
    excess = stored - limits.max_events_per_device
    if excess <= 0:
        return 0
    count = min(excess, batch_events + CAP_DELETE_CHUNK)
    rows = _device_rows(device.tenant_id, device.id)
    threshold = session.scalar(select(EndpointEvent.event_seq).where(*rows).order_by(EndpointEvent.event_seq)
                               .offset(count - 1).limit(1))
    if threshold is None:
        # stored_events counts more rows than the device holds; delete nothing.
        return 0
    return session.execute(delete(EndpointEvent).where(*rows, EndpointEvent.event_seq <= threshold)
                           .execution_options(synchronize_session=False)).rowcount


def ingest_events(session, device_principal, batch, *, limits=DEFAULT_LIMITS, now=None):
    try:
        supplied = batch.model_dump(mode="json") if isinstance(batch, EventBatch) else batch
        batch = EventBatch.model_validate(supplied)
        canonical = canonical_event_batch(batch)
    except EventBatchTooLarge as exc:
        raise ContentTooLarge("Event batch too large") from exc
    except (ValueError, TypeError, AttributeError) as exc:
        raise UnprocessableContent("Invalid event batch") from exc
    digest = hashlib.sha256(canonical).hexdigest()
    device, _ = locked_device_credential(session, device_principal, now)
    received_at = utc_now(now)
    batch_id = UUID(batch.batch_id)
    cursor = session.scalar(select(DeviceEventCursor).where(DeviceEventCursor.tenant_id == device.tenant_id,
        DeviceEventCursor.device_id == device.id).with_for_update().execution_options(populate_existing=True))
    if cursor is not None:
        if batch.batch_sequence == cursor.last_batch_sequence or batch_id == cursor.last_batch_id:
            if (batch.batch_sequence == cursor.last_batch_sequence and batch_id == cursor.last_batch_id
                    and digest == cursor.last_batch_digest):
                return _acceptance(cursor)
            raise _conflict(cursor, "Event batch identity or sequence conflicts with current state")
        if batch.batch_sequence < cursor.last_batch_sequence:
            raise _conflict(cursor, "Event batch sequence is stale")
        if batch.events[0].event_seq <= cursor.last_event_seq:
            raise _conflict(cursor, "Event sequence does not follow the last accepted event")
    session.execute(insert(EndpointEvent), [{"tenant_id": device.tenant_id, "device_id": device.id,
        "event_seq": event.event_seq, "kind": event.kind, "received_at": received_at,
        "observed_at": datetime.fromisoformat(event.observed_at.replace("Z", "+00:00")),
        "payload": event.model_dump(mode="json")} for event in batch.events])
    # Before the cap trim, so that a parent stored just before this batch is still found.
    suppressed = raise_alerts(session, device, batch.events, received_at=received_at,
                              previous_event_seq=cursor.last_event_seq if cursor is not None else None, limits=limits)
    stored = (cursor.stored_events if cursor is not None else 0) + len(batch.events)
    deleted = _trim_to_cap(session, device, stored, len(batch.events), limits)
    if cursor is None:
        cursor = DeviceEventCursor(tenant_id=device.tenant_id, device_id=device.id, cap_deleted_events=0,
                                   suppressed_alerts=0)
        session.add(cursor)
    cursor.last_batch_sequence, cursor.last_batch_id, cursor.last_batch_digest = batch.batch_sequence, batch_id, digest
    cursor.last_event_seq, cursor.last_received_at = batch.events[-1].event_seq, received_at
    cursor.stored_events = stored - deleted
    # The exact number of rows the cap deleted; the cursor row lock keeps the sum exact.
    cursor.cap_deleted_events += deleted
    # Alert openings the per-device open-alert cap suppressed, under the same lock.
    cursor.suppressed_alerts += suppressed
    session.flush()
    return _acceptance(cursor)


def _event_view(row):
    payload = row.payload
    return {"event_seq": row.event_seq, "kind": row.kind, "observed_at": iso(row.observed_at),
            "received_at": iso(row.received_at), **{name: payload.get(name) for name in EVENT_FIELDS[row.kind]},
            "source": "self_reported", "producer_verification": "not_verified"}


def list_device_events(session, operator, tenant_id, device_id, *, before_seq=None, limit=50, limits=DEFAULT_LIMITS):
    """Newest first; keyset paging on event_seq because offsets stop at 10000.

    cap_deleted_events is the number of the device's rows the per-device cap
    has deleted at ingestion (0 until the device's first batch is accepted).
    Retention prune does not change it. suppressed_alerts is the number of
    alert openings the per-device open-alert cap suppressed (0 likewise).
    """
    require_membership(session, operator, tenant_id)
    if (type(limit) is not int or not 1 <= limit <= limits.max_page_size or (before_seq is not None
            and (type(before_seq) is not int or not 1 <= before_seq <= MAX_SEQUENCE))):
        raise ServiceError("Invalid pagination")
    if session.scalar(select(Device.id).where(Device.tenant_id == tenant_id, Device.id == device_id)) is None:
        raise NotFound("Resource not found")
    query = select(EndpointEvent).where(*_device_rows(tenant_id, device_id))
    if before_seq is not None:
        query = query.where(EndpointEvent.event_seq < before_seq)
    rows = session.scalars(query.order_by(EndpointEvent.event_seq.desc()).limit(limit + 1)).all()
    counters = session.execute(select(DeviceEventCursor.cap_deleted_events, DeviceEventCursor.suppressed_alerts).where(
        DeviceEventCursor.tenant_id == tenant_id, DeviceEventCursor.device_id == device_id)).first()
    cap_deleted, suppressed = (0, 0) if counters is None else counters
    return {"items": [_event_view(row) for row in rows[:limit]],
            "next_before_seq": rows[limit - 1].event_seq if len(rows) > limit else None,
            "cap_deleted_events": cap_deleted, "suppressed_alerts": suppressed}


def _prune_chunk(session, tenant_id, cutoff, batch_size):
    expired = session.execute(select(EndpointEvent.device_id, EndpointEvent.event_seq).where(
        EndpointEvent.tenant_id == tenant_id, EndpointEvent.received_at < cutoff)
        .order_by(EndpointEvent.received_at).limit(batch_size)).all()
    if not expired:
        return 0, Counter()
    # Ingestion locks a device's cursor before touching its event rows. Take
    # the same order, sorted by device, so that neither an ingestion nor a
    # parallel prune can deadlock with this transaction.
    cursors = session.scalars(select(DeviceEventCursor).where(DeviceEventCursor.tenant_id == tenant_id,
        DeviceEventCursor.device_id.in_(sorted({device_id for device_id, _ in expired})))
        .order_by(DeviceEventCursor.device_id).with_for_update().execution_options(populate_existing=True)).all()
    # Delete exactly the selected keys: only rows of devices locked above.
    keys = values(column("device_id", Uuid), column("event_seq", BigInteger), name="expired_keys").data(
        [tuple(row) for row in expired])
    removed = Counter(session.scalars(delete(EndpointEvent).where(EndpointEvent.tenant_id == tenant_id,
        EndpointEvent.received_at < cutoff, tuple_(EndpointEvent.device_id, EndpointEvent.event_seq).in_(
            select(keys.c.device_id, keys.c.event_seq))).returning(EndpointEvent.device_id)
        .execution_options(synchronize_session=False)))
    for cursor in cursors:
        cursor.stored_events = max(cursor.stored_events - removed[cursor.device_id], 0)
    session.flush()
    return len(expired), removed


def prune_expired_events(database, *, now=None, batch_size=PRUNE_BATCH_ROWS):
    """Delete events received before each tenant's retention window.

    Server time decides; the device clock (observed_at) is never consulted.
    Each chunk is its own short transaction of at most ``batch_size`` rows, and
    the stored-event count of every touched device is recomputed in that same
    transaction from the exact number of its deleted rows.

    A failing chunk (lock or statement timeout, any other database error) rolls
    back only itself: committed chunks stay deleted and are counted. The
    tenant is then skipped for this run, counted in ``failed_tenants``, and the
    next tenant continues; the next run retries it.
    """
    if type(batch_size) is not int or not 1 <= batch_size <= PRUNE_BATCH_ROWS:
        raise ValueError("Invalid prune batch size")
    now = utc_now(now)
    with database.session() as session:
        tenants = session.execute(select(Tenant.id, Tenant.event_retention_days).order_by(Tenant.id)).all()
    deleted, devices, failed = 0, set(), 0
    for tenant_id, days in tenants:
        cutoff = now - timedelta(days=days)
        try:
            while True:
                with database.session() as session:
                    selected, removed = _prune_chunk(session, tenant_id, cutoff, batch_size)
                deleted += sum(removed.values())
                devices.update(removed)
                # A full chunk without progress means concurrent deletion took
                # the rows; the next scheduled run picks up anything left.
                if selected < batch_size or not removed:
                    break
        except SQLAlchemyError:
            failed += 1
    return {"tenants": len(tenants), "deleted_events": deleted, "devices": len(devices), "failed_tenants": failed}
