"""Real PostgreSQL event ingestion, timeline, per-device cap and retention.

HTTP/JWT acceptance of the two event routes is tested in test_events_api.py.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from functools import partial
import importlib.util
import json
from pathlib import Path
import threading
import time
from types import SimpleNamespace
from uuid import UUID, uuid4

from alembic.migration import MigrationContext
from alembic.operations import Operations
import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from security_platform import cli
from security_platform.auth.principals import OperatorPrincipal
from security_platform.db import Database
from security_platform.event_contracts import (EVENT_FIELDS, MAX_OBSERVED_AT, MIN_OBSERVED_AT, EventBatch,
    ProcessStarted, event_batch_digest, stored_event_bytes)
from security_platform.models import AuditEvent, DeviceEventCursor, EndpointEvent, Tenant
from security_platform.services import administration, enrollment, events, inventory
from security_platform.services.common import (DEFAULT_LIMITS, Conflict, ContentTooLarge, EventCursorConflict,
    NotFound, ServiceError, Unauthorized, UnprocessableContent, iso)
from test_services import NOW, enrolled, pg_service_databases  # noqa: F401  (shared real-database fixture)


pytestmark = pytest.mark.integration
PROJECT = Path(__file__).resolve().parents[2]
MASKED = r"\Device\HarddiskVolume3\Users\*\Downloads\setup.exe"
WIDE = "\U0001F600"


@pytest.fixture
def event_tenants(pg_service_databases):
    owner, runtime = pg_service_databases
    issuer = "https://event-fixture.example"
    admin_a, admin_b, viewer_a = (OperatorPrincipal(issuer=issuer, subject=str(uuid4())) for _ in range(3))
    with owner.session() as session:
        a = UUID(administration.create_tenant(session, "Events A", now=NOW)["id"])
        b = UUID(administration.create_tenant(session, "Events B", now=NOW)["id"])
        administration.set_membership(session, a, issuer, admin_a.subject, "tenant_admin", now=NOW)
        administration.set_membership(session, a, issuer, viewer_a.subject, "viewer", now=NOW)
        administration.set_membership(session, b, issuer, admin_b.subject, "tenant_admin", now=NOW)
    return SimpleNamespace(owner=owner, runtime=runtime, a=a, b=b, admin_a=admin_a, admin_b=admin_b,
                           viewer_a=viewer_a)


def started(seq, **changes):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2030-01-02T03:00:00.000001Z",
            "pid": 4000 + seq, "parent_pid": 4, "session_id": 1, "image": MASKED, **changes}


def stopped(seq, **changes):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2030-01-02T03:00:01Z",
            "pid": 4000 + seq, "exit_code": 0, "image": "setup.exe", **changes}


def sensor(seq, **changes):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:02Z",
            "state": "lost", "error_code": "session_in_use", **changes}


def batch(sequence, *items, batch_id=None):
    return EventBatch.model_validate({"schema_version": 1, "batch_id": batch_id or str(uuid4()),
                                      "batch_sequence": sequence, "events": list(items)})


def send(runtime, device, message, *, now=NOW, limits=DEFAULT_LIMITS):
    with runtime.session() as session:
        principal = enrollment.authenticate_device(session, device["credential_secret"], now=now)
        return events.ingest_events(session, principal, message, limits=limits, now=now)


def stored(owner, device):
    device_id = UUID(device["device_id"])
    with owner.session() as session:
        rows = session.scalars(select(EndpointEvent).where(EndpointEvent.device_id == device_id)
                               .order_by(EndpointEvent.event_seq)).all()
        cursor = session.scalar(select(DeviceEventCursor).where(DeviceEventCursor.device_id == device_id))
    return rows, cursor


def sequences(owner, device):
    return [row.event_seq for row in stored(owner, device)[0]]


def audit_count(owner, tenant):
    with owner.session() as session:
        return session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == tenant))


def test_batch_is_stored_once_with_server_time_and_writes_no_audit(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    before = audit_count(ctx.owner, ctx.a)
    message = batch(1, started(1), stopped(2), sensor(4))
    ack = send(ctx.runtime, device, message)
    assert ack == {"accepted": True, "batch_id": message.batch_id, "batch_sequence": 1, "last_event_seq": 4,
                   "received_at": "2030-01-02T03:04:05Z"}
    rows, cursor = stored(ctx.owner, device)
    assert [(row.tenant_id, row.event_seq, row.kind) for row in rows] == [
        (ctx.a, 1, "process_started"), (ctx.a, 2, "process_stopped"), (ctx.a, 4, "sensor_state")]
    assert all(row.received_at == NOW for row in rows)
    assert rows[1].observed_at == datetime(2030, 1, 2, 3, 0, 1, tzinfo=timezone.utc)
    assert [row.payload for row in rows] == [event.model_dump(mode="json") for event in message.events]
    assert rows[1].payload["observed_at"] == "2030-01-02T03:00:01.000000Z"
    assert (cursor.tenant_id, cursor.last_batch_sequence, str(cursor.last_batch_id), cursor.last_event_seq,
            cursor.last_received_at, cursor.stored_events) == (ctx.a, 1, message.batch_id, 4, NOW, 3)
    assert cursor.last_batch_digest == event_batch_digest(message)
    assert audit_count(ctx.owner, ctx.a) == before
    with ctx.runtime.session() as session:
        detail = inventory.get_device(session, ctx.admin_a, ctx.a, UUID(device["device_id"]), now=NOW)
    # Events never count as a snapshot heartbeat.
    assert detail["connection_status"] == "never_seen" and detail["last_received_at"] is None


def test_exact_replay_returns_the_stored_acceptance_and_inserts_nothing(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    message = batch(3, started(10), stopped(11))
    first = send(ctx.runtime, device, message)
    before = stored(ctx.owner, device)
    assert send(ctx.runtime, device, message, now=NOW + timedelta(seconds=30)) == first
    # The same content in another accepted representation is the same batch.
    equivalent = json.loads(json.dumps(message.model_dump(mode="json")))
    equivalent["events"][1]["observed_at"] = "2030-01-02T03:00:01Z"
    equivalent["events"] = [dict(reversed(list(item.items()))) for item in equivalent["events"]]
    assert send(ctx.runtime, device, equivalent, now=NOW + timedelta(seconds=60)) == first
    after = stored(ctx.owner, device)
    assert [(row.event_seq, row.received_at) for row in after[0]] == [(row.event_seq, row.received_at) for row in before[0]]
    assert (after[1].last_received_at, after[1].stored_events) == (NOW, 2)


REJECTED = {
    "same_sequence_new_id": lambda first: batch(5, started(12)),
    "same_id_new_sequence": lambda first: batch(6, started(12), batch_id=first.batch_id),
    "same_identity_new_content": lambda first: batch(5, started(10), stopped(11, exit_code=1), batch_id=first.batch_id),
    "older_sequence": lambda first: batch(4, started(12)),
    "repeated_event_seq": lambda first: batch(6, started(11)),
    "older_event_seq": lambda first: batch(6, started(3), stopped(12)),
}


@pytest.mark.parametrize("case", sorted(REJECTED))
def test_conflicting_or_stale_batches_are_conflicts_and_atomic(event_tenants, case):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    first = batch(5, started(10), stopped(11))
    send(ctx.runtime, device, first)
    with pytest.raises(EventCursorConflict) as raised:
        send(ctx.runtime, device, REJECTED[case](first), now=NOW + timedelta(seconds=1))
    # Every conflict carries the accepted position (diagnostic; the agent holds the batch).
    assert (raised.value.status_code, raised.value.last_batch_sequence, raised.value.last_event_seq) == (409, 5, 11)
    rows, cursor = stored(ctx.owner, device)
    assert [row.event_seq for row in rows] == [10, 11]
    assert (cursor.last_batch_sequence, str(cursor.last_batch_id), cursor.last_event_seq, cursor.stored_events,
            cursor.last_received_at) == (5, first.batch_id, 11, 2, NOW)


def test_gaps_in_batch_and_event_sequences_are_accepted(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, batch(1, started(1)))
    ack = send(ctx.runtime, device, batch(9, stopped(100), sensor(250)), now=NOW + timedelta(seconds=1))
    assert (ack["batch_sequence"], ack["last_event_seq"]) == (9, 250)
    assert sequences(ctx.owner, device) == [1, 100, 250]


def test_per_device_cap_keeps_the_newest_rows_and_an_exact_count(event_tenants):
    ctx = event_tenants
    limits = replace(DEFAULT_LIMITS, max_events_per_device=5)
    capped, neighbour, burst = (enrolled(ctx.runtime, ctx.admin_a, ctx.a) for _ in range(3))
    expected = {1: [1, 2, 3], 2: [3, 4, 5, 6, 7], 3: [5, 6, 7, 8, 9]}
    # The cursor counts every row the cap deleted, batch by batch: 0, then 2, then 2 more.
    cap_deleted = {1: 0, 2: 2, 3: 4}
    plan = {1: [started(1), stopped(2), sensor(3)], 2: [started(4), stopped(5), sensor(6), started(7)],
            3: [stopped(8), sensor(9)]}
    for sequence, items in plan.items():
        send(ctx.runtime, capped, batch(sequence, *items), limits=limits, now=NOW + timedelta(seconds=sequence))
        rows, cursor = stored(ctx.owner, capped)
        assert [row.event_seq for row in rows] == expected[sequence]
        assert cursor.stored_events == len(rows) and cursor.cap_deleted_events == cap_deleted[sequence]
    send(ctx.runtime, neighbour, batch(1, started(1), stopped(2)), limits=limits)
    assert sequences(ctx.owner, neighbour) == [1, 2] and stored(ctx.owner, neighbour)[1].cap_deleted_events == 0
    # One batch larger than the cap keeps only its own newest events.
    send(ctx.runtime, burst, batch(1, *[sensor(seq, state="started", error_code=None) for seq in range(1, 9)]),
         limits=limits)
    rows, cursor = stored(ctx.owner, burst)
    assert [row.event_seq for row in rows] == [4, 5, 6, 7, 8] and cursor.stored_events == 5
    assert cursor.last_event_seq == 8 and cursor.cap_deleted_events == 3
    # Each device has its own counter.
    assert stored(ctx.owner, capped)[1].cap_deleted_events == 4
    assert stored(ctx.owner, neighbour)[1].cap_deleted_events == 0


def bulk_rows(owner, tenant, device_id, first, last):
    """Store event_seq first..last for a device in one statement and count them on its cursor."""
    with owner.session() as session:
        session.execute(text(
            "INSERT INTO endpoint_events (tenant_id, device_id, event_seq, kind, observed_at, received_at, payload) "
            "SELECT CAST(:tenant AS uuid), CAST(:device AS uuid), seq, 'sensor_state', CAST(:at AS timestamptz), "
            "CAST(:at AS timestamptz), jsonb_build_object('kind', 'sensor_state', 'event_seq', seq, 'observed_at', "
            "'2030-01-02T03:00:02.000000Z', 'state', 'started', 'error_code', NULL) "
            "FROM generate_series(CAST(:first AS bigint), CAST(:last AS bigint)) AS seq"),
            {"tenant": tenant, "device": device_id, "at": NOW, "first": first, "last": last})
        session.execute(text("UPDATE device_event_cursors SET stored_events = stored_events + :count "
                             "WHERE tenant_id = :tenant AND device_id = :device"),
                        {"count": last - first + 1, "tenant": tenant, "device": device_id})


def held_rows(owner, device_id):
    """(lowest event_seq, highest event_seq, rows, stored_events, cap_deleted_events) without loading the rows."""
    with owner.session() as session:
        return tuple(session.execute(text(
            "SELECT min(event_seq), max(event_seq), count(*), (SELECT stored_events FROM device_event_cursors "
            "WHERE device_id = :device), (SELECT cap_deleted_events FROM device_event_cursors "
            "WHERE device_id = :device) FROM endpoint_events WHERE device_id = :device"), {"device": device_id}).one())


def drop_rows(owner, device_id):
    # Keep the shared test database small; the device is not used again.
    with owner.session() as session:
        session.execute(text("DELETE FROM endpoint_events WHERE device_id = :device"), {"device": device_id})


def started_bursts(size):
    def burst(sequence, first):
        return batch(sequence, *[sensor(seq, state="started", error_code=None) for seq in range(first, first + size)])
    return burst


def test_lowered_cap_is_reached_over_later_batches_in_bounded_deletes(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    device_id = UUID(device["device_id"])
    burst = started_bursts(10)
    assert events.CAP_DELETE_CHUNK == 5000
    try:
        send(ctx.runtime, device, burst(1, 9991))
        bulk_rows(ctx.owner, ctx.a, device_id, 1, 9990)
        assert held_rows(ctx.owner, device_id) == (1, 10000, 10000, 10000, 0)
        # The cap is lowered from the default to 1000: each batch deletes at most
        # its own size + 5000 oldest rows and never one of its own events. The
        # cursor adds up the exact deletions: 5010, then 4010, then 10.
        lowered = replace(DEFAULT_LIMITS, max_events_per_device=1000)
        expected = {2: (5011, 10010, 5000, 5000, 5010), 3: (9021, 10020, 1000, 1000, 9020),
                    4: (9031, 10030, 1000, 1000, 9030)}
        for sequence, state in expected.items():
            send(ctx.runtime, device, burst(sequence, 10001 + (sequence - 2) * 10), limits=lowered,
                 now=NOW + timedelta(seconds=sequence))
            assert held_rows(ctx.owner, device_id) == state
    finally:
        drop_rows(ctx.owner, device_id)


def generic_plan_database(runtime):
    """The runtime role with every statement prepared and run with its generic plan."""
    return Database(database_url(runtime), pool_size=1, max_overflow=0, connect_args={
        "connect_timeout": 5, "prepare_threshold": 0,
        "options": "-c statement_timeout=5000 -c lock_timeout=3000 -c plan_cache_mode=force_generic_plan"})


def plan_nodes(plan):
    """Every (node type, index condition) pair of an EXPLAIN (FORMAT JSON) plan tree."""
    found = [(plan["Node Type"], plan.get("Index Cond", ""))]
    for child in plan.get("Plans", []):
        found += plan_nodes(child)
    return found


def generic_plan(session, statement):
    """The generic plan of a prepared statement's text, on the session's own connection."""
    # Sent unprepared: a prepared EXPLAIN would itself demand the $n parameters.
    with session.connection().connection.dbapi_connection.cursor() as cursor:
        cursor.execute("EXPLAIN (GENERIC_PLAN, FORMAT JSON) " + statement, prepare=False)
        return plan_nodes(cursor.fetchone()[0][0]["Plan"])


INDEX_RANGE_NODES = {"ModifyTable", "Index Scan", "Bitmap Heap Scan", "Bitmap Index Scan"}
PRIMARY_KEY_RANGE = "((tenant_id = $1) AND (device_id = $2) AND (event_seq <= $3))"


def test_cap_delete_stays_an_index_range_under_a_generic_plan(event_tenants):
    # psycopg prepares a statement after five runs on a pooled connection and
    # PostgreSQL then switches it to its generic plan. A DELETE ... IN (SELECT
    # ... LIMIT n) could become a nested loop that reran the subquery for every
    # row of the device and hit the 5 s statement timeout at the default cap.
    # Whether the planner picks that loop depends on the statistics, so the
    # test asserts the generic plan of the statement the service actually ran:
    # a primary-key range with no subquery, Limit or join.
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    device_id = UUID(device["device_id"])
    # Other devices in both tenants: the statistics then describe a deployment
    # of several devices, whatever rows other tests left behind. A table that
    # holds a single device has a sequential scan as its cheapest generic plan.
    others = [enrolled(ctx.runtime, ctx.admin_a, ctx.a), enrolled(ctx.runtime, ctx.admin_b, ctx.b)]
    held, size = 100000, 130
    burst = started_bursts(size)
    generic = generic_plan_database(ctx.runtime)
    try:
        for other in others:
            send(ctx.runtime, other, burst(1, 1))
        send(ctx.runtime, device, burst(1, held + 1))
        bulk_rows(ctx.owner, ctx.a, device_id, 1, held)
        # Current statistics, as autovacuum keeps them for a table that grows
        # gradually; right after a bulk load they would still describe a tiny table.
        with ctx.owner.session() as session:
            session.execute(text("ANALYZE endpoint_events"))
        with generic.session() as session:
            principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
            begun = time.monotonic()
            events.ingest_events(session, principal, burst(2, held + size + 1),
                                 limits=replace(DEFAULT_LIMITS, max_events_per_device=held + size), now=NOW)
            elapsed = time.monotonic() - begun
            prepared = session.execute(text("SELECT statement, generic_plans FROM pg_prepared_statements")).all()
            deletes = [(statement, count) for statement, count in prepared
                       if statement.lstrip().upper().startswith("DELETE FROM ENDPOINT_EVENTS")]
            plans = [generic_plan(session, statement) for statement, _ in deletes]
        # The cap delete really ran prepared, with its generic plan.
        assert len(deletes) == 1 and deletes[0][1] >= 1, prepared
        nodes = plans[0]
        assert {node for node, _ in nodes} <= INDEX_RANGE_NODES, nodes
        assert PRIMARY_KEY_RANGE in {condition for _, condition in nodes}, nodes
        assert elapsed < 2.5, elapsed
        assert held_rows(ctx.owner, device_id) == (size + 1, held + 2 * size, held + size, held + size, size)
    finally:
        generic.close()
        for each in (device, *others):
            drop_rows(ctx.owner, UUID(each["device_id"]))


def prune(ctx, **options):
    return events.prune_expired_events(ctx.runtime, now=NOW, **options)


def test_prune_uses_each_tenant_retention_and_server_receive_time(event_tenants):
    ctx = event_tenants
    with ctx.owner.session() as session:
        administration.set_event_retention(session, ctx.a, 1, now=NOW)
        assert session.get(Tenant, ctx.b).event_retention_days == 30
    device_a = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    device_b = enrolled(ctx.runtime, ctx.admin_b, ctx.b)
    day = timedelta(days=1)
    # The device clock is ignored in both directions: a future observed_at
    # does not keep an old row, an ancient observed_at does not expire a new one.
    future, ancient = "2099-01-01T00:00:00Z", "2000-01-01T00:00:00Z"
    send(ctx.runtime, device_a, batch(1, started(1, observed_at=future), stopped(2)), now=NOW - 3 * day)
    send(ctx.runtime, device_a, batch(2, sensor(3)), now=NOW - day - timedelta(microseconds=1))
    send(ctx.runtime, device_a, batch(3, sensor(4)), now=NOW - day)
    send(ctx.runtime, device_a, batch(4, started(5, observed_at=ancient)), now=NOW - timedelta(hours=2))
    send(ctx.runtime, device_b, batch(1, started(1)), now=NOW - 31 * day)
    send(ctx.runtime, device_b, batch(2, stopped(2)), now=NOW - 3 * day)
    summary = prune(ctx)
    assert set(summary) == {"tenants", "deleted_events", "devices", "failed_tenants"}
    assert all(type(value) is int for value in summary.values())
    assert summary["tenants"] >= 2 and summary["deleted_events"] >= 4 and summary["devices"] >= 2
    assert summary["failed_tenants"] == 0
    for device, kept in ((device_a, [4, 5]), (device_b, [2])):
        rows, cursor = stored(ctx.owner, device)
        assert [row.event_seq for row in rows] == kept
        assert cursor.stored_events == len(kept)
    prune(ctx)
    assert sequences(ctx.owner, device_a) == [4, 5] and sequences(ctx.owner, device_b) == [2]


def test_prune_works_in_bounded_chunks_and_keeps_counts_exact(event_tenants, monkeypatch):
    ctx = event_tenants
    with ctx.owner.session() as session:
        administration.set_event_retention(session, ctx.a, 1, now=NOW)
    first, second = enrolled(ctx.runtime, ctx.admin_a, ctx.a), enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    old = NOW - timedelta(days=2)
    send(ctx.runtime, first, batch(1, *[sensor(seq, state="started", error_code=None) for seq in range(1, 8)]), now=old)
    send(ctx.runtime, second, batch(1, *[sensor(seq, state="started", error_code=None) for seq in range(1, 6)]), now=old)
    send(ctx.runtime, second, batch(2, started(6)), now=NOW)
    chunks, original = [], events._prune_chunk
    def observed(session, tenant_id, cutoff, batch_size):
        selected, removed = original(session, tenant_id, cutoff, batch_size)
        if tenant_id == ctx.a:
            chunks.append((selected, sum(removed.values())))
        return selected, removed
    monkeypatch.setattr(events, "_prune_chunk", observed)
    prune(ctx, batch_size=5)
    assert chunks == [(5, 5), (5, 5), (2, 2)]
    assert sequences(ctx.owner, first) == [] and sequences(ctx.owner, second) == [6]
    assert stored(ctx.owner, first)[1].stored_events == 0 and stored(ctx.owner, second)[1].stored_events == 1


def test_cap_deletions_are_shown_in_the_timeline_and_left_alone_by_prune(event_tenants):
    ctx = event_tenants
    with ctx.owner.session() as session:
        administration.set_event_retention(session, ctx.a, 1, now=NOW)
    limits = replace(DEFAULT_LIMITS, max_events_per_device=5)
    device, quiet = enrolled(ctx.runtime, ctx.admin_a, ctx.a), enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, batch(1, *[sensor(seq, state="started", error_code=None) for seq in range(1, 9)]),
         limits=limits, now=NOW - timedelta(days=2))
    send(ctx.runtime, device, batch(2, started(9), stopped(10)), limits=limits)
    # Eight, then two events under a cap of five: the cap deleted 3, then 2 rows.
    rows, cursor = stored(ctx.owner, device)
    assert [row.event_seq for row in rows] == [6, 7, 8, 9, 10]
    assert (cursor.stored_events, cursor.cap_deleted_events) == (5, 5)

    def timeline(target, **options):
        with ctx.runtime.session() as session:
            return events.list_device_events(session, ctx.viewer_a, ctx.a, UUID(target["device_id"]), **options)

    first = timeline(device, limit=2)
    assert [item["event_seq"] for item in first["items"]] == [10, 9] and first["cap_deleted_events"] == 5
    assert timeline(device, before_seq=first["next_before_seq"])["cap_deleted_events"] == 5
    # A device without a cursor reports zero.
    assert timeline(quiet) == {"items": [], "next_before_seq": None, "cap_deleted_events": 0, "suppressed_alerts": 0}
    # Retention removes the three rows received two days ago; the counter stays.
    assert prune(ctx)["failed_tenants"] == 0
    rows, cursor = stored(ctx.owner, device)
    assert [row.event_seq for row in rows] == [9, 10]
    assert (cursor.stored_events, cursor.cap_deleted_events) == (2, 5)
    assert timeline(device)["cap_deleted_events"] == 5


@pytest.mark.parametrize("size", [0, 5001, True, 2.0])
def test_prune_batch_size_is_bounded(event_tenants, size):
    with pytest.raises(ValueError):
        prune(event_tenants, batch_size=size)


def three_tenants_with_expired_events(ctx, now):
    """Tenants first < middle < last by id; each device holds expired events 1 and 2 (in that receive order)
    and a fresh event 3, under the default 30-day retention."""
    with ctx.owner.session() as session:
        created = [UUID(administration.create_tenant(session, f"Prune {index}", now=NOW)["id"]) for index in range(3)]
        for tenant in created:
            administration.set_membership(session, tenant, ctx.admin_a.issuer, ctx.admin_a.subject, "tenant_admin",
                                          now=NOW)
    ordered = sorted(created)
    devices = [enrolled(ctx.runtime, ctx.admin_a, tenant) for tenant in ordered]
    for device in devices:
        send(ctx.runtime, device, batch(1, sensor(1)), now=now - timedelta(days=41))
        send(ctx.runtime, device, batch(2, sensor(2)), now=now - timedelta(days=40))
        send(ctx.runtime, device, batch(3, sensor(3)), now=now - timedelta(days=1))
    return ordered, devices


def test_prune_skips_a_failing_tenant_and_continues_with_the_next(event_tenants):
    ctx = event_tenants
    (first, middle, last), devices = three_tenants_with_expired_events(ctx, NOW)
    # Another transaction holds the middle device's cursor: that tenant's
    # chunk runs into the 3 s lock timeout while prune walks the tenants by id.
    blocker = ctx.owner.session_factory()
    try:
        blocker.execute(select(DeviceEventCursor).where(DeviceEventCursor.tenant_id == middle).with_for_update())
        summary = prune(ctx)
    finally:
        blocker.rollback()
        blocker.close()
    assert summary["failed_tenants"] == 1 and summary["deleted_events"] >= 4 and summary["devices"] >= 2
    assert sequences(ctx.owner, devices[0]) == [3] and sequences(ctx.owner, devices[2]) == [3]
    assert sequences(ctx.owner, devices[1]) == [1, 2, 3] and stored(ctx.owner, devices[1])[1].stored_events == 3
    # The next run retries the skipped tenant.
    assert prune(ctx)["failed_tenants"] == 0
    assert sequences(ctx.owner, devices[1]) == [3] and stored(ctx.owner, devices[1])[1].stored_events == 1


def failing_chunk(tenant_id, *, after):
    """A _prune_chunk that fails for one tenant once `after` of its chunks have been committed."""
    original, calls = events._prune_chunk, []
    def chunk(session, tenant, cutoff, batch_size):
        if tenant == tenant_id:
            calls.append(tenant)
            if len(calls) > after:
                raise OperationalError("DELETE FROM endpoint_events", {}, Exception("canceling statement due to "
                                                                                   "lock timeout"))
        return original(session, tenant, cutoff, batch_size)
    return chunk


def test_events_prune_cli_reports_failed_tenants_after_committed_chunks(event_tenants, monkeypatch, capsys):
    ctx = event_tenants
    (first, middle, last), devices = three_tenants_with_expired_events(ctx, datetime.now(timezone.utc))
    # One-row chunks: the middle tenant commits one chunk, then its second fails.
    monkeypatch.setattr(events, "prune_expired_events", partial(events.prune_expired_events, batch_size=1))
    monkeypatch.setattr(events, "_prune_chunk", failing_chunk(middle, after=1))
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.runtime))
    assert cli.main(["events", "prune"]) == 1
    output = capsys.readouterr()
    summary = json.loads(output.out)
    assert set(summary) == {"tenants", "deleted_events", "devices", "failed_tenants"}
    assert all(type(value) is int and value >= 0 for value in summary.values())
    assert summary["failed_tenants"] == 1 and summary["deleted_events"] >= 5 and summary["devices"] >= 3
    assert output.err.startswith("events prune incomplete: 1 tenant(s) failed")
    assert "no success was recorded" not in output.err and "postgresql" not in output.out + output.err
    assert sequences(ctx.owner, devices[0]) == [3] and sequences(ctx.owner, devices[2]) == [3]
    # The committed chunk of the failing tenant stays deleted and counted.
    assert sequences(ctx.owner, devices[1]) == [2, 3] and stored(ctx.owner, devices[1])[1].stored_events == 2


def test_timeline_pages_newest_first_with_a_keyset_cursor(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    device_id = UUID(device["device_id"])
    send(ctx.runtime, device, batch(1, started(1), stopped(2), sensor(3)))
    send(ctx.runtime, device, batch(2, started(4), stopped(5, exit_code=None, image=None), sensor(6), started(7)),
         now=NOW + timedelta(seconds=5))
    pages, before = [], None
    with ctx.runtime.session() as session:
        while True:
            page = events.list_device_events(session, ctx.viewer_a, ctx.a, device_id, before_seq=before, limit=3)
            pages.append([item["event_seq"] for item in page["items"]])
            before = page["next_before_seq"]
            if before is None:
                break
        assert pages == [[7, 6, 5], [4, 3, 2], [1]]
        everything = events.list_device_events(session, ctx.admin_a, ctx.a, device_id, limit=7)
        assert everything["next_before_seq"] is None and len(everything["items"]) == 7
        assert events.list_device_events(session, ctx.admin_a, ctx.a, device_id, before_seq=1) == {
            "items": [], "next_before_seq": None, "cap_deleted_events": 0, "suppressed_alerts": 0}
    by_seq = {item["event_seq"]: item for item in everything["items"]}
    for item in by_seq.values():
        assert set(item) == {"event_seq", "kind", "observed_at", "received_at", "source", "producer_verification",
                             *EVENT_FIELDS[item["kind"]]}
        assert (item["source"], item["producer_verification"]) == ("self_reported", "not_verified")
    assert by_seq[1] == {"event_seq": 1, "kind": "process_started", "observed_at": "2030-01-02T03:00:00.000001Z",
        "received_at": "2030-01-02T03:04:05Z", "pid": 4001, "parent_pid": 4, "session_id": 1, "image": MASKED,
        "source": "self_reported", "producer_verification": "not_verified"}
    assert by_seq[5]["exit_code"] is None and by_seq[5]["image"] is None
    assert by_seq[6]["received_at"] == "2030-01-02T03:04:10Z" and by_seq[6]["error_code"] == "session_in_use"


def test_timeline_is_tenant_scoped_and_hides_foreign_devices(event_tenants):
    ctx = event_tenants
    device_a = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    device_b = enrolled(ctx.runtime, ctx.admin_b, ctx.b)
    send(ctx.runtime, device_a, batch(1, started(1)))
    send(ctx.runtime, device_b, batch(1, stopped(1)))
    a_id, b_id = UUID(device_a["device_id"]), UUID(device_b["device_id"])
    stranger = OperatorPrincipal(issuer="https://other-issuer.example", subject=ctx.admin_a.subject)
    hidden = ((ctx.admin_a, ctx.a, b_id), (ctx.admin_a, ctx.b, b_id), (ctx.admin_a, ctx.b, a_id),
              (ctx.admin_b, ctx.a, a_id), (ctx.admin_b, ctx.b, a_id), (ctx.viewer_a, ctx.b, b_id),
              (ctx.admin_a, ctx.a, uuid4()), (stranger, ctx.a, a_id))
    for operator, tenant, device_id in hidden:
        with ctx.runtime.session() as session:
            with pytest.raises(NotFound):
                events.list_device_events(session, operator, tenant, device_id)
    with ctx.runtime.session() as session:
        assert [item["kind"] for item in events.list_device_events(session, ctx.admin_a, ctx.a, a_id)["items"]] == [
            "process_started"]
        assert [item["kind"] for item in events.list_device_events(session, ctx.admin_b, ctx.b, b_id)["items"]] == [
            "process_stopped"]
    with ctx.runtime.session() as session:
        with pytest.raises(Unauthorized):
            events.list_device_events(session, None, ctx.a, a_id)


@pytest.mark.parametrize("zone", ["UTC", "Europe/Istanbul", "Pacific/Kiritimati", "Etc/GMT+12"])
def test_extreme_accepted_observed_times_render_in_any_session_time_zone(event_tenants, zone):
    # PostgreSQL returns timestamptz in the session zone and the driver cannot
    # load a year after 9999 or before 1. Both ends of the accepted window must
    # read back in the zones furthest east (+14) and west (-12) of UTC.
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    earliest, latest = iso(MIN_OBSERVED_AT), iso(MAX_OBSERVED_AT - timedelta(microseconds=1))
    assert (earliest, latest) == ("1970-01-01T00:00:00Z", "9998-12-31T23:59:59.999999Z")
    send(ctx.runtime, device, batch(1, started(1, observed_at=earliest), sensor(2, observed_at=latest)))
    with ctx.runtime.session() as session:
        session.execute(text("SELECT set_config('TimeZone', :zone, true)"), {"zone": zone})
        assert session.scalar(text("SHOW TimeZone")) == zone
        page = events.list_device_events(session, ctx.viewer_a, ctx.a, UUID(device["device_id"]))
    assert [(item["event_seq"], item["observed_at"]) for item in page["items"]] == [(2, latest), (1, earliest)]


@pytest.mark.parametrize("options", [{"limit": 0}, {"limit": 101}, {"limit": True}, {"before_seq": 0},
                                     {"before_seq": 2**63}, {"before_seq": True}, {"before_seq": "5"}])
def test_timeline_pagination_is_bounded(event_tenants, options):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    with ctx.runtime.session() as session:
        with pytest.raises(ServiceError):
            events.list_device_events(session, ctx.admin_a, ctx.a, UUID(device["device_id"]), **options)


def test_revocation_and_expiry_are_rechecked_in_the_event_transaction(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    with ctx.runtime.session() as session:
        principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
    with ctx.runtime.session() as session:
        enrollment.revoke_device(session, ctx.admin_a, ctx.a, UUID(device["device_id"]), now=NOW)
    with ctx.runtime.session() as session:
        with pytest.raises(Unauthorized):
            events.ingest_events(session, principal, batch(1, started(1)), now=NOW)
    short = enrolled(ctx.runtime, ctx.admin_a, ctx.a, limits=replace(DEFAULT_LIMITS, credential_ttl_seconds=60))
    with ctx.runtime.session() as session:
        principal = enrollment.authenticate_device(session, short["credential_secret"], now=NOW)
    with ctx.runtime.session() as session:
        with pytest.raises(Unauthorized):
            events.ingest_events(session, principal, batch(1, started(1)), now=NOW + timedelta(seconds=60))
    assert sequences(ctx.owner, device) == [] and sequences(ctx.owner, short) == []


def test_invalid_batches_are_rejected_before_any_write(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    valid = batch(1, started(1)).model_dump(mode="json")
    for message in ({**valid, "device_id": device["device_id"]}, {**valid, "events": [started(1, image=r"\Users\x\a.exe")]},
                    {**valid, "events": [started(1, observed_at="9999-12-31T23:59:59Z")]}, None, "batch"):
        with pytest.raises(UnprocessableContent, match="^Invalid event batch$") as raised:
            send(ctx.runtime, device, message)
        assert raised.value.status_code == 422
    # Schema-valid, but the canonical form is larger than 16 KiB.
    oversized = {**valid, "events": [started(seq, image="\\" + "a" * 1000) for seq in range(1, 16)]}
    with pytest.raises(ContentTooLarge, match="^Event batch too large$") as raised:
        send(ctx.runtime, device, oversized)
    assert raised.value.status_code == 413
    assert stored(ctx.owner, device) == ([], None)


def test_parallel_exact_retries_store_the_batch_once(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    message = batch(1, started(1), stopped(2))
    barrier = threading.Barrier(2)
    def attempt(_):
        with ctx.runtime.session() as session:
            principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
            barrier.wait(timeout=5)
            return events.ingest_events(session, principal, message, now=NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.map(attempt, range(2))
    assert first == second and first["last_event_seq"] == 2
    rows, cursor = stored(ctx.owner, device)
    assert [row.event_seq for row in rows] == [1, 2] and cursor.stored_events == 2


def test_parallel_batches_sharing_a_sequence_accept_exactly_one(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    messages = [batch(1, started(1)), batch(1, started(1), stopped(2))]
    barrier = threading.Barrier(2)
    def attempt(message):
        try:
            with ctx.runtime.session() as session:
                principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
                barrier.wait(timeout=5)
                return events.ingest_events(session, principal, message, now=NOW)
        except Conflict:
            return None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, messages))
    accepted = [result for result in results if result is not None]
    assert len(accepted) == 1
    rows, cursor = stored(ctx.owner, device)
    assert [row.event_seq for row in rows] == list(range(1, accepted[0]["last_event_seq"] + 1))
    assert str(cursor.last_batch_id) == accepted[0]["batch_id"] and cursor.stored_events == len(rows)


@pytest.mark.parametrize("kind", ["event", "cursor"])
def test_composite_foreign_keys_reject_cross_tenant_rows(event_tenants, kind):
    ctx = event_tenants
    device_id = UUID(enrolled(ctx.runtime, ctx.admin_a, ctx.a)["device_id"])
    with pytest.raises(IntegrityError):
        with ctx.owner.session() as session:
            if kind == "event":
                session.add(EndpointEvent(tenant_id=ctx.b, device_id=device_id, event_seq=1, kind="sensor_state",
                    observed_at=NOW, received_at=NOW, payload={}))
            else:
                session.add(DeviceEventCursor(tenant_id=ctx.b, device_id=device_id, last_batch_sequence=1,
                    last_batch_id=uuid4(), last_batch_digest="a" * 64, last_event_seq=1, last_received_at=NOW,
                    stored_events=0))


@pytest.mark.parametrize("case", ["event_kind", "event_payload_bytes", "event_sequence", "event_observed_before_1970",
                                  "event_observed_from_9999", "cursor_digest", "cursor_batch_sequence",
                                  "cursor_event_seq", "cursor_stored_events", "cursor_cap_deleted_events",
                                  "retention_low", "retention_high"])
def test_database_constraints_back_the_contract(event_tenants, case):
    ctx = event_tenants
    device_id = UUID(enrolled(ctx.runtime, ctx.admin_a, ctx.a)["device_id"])
    event_row = {"tenant_id": ctx.a, "device_id": device_id, "event_seq": 1, "kind": "sensor_state",
                 "observed_at": NOW, "received_at": NOW, "payload": {"kind": "sensor_state"}}
    cursor_row = {"tenant_id": ctx.a, "device_id": device_id, "last_batch_sequence": 1, "last_batch_id": uuid4(),
                  "last_batch_digest": "a" * 64, "last_event_seq": 1, "last_received_at": NOW, "stored_events": 0,
                  "cap_deleted_events": 0}
    changes = {"event_kind": ("event", {"kind": "network_connection"}),
               "event_payload_bytes": ("event", {"payload": {"image": "a" * 4096}}),
               "event_sequence": ("event", {"event_seq": 0}),
               "event_observed_before_1970": ("event", {"observed_at": MIN_OBSERVED_AT - timedelta(microseconds=1)}),
               "event_observed_from_9999": ("event", {"observed_at": MAX_OBSERVED_AT}),
               "cursor_digest": ("cursor", {"last_batch_digest": "A" * 64}),
               "cursor_batch_sequence": ("cursor", {"last_batch_sequence": 0}),
               "cursor_event_seq": ("cursor", {"last_event_seq": 0}),
               "cursor_stored_events": ("cursor", {"stored_events": -1}),
               "cursor_cap_deleted_events": ("cursor", {"cap_deleted_events": -1}),
               "retention_low": ("tenant", 0), "retention_high": ("tenant", 91)}
    target, change = changes[case]
    # The unchanged rows are valid, so each failure below is the named CHECK.
    with ctx.owner.session_factory() as session:
        session.add(EndpointEvent(**event_row))
        session.add(DeviceEventCursor(**cursor_row))
        session.flush()
        session.rollback()
    with pytest.raises(IntegrityError):
        with ctx.owner.session() as session:
            if target == "event":
                session.add(EndpointEvent(**{**event_row, **change}))
            elif target == "cursor":
                session.add(DeviceEventCursor(**{**cursor_row, **change}))
            else:
                session.get(Tenant, ctx.a).event_retention_days = change


def test_contract_event_bound_equals_the_postgres_payload_check(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    prefix = '\\Device\\"quoted"\\Users\\*\\'
    base = stored_event_bytes(ProcessStarted.model_validate(started(1, image=prefix)))
    wide, narrow = divmod(4096 - base, len(WIDE.encode("utf-8")))
    message = batch(1, started(1, image=prefix + WIDE * wide + "a" * narrow), stopped(2, image="çalış.exe"),
                    sensor(3, state="failed", error_code="access_denied"))
    assert stored_event_bytes(message.events[0]) == 4096
    send(ctx.runtime, device, message)
    with ctx.owner.session() as session:
        sizes = session.execute(text("SELECT event_seq, octet_length(payload::text) FROM endpoint_events "
            "WHERE device_id = :device ORDER BY event_seq"), {"device": UUID(device["device_id"])}).all()
    assert [tuple(row) for row in sizes] == [(event.event_seq, stored_event_bytes(event)) for event in message.events]


def test_event_retention_setting_is_bounded_and_audited(event_tenants):
    ctx = event_tenants
    before = audit_count(ctx.owner, ctx.a)
    with ctx.owner.session() as session:
        assert session.get(Tenant, ctx.a).event_retention_days == 30
        assert administration.set_event_retention(session, ctx.a, 90, now=NOW) == {
            "tenant_id": str(ctx.a), "event_retention_days": 90}
    for days in (0, 91, True, "30", None):
        with ctx.owner.session() as session:
            with pytest.raises(ServiceError):
                administration.set_event_retention(session, ctx.a, days, now=NOW)
    with ctx.owner.session() as session:
        with pytest.raises(NotFound):
            administration.set_event_retention(session, uuid4(), 5, now=NOW)
    with ctx.owner.session() as session:
        assert session.get(Tenant, ctx.a).event_retention_days == 90
        rows = session.execute(select(AuditEvent.actor_type, AuditEvent.action, AuditEvent.object_type,
            AuditEvent.object_id).where(AuditEvent.tenant_id == ctx.a, AuditEvent.action == "tenant_event_retention_set")).all()
    assert [tuple(row) for row in rows] == [("local_admin", "tenant_event_retention_set", "tenant", ctx.a)]
    assert audit_count(ctx.owner, ctx.a) == before + 1


def test_runtime_role_holds_exactly_the_event_grants(pg_service_databases):
    _, runtime = pg_service_databases
    expected = {("endpoint_events", "SELECT"): True, ("endpoint_events", "INSERT"): True,
                ("endpoint_events", "DELETE"): True, ("endpoint_events", "UPDATE"): False,
                ("endpoint_events", "TRUNCATE"): False, ("device_event_cursors", "SELECT"): True,
                ("device_event_cursors", "INSERT"): True, ("device_event_cursors", "UPDATE"): True,
                ("device_event_cursors", "DELETE"): False, ("device_event_cursors", "TRUNCATE"): False}
    with runtime.session() as session:
        actual = {(table, privilege): session.scalar(text("SELECT has_table_privilege(current_user, :table, :privilege)"),
                  {"table": table, "privilege": privilege}) for table, privilege in expected}
        assert actual == expected
        assert session.scalar(text("SELECT has_column_privilege(current_user, 'tenants', 'event_retention_days', "
                                   "'UPDATE')")) is False


def database_url(database):
    # Only an already-owned engine supplies the URL; never assert on or print it.
    return database.engine.url.render_as_string(hide_password=False)


def test_events_prune_cli_runs_only_with_the_runtime_credential(event_tenants, monkeypatch, capsys):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    real_now = datetime.now(timezone.utc)
    send(ctx.runtime, device, batch(1, sensor(1)), now=real_now - timedelta(days=40))
    send(ctx.runtime, device, batch(2, sensor(2)), now=real_now - timedelta(days=1))
    monkeypatch.delenv("SP_DATABASE_URL", raising=False)
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["events", "prune"]) == 1
    assert "SP_DATABASE_URL is required" in capsys.readouterr().err
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["events", "prune"]) == 1
    assert "unprivileged runtime database role" in capsys.readouterr().err
    assert sequences(ctx.owner, device) == [1, 2]
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.runtime))
    assert cli.main(["events", "prune"]) == 0
    output = capsys.readouterr()
    summary = json.loads(output.out)
    assert set(summary) == {"tenants", "deleted_events", "devices", "failed_tenants"}
    assert all(type(value) is int and value >= 0 for value in summary.values()) and summary["deleted_events"] >= 1
    assert summary["failed_tenants"] == 0
    assert "postgresql" not in output.out + output.err and output.err == ""
    assert sequences(ctx.owner, device) == [2] and stored(ctx.owner, device)[1].stored_events == 1


def test_set_event_retention_cli_needs_the_owner_credential(event_tenants, monkeypatch, capsys):
    ctx = event_tenants
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["set-event-retention", "--tenant-id", str(ctx.a), "--days", "7"]) == 0
    assert json.loads(capsys.readouterr().out) == {"tenant_id": str(ctx.a), "event_retention_days": 7}
    for days in ("0", "91"):
        assert cli.main(["set-event-retention", "--tenant-id", str(ctx.a), "--days", days]) == 1
        assert "Invalid event retention" in capsys.readouterr().err
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", database_url(ctx.runtime))
    assert cli.main(["set-event-retention", "--tenant-id", str(ctx.a), "--days", "9"]) == 1
    assert "Database operation failed" in capsys.readouterr().err
    with ctx.owner.session() as session:
        assert session.get(Tenant, ctx.a).event_retention_days == 7


EVENT_TABLES = ("endpoint_events", "device_event_cursors")


def event_schema(connection):
    """Reflected names of everything migration 0002 creates."""
    inspector = inspect(connection)
    present = set(inspector.get_table_names())
    shape = {"tenants": ({column["name"] for column in inspector.get_columns("tenants")} & {"event_retention_days"},
                         {item["name"] for item in inspector.get_check_constraints("tenants")})}
    for table in EVENT_TABLES:
        if table in present:
            shape[table] = ({column["name"] for column in inspector.get_columns(table)},
                            {item["name"] for item in inspector.get_check_constraints(table)},
                            {item["name"] for item in inspector.get_foreign_keys(table)},
                            {item["name"] for item in inspector.get_indexes(table)},
                            tuple(inspector.get_pk_constraint(table)["constrained_columns"]))
    return shape


def model_schema():
    from sqlalchemy import CheckConstraint, ForeignKeyConstraint
    from security_platform.db import Base
    shape = {"tenants": ({"event_retention_days"}, {"ck_tenant_event_retention"})}
    for name in EVENT_TABLES:
        table = Base.metadata.tables[name]
        shape[name] = ({column.name for column in table.columns},
                       {item.name for item in table.constraints if isinstance(item, CheckConstraint)},
                       {item.name for item in table.constraints if isinstance(item, ForeignKeyConstraint)},
                       {index.name for index in table.indexes},
                       tuple(column.name for column in table.primary_key.columns))
    return shape


def test_migrated_event_schema_matches_the_models(pg_service_databases):
    owner, _ = pg_service_databases
    with owner.engine.connect() as connection:
        assert event_schema(connection) == model_schema()
        default = connection.execute(text("SELECT column_default FROM information_schema.columns "
            "WHERE table_name = 'tenants' AND column_name = 'event_retention_days'")).scalar_one()
    assert default == "30"


def test_cap_deletion_counter_is_defined_alike_in_migration_and_model(pg_service_databases):
    from sqlalchemy import BigInteger, CheckConstraint
    owner, _ = pg_service_databases
    with owner.engine.connect() as connection:
        migrated = connection.execute(text(
            "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'device_event_cursors' "
            "AND column_name = 'cap_deleted_events'")).one()
        check = connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_event_cursor_cap_deleted_events' "
            "AND conrelid = 'public.device_event_cursors'::regclass")).scalar_one()
    assert tuple(migrated) == ("bigint", "NO", "0")
    assert check == "CHECK ((cap_deleted_events >= 0))"
    table = DeviceEventCursor.__table__
    column = table.c.cap_deleted_events
    assert isinstance(column.type, BigInteger) and column.nullable is False and column.server_default.arg.text == "0"
    assert [item.sqltext.text for item in table.constraints if isinstance(item, CheckConstraint)
            and item.name == "ck_event_cursor_cap_deleted_events"] == ["cap_deleted_events >= 0"]


def migration_module(name):
    spec = importlib.util.spec_from_file_location("migration_" + name, PROJECT / "migrations/versions" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_0002_downgrades_and_upgrades_in_a_rolled_back_transaction(pg_service_databases):
    owner, _ = pg_service_databases
    module, alerts_migration = migration_module("0002_endpoint_events"), migration_module("0003_alerts")
    assert (module.revision, module.down_revision) == ("0002_endpoint_events", "0001_initial")
    assert alerts_migration.down_revision == module.revision
    expected = model_schema()
    # 0003 adds suppressed_alerts and its CHECK to the cursor table; the rest is 0002's.
    columns, checks, foreign_keys, indexes, primary_key = expected["device_event_cursors"]
    at_0002 = {**expected, "device_event_cursors": (columns - {"suppressed_alerts"},
        checks - {"ck_event_cursor_suppressed_alerts"}, foreign_keys, indexes, primary_key)}
    with owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            with Operations.context(MigrationContext.configure(connection)):
                assert event_schema(connection) == expected
                alerts_migration.downgrade()
                assert event_schema(connection) == at_0002
                module.downgrade()
                assert event_schema(connection) == {"tenants": (set(), set())}
                module.upgrade()
                assert event_schema(connection) == at_0002
                alerts_migration.upgrade()
                assert event_schema(connection) == expected
        finally:
            transaction.rollback()
