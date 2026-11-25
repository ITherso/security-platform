"""Real PostgreSQL alerts: the rules inside ingestion, deduplication, the per-device open-alert cap, the
operator lifecycle, a close racing an ingestion, and migration 0003.

HTTP/JWT acceptance of the three alert routes is in test_alerts_api.py; the rules as pure functions are
in tests/unit/test_alert_rules.py.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta
import threading
import time
from uuid import UUID, uuid4

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import func, inspect, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from security_platform.auth.principals import OperatorPrincipal
from security_platform.models import Alert, AuditEvent, DeviceEventCursor, Principal
from security_platform.services import administration, alerts, enrollment, events
from security_platform.services.common import (DEFAULT_LIMITS, Conflict, ContentTooLarge, EventCursorConflict,
    Forbidden, NotFound, ServiceError, Unauthorized, UnprocessableContent)
from test_events import PROJECT, batch, event_tenants, migration_module, send, stored  # noqa: F401  (shared fixtures)
from test_services import NOW, enrolled, pg_service_databases  # noqa: F401  (shared real-database fixture)


pytestmark = pytest.mark.integration
VOLUME = r"\Device\HarddiskVolume3"
NEUTRAL = VOLUME + r"\Windows\System32\svchost.exe"
WORD = VOLUME + r"\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"
OUTLOOK = VOLUME + r"\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE"
EXCEL = VOLUME + r"\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"
CHROME = VOLUME + r"\Program Files\Google\Chrome\Application\chrome.exe"
EDGE = VOLUME + r"\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
NOTEPAD = VOLUME + r"\Windows\notepad.exe"
sha = alerts.dedup_key


def path(*parts):
    return "\\".join((VOLUME, *parts))


def downloads(name):
    return path("Users", "*", "Downloads", name)


def tool(name):
    return path("Windows", "System32", name)


def launch(seq, image=NEUTRAL, *, pid=None, parent=4):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2030-01-02T03:00:00Z",
            "pid": 5000 + seq if pid is None else pid, "parent_pid": parent, "session_id": 1, "image": image}


def stop(seq, pid):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2030-01-02T03:00:01Z", "pid": pid,
            "exit_code": 0, "image": None}


def state(seq, value="lost", code=None):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:02Z", "state": value,
            "error_code": code}


def at(seconds):
    return NOW + timedelta(seconds=seconds)


def alert_rows(owner, device, rule=None):
    """The device's alerts in opening order."""
    with owner.session() as session:
        query = select(Alert).where(Alert.device_id == UUID(device["device_id"]))
        if rule is not None:
            query = query.where(Alert.rule == rule)
        return session.scalars(query.order_by(Alert.created_at, Alert.first_event_seq, Alert.rule)).all()


def suppressed(owner, device):
    return stored(owner, device)[1].suppressed_alerts


def transition(ctx, action, alert_id, *, operator=None, tenant=None, now=NOW):
    with ctx.runtime.session() as session:
        return getattr(alerts, action)(session, operator or ctx.admin_a, tenant or ctx.a, alert_id, now=now)


# Rules ---------------------------------------------------------------------------------------------


def test_user_writable_launches_open_low_alerts_keyed_by_the_casefolded_image(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    appdata = path("Users", "*", "AppData", "Local", "Temp", "x.exe")
    other_case = path("USERS", "*", "appdata", "LOCAL", "temp", "X.EXE")
    stream = path("Users", "*:stream", "AppData", "f.exe")
    near = [path("Windows", "Temporary", "a.exe"), path("Windows", "MyTemp", "b.exe"), path("Tools", "temp.exe"),
            path("Users", "*", "Documents", "c.exe"), path("Users", "*", "Desktop", "AppData", "d.exe"),
            path("ProgramData", "AppData", "e.exe")]
    send(ctx.runtime, device, batch(1, launch(1, appdata), *[launch(2 + index, image) for index, image in enumerate(near)],
                                    launch(8, other_case), launch(9, stream), launch(10, "D:/Temp/g.exe")))
    rows = alert_rows(ctx.owner, device)
    assert [(row.rule, row.severity, row.dedup_key, row.occurrences, row.first_event_seq, row.last_event_seq,
             row.evidence) for row in rows] == [
        # The same image in another case is the same key; the evidence is the latest match.
        ("user_writable_launch", "low", sha(appdata.casefold()), 2, 1, 8, {"image": other_case, "pid": 5008}),
        ("user_writable_launch", "low", sha(stream.casefold()), 1, 9, 9, {"image": stream, "pid": 5009}),
        ("user_writable_launch", "low", sha("d:/temp/g.exe"), 1, 10, 10, {"image": "D:/Temp/g.exe", "pid": 5010}),
    ]
    for row in rows:
        assert (row.status, row.first_seen_at, row.last_seen_at, row.created_at, row.updated_at) == (
            "open", NOW, NOW, NOW, NOW)
        assert (row.tenant_id, row.acknowledged_at, row.acknowledged_by, row.closed_at, row.closed_by) == (
            ctx.a, None, None, None, None)


def test_office_or_browser_parents_are_found_in_the_batch_first_then_in_stored_events(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, batch(1, launch(1, WORD, pid=100), launch(2, CHROME, pid=200), launch(3, OUTLOOK, pid=300),
                                    stop(4, 300), launch(5, EXCEL, pid=400), launch(6, WORD, pid=600),
                                    launch(7, NOTEPAD, pid=600)))
    assert alert_rows(ctx.owner, device) == []
    send(ctx.runtime, device, batch(2,
        launch(8, tool("rundll32.exe"), parent=200),     # Chrome, stored: found
        launch(9, tool("cmd.exe"), parent=300),          # Outlook stopped before (stored): none
        stop(10, 400),
        launch(11, tool("wscript.exe"), parent=400),     # Excel's stop in this batch wins over its stored start
        launch(12, EDGE, pid=500),
        launch(13, tool("certutil.exe"), parent=500),    # Edge in this batch: found
        launch(14, NOTEPAD, pid=100),
        launch(15, tool("powershell.exe"), parent=100),  # pid reuse in this batch: Notepad, not Word
        launch(16, tool("schtasks.exe"), parent=600)),   # pid reuse in stored events: Notepad, not Word
        now=at(1))
    rows = alert_rows(ctx.owner, device)
    assert [(row.rule, row.severity, row.dedup_key, row.occurrences, row.first_event_seq, row.evidence)
            for row in rows] == [
        ("office_browser_spawned_tool", "medium", sha("chrome.exe>rundll32.exe"), 1, 8,
         {"image": tool("rundll32.exe"), "pid": 5008, "parent_image": CHROME, "parent_pid": 200}),
        ("office_browser_spawned_tool", "medium", sha("msedge.exe>certutil.exe"), 1, 13,
         {"image": tool("certutil.exe"), "pid": 5013, "parent_image": EDGE, "parent_pid": 500}),
    ]
    # The same pair under another parent process updates the same alert.
    send(ctx.runtime, device, batch(3, launch(17, CHROME, pid=700), launch(18, tool("RunDLL32.EXE"), parent=700)),
         now=at(2))
    first = alert_rows(ctx.owner, device)[0]
    assert (first.occurrences, first.last_event_seq, first.evidence["parent_pid"], first.last_seen_at) == (2, 18, 700, at(2))


def test_evidence_of_two_long_paths_fits_the_4_kib_check_as_postgresql_measures_it(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    wide = "\U0001F600"  # four UTF-8 bytes
    parent = path("Users", "*", "AppData", wide * 950, "WINWORD.EXE")
    child = path("Users", "*", "Downloads", wide * 950, "cmd.exe")
    # Each event fits its own 4 KiB; together the two paths do not.
    send(ctx.runtime, device, batch(1, launch(1, parent, pid=100), launch(2, child, parent=100)))
    [row] = alert_rows(ctx.owner, device, "office_browser_spawned_tool")
    assert row.evidence["image"].startswith("…") and row.evidence["image"].endswith("\\cmd.exe")
    assert row.evidence["parent_image"].startswith("…") and row.evidence["parent_image"].endswith("\\WINWORD.EXE")
    assert (row.evidence["pid"], row.evidence["parent_pid"]) == (5002, 100)
    with ctx.owner.session() as session:
        size = session.scalar(text("SELECT octet_length(evidence::text) FROM alerts WHERE id = :id"), {"id": row.id})
    assert 4096 - 8 <= size <= 4096 and size == alerts._stored_bytes(row.evidence)
    # Each launch's own alert keeps the whole image.
    assert {item.evidence["image"] for item in alert_rows(ctx.owner, device, "user_writable_launch")} == {parent, child}


@pytest.mark.parametrize("child,found", [(2010, True), (2011, False)])
def test_a_stored_parent_outside_the_2000_event_window_is_not_found(event_tenants, child, found):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, batch(1, launch(10, WORD, pid=100)))
    send(ctx.runtime, device, batch(2, launch(child, tool("cmd.exe"), parent=100)), now=at(1))
    office = [(row.dedup_key, row.first_event_seq) for row in alert_rows(ctx.owner, device, "office_browser_spawned_tool")]
    assert office == ([(sha("winword.exe>cmd.exe"), child)] if found else [])
    # The jump in event_seq is an event loss either way.
    assert [row.evidence for row in alert_rows(ctx.owner, device, "event_loss")] == [{"missing_events": child - 11}]


def test_a_pruned_parent_is_not_found(event_tenants):
    ctx = event_tenants
    with ctx.owner.session() as session:
        administration.set_event_retention(session, ctx.a, 1, now=NOW)
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, batch(1, launch(1, WORD, pid=100)), now=NOW - timedelta(days=2))
    assert events.prune_expired_events(ctx.runtime, now=NOW)["failed_tenants"] == 0
    assert stored(ctx.owner, device)[0] == []
    send(ctx.runtime, device, batch(2, launch(2, tool("cmd.exe"), parent=100)))
    assert alert_rows(ctx.owner, device) == []


def test_sensor_losses_and_failures_raise_medium_alerts_counted_per_state(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, batch(1, state(1, "started"), state(2, "lost", "session_in_use"), state(3, "lost"),
                                    state(4, "failed", "access_denied"), state(5, "stopped")))
    send(ctx.runtime, device, batch(2, state(6, "lost", "unknown")), now=at(1))
    assert [(row.rule, row.severity, row.dedup_key, row.occurrences, row.first_event_seq, row.last_event_seq,
             row.evidence, row.first_seen_at, row.last_seen_at) for row in alert_rows(ctx.owner, device)] == [
        ("sensor_unstable", "medium", sha("lost"), 3, 2, 6, {"state": "lost", "error_code": "unknown"}, NOW, at(1)),
        ("sensor_unstable", "medium", sha("failed"), 1, 4, 4, {"state": "failed", "error_code": "access_denied"},
         NOW, NOW),
    ]


def test_event_loss_counts_gaps_inside_and_across_batches_but_never_on_a_first_batch(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)

    def sensors(*seqs):
        return [state(seq, "started") for seq in seqs]

    # A first batch may start above 1 and have gaps: no loss without a cursor.
    send(ctx.runtime, device, batch(1, *sensors(5, 6, 9)))
    assert alert_rows(ctx.owner, device) == []
    send(ctx.runtime, device, batch(2, *sensors(10, 13, 14, 20)), now=at(1))   # 11-12 and 15-19 inside
    send(ctx.runtime, device, batch(3, *sensors(25)), now=at(2))               # 21-24 after the cursor
    send(ctx.runtime, device, batch(4, *sensors(26, 27)), now=at(3))           # contiguous
    [loss] = alert_rows(ctx.owner, device)
    assert (loss.rule, loss.severity, loss.dedup_key, loss.occurrences, loss.first_event_seq, loss.last_event_seq,
            loss.evidence, loss.first_seen_at, loss.last_seen_at) == (
        "event_loss", "medium", sha("event_loss"), 3, 13, 25, {"missing_events": 11}, at(1), at(2))
    transition(ctx, "close_alert", loss.id, now=at(4))
    send(ctx.runtime, device, batch(5, *sensors(30)), now=at(5))               # 28-29: a new alert
    closed, reopened = alert_rows(ctx.owner, device)
    assert (closed.id, closed.status, closed.occurrences, closed.evidence) == (loss.id, "closed", 3, {"missing_events": 11})
    assert (reopened.status, reopened.occurrences, reopened.first_event_seq, reopened.evidence) == (
        "open", 1, 30, {"missing_events": 2})
    # Another device's first batch with gaps raises nothing.
    other = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, other, batch(1, *sensors(100, 150, 400)))
    assert alert_rows(ctx.owner, other) == []


def test_matches_update_the_alert_until_it_is_closed_and_then_open_a_new_one(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    image = downloads("setup.exe")

    def shape(row):
        return (row.status, row.occurrences, row.first_event_seq, row.last_event_seq, row.first_seen_at,
                row.last_seen_at, row.created_at, row.updated_at, row.evidence)

    send(ctx.runtime, device, batch(1, launch(1, image), launch(2, image)), now=at(0))
    [first] = alert_rows(ctx.owner, device)
    assert shape(first) == ("open", 2, 1, 2, at(0), at(0), at(0), at(0), {"image": image, "pid": 5002})
    send(ctx.runtime, device, batch(2, launch(3, image)), now=at(10))
    [row] = alert_rows(ctx.owner, device)
    assert row.id == first.id and shape(row) == (
        "open", 3, 1, 3, at(0), at(10), at(0), at(10), {"image": image, "pid": 5003})
    # An acknowledged alert is not closed: later matches still update it.
    transition(ctx, "acknowledge_alert", first.id, now=at(15))
    send(ctx.runtime, device, batch(3, launch(4, image)), now=at(20))
    [row] = alert_rows(ctx.owner, device)
    assert shape(row) == ("acknowledged", 4, 1, 4, at(0), at(20), at(0), at(20), {"image": image, "pid": 5004})
    assert row.acknowledged_at == at(15)
    transition(ctx, "close_alert", first.id, now=at(25))
    send(ctx.runtime, device, batch(4, launch(5, image), launch(6, image)), now=at(30))
    closed, opened = alert_rows(ctx.owner, device)
    assert closed.id == first.id and shape(closed) == (
        "closed", 4, 1, 4, at(0), at(20), at(0), at(25), {"image": image, "pid": 5004})
    assert opened.id != first.id and opened.dedup_key == closed.dedup_key == sha(image.casefold())
    assert shape(opened) == ("open", 2, 5, 6, at(30), at(30), at(30), at(30), {"image": image, "pid": 5006})


def test_the_open_alert_cap_suppresses_openings_but_never_updates(event_tenants):
    ctx = event_tenants
    limits = replace(DEFAULT_LIMITS, max_open_alerts_per_device=10)
    device, neighbour = enrolled(ctx.runtime, ctx.admin_a, ctx.a), enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    images = [downloads(f"tool{number}.exe") for number in range(20)]

    def ingest(target, sequence, *pairs, seconds=0):
        send(ctx.runtime, target, batch(sequence, *[launch(seq, images[index]) for seq, index in pairs]),
             limits=limits, now=at(seconds))

    def open_images(target):
        return {row.evidence["image"]: row.occurrences for row in alert_rows(ctx.owner, target) if row.status != "closed"}

    ingest(device, 1, *[(seq, seq - 1) for seq in range(1, 10)])
    assert len(open_images(device)) == 9 and suppressed(ctx.owner, device) == 0
    # The first new key reaches the cap; the next two are suppressed; a repeat of an open key still updates.
    ingest(device, 2, (10, 9), (11, 10), (12, 11), (13, 0), seconds=1)
    assert open_images(device) == {**{images[index]: 1 for index in range(1, 10)}, images[0]: 2}
    assert suppressed(ctx.owner, device) == 2
    rows = alert_rows(ctx.owner, device)
    # An acknowledged alert still counts towards the cap.
    transition(ctx, "acknowledge_alert", rows[1].id, now=at(2))
    ingest(device, 3, (14, 12), seconds=3)
    assert images[12] not in open_images(device) and suppressed(ctx.owner, device) == 3
    # A close frees one slot: the first new key opens, the second is suppressed.
    transition(ctx, "close_alert", rows[2].id, now=at(4))
    ingest(device, 4, (15, 13), (16, 14), seconds=5)
    current = open_images(device)
    assert len(current) == 10 and images[13] in current and images[14] not in current
    assert suppressed(ctx.owner, device) == 4
    # A closed key's next match is a new opening, suppressed at the cap like any other.
    ingest(device, 5, (17, 2), seconds=6)
    assert [row.status for row in alert_rows(ctx.owner, device) if row.evidence["image"] == images[2]] == ["closed"]
    assert suppressed(ctx.owner, device) == 5 and len(alert_rows(ctx.owner, device)) == 11
    with ctx.runtime.session() as session:
        page = events.list_device_events(session, ctx.viewer_a, ctx.a, UUID(device["device_id"]), limit=1)
    assert (page["suppressed_alerts"], page["cap_deleted_events"]) == (5, 0)
    # The cap is per device.
    ingest(neighbour, 1, (1, 0), (2, 1), (3, 2))
    assert len(open_images(neighbour)) == 3 and suppressed(ctx.owner, neighbour) == 0


# Ingestion -----------------------------------------------------------------------------------------


def test_an_exact_retry_adds_no_alert_and_no_occurrence(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    message = batch(1, launch(1, downloads("a.exe")), state(2, "failed", "access_denied"))
    first = send(ctx.runtime, device, message)

    def snapshot():
        return [(row.id, row.occurrences, row.last_event_seq, row.last_seen_at, row.updated_at, row.evidence)
                for row in alert_rows(ctx.owner, device)]

    before = snapshot()
    assert len(before) == 2
    assert send(ctx.runtime, device, message, now=at(30)) == first
    assert snapshot() == before and suppressed(ctx.owner, device) == 0


def test_conflicting_oversized_or_invalid_batches_leave_no_alert(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    accepted = batch(5, launch(10), launch(11))
    send(ctx.runtime, device, accepted)
    matching = [launch(12, downloads("a.exe")), state(13, "lost")]
    for conflicting in (batch(5, *matching), batch(6, *matching, batch_id=accepted.batch_id), batch(4, *matching),
                        batch(6, launch(11, downloads("a.exe")), state(13, "lost"))):
        with pytest.raises(EventCursorConflict):
            send(ctx.runtime, device, conflicting, now=at(1))
    assert alert_rows(ctx.owner, device) == [] and [row.event_seq for row in stored(ctx.owner, device)[0]] == [10, 11]
    fresh = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    valid = batch(1, launch(1, downloads("a.exe")), state(2, "lost")).model_dump(mode="json")
    with pytest.raises(UnprocessableContent):
        send(ctx.runtime, fresh, {**valid, "events": [launch(1, downloads("a.exe")),
                                                      launch(2, path("Users", "ahmet", "Downloads", "b.exe"))]})
    oversized = {**valid, "events": [launch(seq, downloads("x" * 950 + ".exe")) for seq in range(1, 18)]}
    with pytest.raises(ContentTooLarge):
        send(ctx.runtime, fresh, oversized)
    assert alert_rows(ctx.owner, fresh) == [] and stored(ctx.owner, fresh) == ([], None)


def test_alerts_and_events_commit_together_and_roll_back_together(event_tenants, monkeypatch):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    message = batch(1, launch(1, downloads("a.exe")), state(2, "lost"))
    original, upserted = events._trim_to_cap, []

    def failing_trim(session, device_row, *arguments):
        # The alert upsert already ran in this transaction; the next statement fails.
        upserted.append(session.scalar(select(func.count()).select_from(Alert).where(Alert.device_id == device_row.id)))
        raise OperationalError("DELETE FROM endpoint_events", {}, Exception("canceling statement due to lock timeout"))

    monkeypatch.setattr(events, "_trim_to_cap", failing_trim)
    with pytest.raises(OperationalError):
        send(ctx.runtime, device, message)
    assert upserted == [2]
    assert alert_rows(ctx.owner, device) == [] and stored(ctx.owner, device) == ([], None)
    monkeypatch.setattr(events, "_trim_to_cap", original)
    send(ctx.runtime, device, message)
    rows, cursor = stored(ctx.owner, device)
    assert [row.event_seq for row in rows] == [1, 2] and cursor.suppressed_alerts == 0
    assert [row.rule for row in alert_rows(ctx.owner, device)] == ["user_writable_launch", "sensor_unstable"]


# Operator lifecycle --------------------------------------------------------------------------------


def alert_audit(owner, tenant):
    with owner.session() as session:
        return [tuple(row) for row in session.execute(select(AuditEvent.actor_type, AuditEvent.actor_id,
            AuditEvent.action, AuditEvent.object_type, AuditEvent.object_id).where(
            AuditEvent.tenant_id == tenant, AuditEvent.object_type == "alert").order_by(AuditEvent.created_at))]


def principal_id(owner, operator):
    with owner.session() as session:
        return session.scalar(select(Principal.id).where(Principal.issuer == operator.issuer,
                                                         Principal.subject == operator.subject))


def test_lifecycle_transitions_roles_and_audit(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, batch(1, launch(1, downloads("a.exe")), state(2, "lost")))
    first, second = alert_rows(ctx.owner, device)
    admin = principal_id(ctx.owner, ctx.admin_a)
    stranger = OperatorPrincipal(issuer="https://other-issuer.example", subject=ctx.admin_a.subject)
    for operator, tenant, alert_id, error in (
            (ctx.viewer_a, ctx.a, first.id, Forbidden), (ctx.admin_b, ctx.a, first.id, NotFound),
            (ctx.admin_b, ctx.b, first.id, NotFound), (ctx.admin_a, ctx.a, uuid4(), NotFound),
            (stranger, ctx.a, first.id, NotFound), (None, ctx.a, first.id, Unauthorized)):
        for action in ("acknowledge_alert", "close_alert"):
            with ctx.runtime.session() as session:
                with pytest.raises(error):
                    getattr(alerts, action)(session, operator, tenant, alert_id, now=at(1))
    assert alert_audit(ctx.owner, ctx.a) == [] and alert_audit(ctx.owner, ctx.b) == []
    acknowledged = transition(ctx, "acknowledge_alert", first.id, now=at(2))
    assert (acknowledged["status"], acknowledged["acknowledged_at"], acknowledged["closed_at"]) == (
        "acknowledged", "2030-01-02T03:04:07Z", None)
    assert transition(ctx, "acknowledge_alert", first.id, now=at(3)) == acknowledged
    closed = transition(ctx, "close_alert", first.id, now=at(4))
    assert (closed["status"], closed["acknowledged_at"], closed["closed_at"]) == (
        "closed", "2030-01-02T03:04:07Z", "2030-01-02T03:04:09Z")
    assert transition(ctx, "close_alert", first.id, now=at(5)) == closed
    with pytest.raises(Conflict, match="^Alert is closed$"):
        transition(ctx, "acknowledge_alert", first.id, now=at(6))
    directly = transition(ctx, "close_alert", second.id, now=at(7))
    assert (directly["status"], directly["acknowledged_at"], directly["closed_at"]) == (
        "closed", None, "2030-01-02T03:04:12Z")
    with ctx.owner.session() as session:
        rows = {row.id: row for row in session.scalars(select(Alert).where(Alert.device_id == first.device_id))}
    assert (rows[first.id].acknowledged_by, rows[first.id].closed_by, rows[first.id].updated_at) == (admin, admin, at(4))
    assert (rows[second.id].acknowledged_by, rows[second.id].closed_by) == (None, admin)
    # One row per real transition, none for the repeats or the refusals; the row names the alert only.
    assert alert_audit(ctx.owner, ctx.a) == [("operator", admin, "alert_acknowledged", "alert", first.id),
                                             ("operator", admin, "alert_closed", "alert", first.id),
                                             ("operator", admin, "alert_closed", "alert", second.id)]


def test_the_alert_list_pages_by_last_activity_with_ties_filters_and_bounds(event_tenants):
    ctx = event_tenants
    device, other = enrolled(ctx.runtime, ctx.admin_a, ctx.a), enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    foreign = enrolled(ctx.runtime, ctx.admin_b, ctx.b)
    # Five alerts from one batch share last_seen_at; the id breaks the tie.
    send(ctx.runtime, device, batch(1, *[launch(seq, downloads(f"{seq}.exe")) for seq in range(1, 6)]), now=at(0))
    send(ctx.runtime, other, batch(1, launch(1, downloads("1.exe")), state(2, "failed")), now=at(1))
    # A later match moves an older alert to the front.
    send(ctx.runtime, device, batch(2, launch(6, downloads("3.exe"))), now=at(2))
    send(ctx.runtime, foreign, batch(1, launch(1, downloads("1.exe"))), now=at(3))
    with ctx.owner.session() as session:
        rows = session.scalars(select(Alert).where(Alert.tenant_id == ctx.a)).all()
    expected = [str(row.id) for row in sorted(rows, key=lambda row: (row.last_seen_at, row.id), reverse=True)]
    assert len(expected) == 7

    def listing(operator=ctx.viewer_a, **options):
        with ctx.runtime.session() as session:
            return alerts.list_alerts(session, operator, ctx.a, **options)

    pages, cursor = [], {}
    while True:
        page = listing(limit=2, **cursor)
        pages.append([item["id"] for item in page["items"]])
        if page["next_before"] is None:
            break
        last = page["items"][-1]
        assert page["next_before"]["id"] == last["id"] and len(page["next_before"]["seen_at"]) == 27
        cursor = {"before_seen_at": page["next_before"]["seen_at"], "before_id": UUID(page["next_before"]["id"])}
    assert [len(page) for page in pages] == [2, 2, 2, 1] and sum(pages, []) == expected
    everything = listing(limit=100)
    assert [item["id"] for item in everything["items"]] == expected and everything["next_before"] is None
    assert everything["items"][0]["evidence"]["image"] == downloads("3.exe")
    assert {item["device_id"] for item in listing(device_id=UUID(other["device_id"]))["items"]} == {other["device_id"]}
    assert len(listing(device_id=UUID(device["device_id"]))["items"]) == 5
    transition(ctx, "acknowledge_alert", UUID(expected[0]), now=at(4))
    transition(ctx, "close_alert", UUID(expected[1]), now=at(5))
    assert [item["id"] for item in listing(status="acknowledged")["items"]] == [expected[0]]
    assert [item["id"] for item in listing(status="closed")["items"]] == [expected[1]]
    assert [item["id"] for item in listing(status="open")["items"]] == expected[2:]
    # The acknowledged alert is the first device's: the other device has none.
    assert listing(status="acknowledged", device_id=UUID(other["device_id"])) == {"items": [], "next_before": None}
    for device_id in (UUID(foreign["device_id"]), uuid4()):
        with pytest.raises(NotFound):
            listing(device_id=device_id)
    for operator in (ctx.admin_b, None):
        with pytest.raises((NotFound, Unauthorized)):
            listing(operator=operator)
    for options in ({"limit": 0}, {"limit": 101}, {"limit": True}, {"status": "resolved"}, {"device_id": "x"},
                    {"before_seen_at": "2030-01-02T03:04:05.000000Z"}, {"before_id": uuid4()},
                    {"before_seen_at": "2030-01-02T03:04:05Z", "before_id": uuid4()}):
        with pytest.raises(ServiceError):
            listing(**options)


# Concurrency ---------------------------------------------------------------------------------------


def lock_waiting(runtime, backend, done):
    """True once PostgreSQL reports the backend in `backend["pid"]` waiting for a lock."""
    deadline = time.monotonic() + 2.5
    while time.monotonic() < deadline and not done.is_set():
        if "pid" in backend:
            # Wait details are visible to sessions of the same role.
            with runtime.session() as session:
                if session.scalar(text("SELECT wait_event_type = 'Lock' FROM pg_stat_activity WHERE pid=:pid"),
                                  {"pid": backend["pid"]}) is True:
                    return True
        done.wait(timeout=0.01)
    return False


def ingest_in(session, device, message, now):
    principal = enrollment.authenticate_device(session, device["credential_secret"], now=now)
    return events.ingest_events(session, principal, message, now=now)


def test_a_close_holding_the_alert_makes_a_racing_match_open_a_new_alert(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    image = downloads("race.exe")
    send(ctx.runtime, device, batch(1, launch(1, image)))
    [alert] = alert_rows(ctx.owner, device)
    closing, release, done, backend = threading.Event(), threading.Event(), threading.Event(), {}

    def close():
        with ctx.runtime.session() as session:
            view = alerts.close_alert(session, ctx.admin_a, ctx.a, alert.id, now=at(1))
            closing.set()
            assert release.wait(timeout=5)
            return view

    def ingest():
        try:
            with ctx.runtime.session() as session:
                backend["pid"] = session.scalar(text("SELECT pg_backend_pid()"))
                return ingest_in(session, device, batch(2, launch(2, image)), at(2))
        finally:
            done.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        closer = pool.submit(close)
        assert closing.wait(timeout=5)
        ingester = pool.submit(ingest)
        try:
            blocked = lock_waiting(ctx.runtime, backend, done)
        finally:
            release.set()
        assert closer.result(timeout=10)["status"] == "closed"
        assert ingester.result(timeout=10)["last_event_seq"] == 2
    assert blocked, "the upsert did not wait for the close"
    assert [(row.id == alert.id, row.status, row.occurrences, row.first_event_seq, row.last_event_seq)
            for row in alert_rows(ctx.owner, device)] == [(True, "closed", 1, 1, 1), (False, "open", 1, 2, 2)]


def test_an_ingestion_holding_the_alert_makes_a_racing_close_include_its_match(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    image = downloads("race.exe")
    send(ctx.runtime, device, batch(1, launch(1, image)))
    [alert] = alert_rows(ctx.owner, device)
    upserted, release, done, backend = threading.Event(), threading.Event(), threading.Event(), {}

    def ingest():
        with ctx.runtime.session() as session:
            acceptance = ingest_in(session, device, batch(2, launch(2, image)), at(1))
            upserted.set()
            assert release.wait(timeout=5)
            return acceptance

    def close():
        try:
            with ctx.runtime.session() as session:
                backend["pid"] = session.scalar(text("SELECT pg_backend_pid()"))
                return alerts.close_alert(session, ctx.admin_a, ctx.a, alert.id, now=at(2))
        finally:
            done.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        ingester = pool.submit(ingest)
        assert upserted.wait(timeout=5)
        closer = pool.submit(close)
        try:
            blocked = lock_waiting(ctx.runtime, backend, done)
        finally:
            release.set()
        assert ingester.result(timeout=10)["last_event_seq"] == 2
        view = closer.result(timeout=10)
    assert blocked, "the close did not wait for the upsert"
    assert (view["status"], view["occurrences"], view["last_event_seq"]) == ("closed", 2, 2)
    assert [(row.id, row.status, row.occurrences) for row in alert_rows(ctx.owner, device)] == [(alert.id, "closed", 2)]


def test_racing_closes_and_ingestions_never_leave_two_alerts_open_or_fail(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    image = downloads("loop.exe")
    sequence = 1
    send(ctx.runtime, device, batch(sequence, launch(sequence, image)), now=at(sequence))
    for _ in range(12):
        not_closed = [row for row in alert_rows(ctx.owner, device) if row.status != "closed"]
        if not not_closed:
            sequence += 1
            send(ctx.runtime, device, batch(sequence, launch(sequence, image)), now=at(sequence))
            not_closed = [row for row in alert_rows(ctx.owner, device) if row.status != "closed"]
        [current] = not_closed
        sequence += 1
        barrier = threading.Barrier(2)

        def close(alert_id=current.id, now=at(sequence)):
            with ctx.runtime.session() as session:
                barrier.wait(timeout=5)
                return alerts.close_alert(session, ctx.admin_a, ctx.a, alert_id, now=now)

        def ingest(number=sequence):
            with ctx.runtime.session() as session:
                principal = enrollment.authenticate_device(session, device["credential_secret"], now=at(number))
                barrier.wait(timeout=5)
                return events.ingest_events(session, principal, batch(number, launch(number, image)), now=at(number))

        with ThreadPoolExecutor(max_workers=2) as pool:
            closer, ingester = pool.submit(close), pool.submit(ingest)
            # Neither side ever fails.
            assert closer.result(timeout=10)["status"] == "closed"
            assert ingester.result(timeout=10)["last_event_seq"] == sequence
        rows = alert_rows(ctx.owner, device)
        after = {row.id: row for row in rows}[current.id]
        left_open = [row for row in rows if row.status != "closed"]
        assert after.status == "closed" and len(left_open) <= 1
        if left_open:
            # The close won: the match opened a new alert and the closed one kept its count.
            assert (left_open[0].occurrences, left_open[0].first_event_seq) == (1, sequence)
            assert after.occurrences == current.occurrences and after.last_event_seq < sequence
        else:
            # The ingestion won: the closed alert includes the match.
            assert (after.occurrences, after.last_event_seq) == (current.occurrences + 1, sequence)
    # Every match is counted exactly once over all alerts of the key.
    rows = alert_rows(ctx.owner, device)
    assert sum(row.occurrences for row in rows) == sequence and len({row.dedup_key for row in rows}) == 1


# Migration, constraints and grants -----------------------------------------------------------------


ALERT_COLUMNS = {
    "id": ("uuid", "NO", None), "tenant_id": ("uuid", "NO", None), "device_id": ("uuid", "NO", None),
    "rule": ("text", "NO", None), "severity": ("text", "NO", None), "dedup_key": ("character", "NO", 64),
    "status": ("text", "NO", None), "occurrences": ("bigint", "NO", None),
    "first_event_seq": ("bigint", "NO", None), "last_event_seq": ("bigint", "NO", None),
    "first_seen_at": ("timestamp with time zone", "NO", None), "last_seen_at": ("timestamp with time zone", "NO", None),
    "evidence": ("jsonb", "NO", None), "acknowledged_at": ("timestamp with time zone", "YES", None),
    "acknowledged_by": ("uuid", "YES", None), "closed_at": ("timestamp with time zone", "YES", None),
    "closed_by": ("uuid", "YES", None), "created_at": ("timestamp with time zone", "NO", None),
    "updated_at": ("timestamp with time zone", "NO", None),
}
ALERT_INDEXES = {
    "alerts_pkey": "CREATE UNIQUE INDEX alerts_pkey ON public.alerts USING btree (id)",
    "uq_alert_not_closed_key": "CREATE UNIQUE INDEX uq_alert_not_closed_key ON public.alerts USING btree "
                               "(tenant_id, device_id, rule, dedup_key) WHERE (status <> 'closed'::text)",
    "ix_alert_tenant_seen": "CREATE INDEX ix_alert_tenant_seen ON public.alerts USING btree "
                            "(tenant_id, last_seen_at DESC, id DESC)",
    "ix_alert_device_seen": "CREATE INDEX ix_alert_device_seen ON public.alerts USING btree "
                            "(tenant_id, device_id, last_seen_at DESC, id DESC)",
}
ALERT_FOREIGN_KEYS = {
    "fk_alert_tenant_device": (("tenant_id", "device_id"), "devices", ("tenant_id", "id")),
    "fk_alert_acknowledger_membership": (("tenant_id", "acknowledged_by"), "memberships", ("tenant_id", "principal_id")),
    "fk_alert_closer_membership": (("tenant_id", "closed_by"), "memberships", ("tenant_id", "principal_id")),
}


def alert_schema(connection):
    """Reflected alerts table (None when absent) and the cursor's suppressed_alerts column."""
    inspector = inspect(connection)
    cursor_columns = {column["name"] for column in inspector.get_columns("device_event_cursors")}
    if "alerts" not in inspector.get_table_names():
        return None, "suppressed_alerts" in cursor_columns
    columns = {row[0]: tuple(row[1:]) for row in connection.execute(text(
        "SELECT column_name, data_type, is_nullable, character_maximum_length FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = 'alerts'"))}
    indexes = dict(connection.execute(text(
        "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'alerts'")).all())
    checks = {item["name"] for item in inspector.get_check_constraints("alerts")}
    foreign_keys = {item["name"]: (tuple(item["constrained_columns"]), item["referred_table"],
                                   tuple(item["referred_columns"])) for item in inspector.get_foreign_keys("alerts")}
    primary_key = tuple(inspector.get_pk_constraint("alerts")["constrained_columns"])
    return (columns, indexes, checks, foreign_keys, primary_key), "suppressed_alerts" in cursor_columns


def model_checks():
    from sqlalchemy import CheckConstraint
    return {item.name for item in Alert.__table__.constraints if isinstance(item, CheckConstraint)}


def test_migrated_alert_table_matches_the_model(pg_service_databases):
    owner, _ = pg_service_databases
    with owner.engine.connect() as connection:
        schema, has_counter = alert_schema(connection)
        counter = connection.execute(text(
            "SELECT data_type, is_nullable, column_default FROM information_schema.columns WHERE table_schema = "
            "'public' AND table_name = 'device_event_cursors' AND column_name = 'suppressed_alerts'")).one()
        check = connection.execute(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'ck_event_cursor_suppressed_alerts' "
            "AND conrelid = 'public.device_event_cursors'::regclass")).scalar_one()
        head = connection.scalar(text("SELECT version_num FROM alembic_version"))
    columns, indexes, checks, foreign_keys, primary_key = schema
    table = Alert.__table__
    assert columns == ALERT_COLUMNS and set(columns) == {column.name for column in table.columns}
    assert {name: nullable == "YES" for name, (_, nullable, _) in columns.items()} == {
        column.name: column.nullable for column in table.columns}
    assert indexes == ALERT_INDEXES and set(indexes) - {"alerts_pkey"} == {index.name for index in table.indexes}
    [partial] = [index for index in table.indexes if index.unique]
    assert (partial.name, str(partial.dialect_options["postgresql"]["where"])) == (
        "uq_alert_not_closed_key", "status <> 'closed'")
    assert checks == model_checks() == {
        "ck_alert_rule", "ck_alert_severity", "ck_alert_dedup_key", "ck_alert_status", "ck_alert_occurrences",
        "ck_alert_event_seq", "ck_alert_evidence_object", "ck_alert_evidence_bytes", "ck_alert_acknowledgement",
        "ck_alert_closure", "ck_alert_lifecycle"}
    assert foreign_keys == ALERT_FOREIGN_KEYS and primary_key == ("id",)
    assert has_counter and tuple(counter) == ("bigint", "NO", "0") and check == "CHECK ((suppressed_alerts >= 0))"
    column = DeviceEventCursor.__table__.c.suppressed_alerts
    assert column.nullable is False and column.server_default.arg.text == "0"
    # 0004 (Snapshot V2) follows 0003 and changes only product_states.ck_product_id.
    assert head == "0004_edr_agent_product"


def test_the_alembic_chain_is_linear_up_to_0004():
    script = ScriptDirectory.from_config(Config(str(PROJECT / "alembic.ini")))
    assert script.get_heads() == ["0004_edr_agent_product"]
    assert [(revision.revision, revision.down_revision) for revision in script.walk_revisions()] == [
        ("0004_edr_agent_product", "0003_alerts"), ("0003_alerts", "0002_endpoint_events"),
        ("0002_endpoint_events", "0001_initial"), ("0001_initial", None)]


def test_migration_0003_upgrades_a_0002_database_in_a_rolled_back_transaction(event_tenants):
    ctx = event_tenants
    device_id = UUID(enrolled(ctx.runtime, ctx.admin_a, ctx.a)["device_id"])
    module = migration_module("0003_alerts")
    assert (module.revision, module.down_revision) == ("0003_alerts", "0002_endpoint_events")
    with ctx.owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            head, counter = alert_schema(connection)
            assert head is not None and counter
            with Operations.context(MigrationContext.configure(connection)):
                module.downgrade()
                assert alert_schema(connection) == (None, False)
                # A cursor written at 0002 gets suppressed_alerts = 0 from the upgrade.
                connection.execute(text(
                    "INSERT INTO device_event_cursors (tenant_id, device_id, last_batch_sequence, last_batch_id, "
                    "last_batch_digest, last_event_seq, last_received_at, stored_events, cap_deleted_events) "
                    "VALUES (:tenant, :device, 1, :batch, :digest, 7, :at, 1, 0)"),
                    {"tenant": ctx.a, "device": device_id, "batch": uuid4(), "digest": "a" * 64, "at": NOW})
                module.upgrade()
                assert alert_schema(connection) == (head, True)
                assert connection.scalar(text("SELECT suppressed_alerts FROM device_event_cursors "
                                              "WHERE device_id = :device"), {"device": device_id}) == 0
        finally:
            transaction.rollback()
    with ctx.owner.engine.connect() as connection:
        assert alert_schema(connection) == (head, True)


CONSTRAINT_CASES = {
    "rule": {"rule": "network_beacon"}, "severity": {"severity": "high"},
    "dedup_key_upper": {"dedup_key": "A" * 64}, "dedup_key_short": {"dedup_key": "a" * 63},
    "status": {"status": "resolved"}, "occurrences": {"occurrences": 0},
    "first_event_seq": {"first_event_seq": 0, "last_event_seq": 0},
    "event_seq_order": {"first_event_seq": 5, "last_event_seq": 4},
    "evidence_array": {"evidence": ["image"]}, "evidence_bytes": {"evidence": {"image": "a" * 4096}},
    "acknowledged_without_principal": {"status": "acknowledged", "acknowledged_at": NOW},
    "closed_without_principal": {"status": "closed", "closed_at": NOW},
    "acknowledged_without_time": {"status": "acknowledged"}, "closed_without_time": {"status": "closed"},
    "open_but_acknowledged": {"acknowledged_at": NOW, "acknowledged_by": "admin"},
    "open_but_closed": {"closed_at": NOW, "closed_by": "admin"},
    "acknowledged_but_closed": {"status": "acknowledged", "acknowledged_at": NOW, "acknowledged_by": "admin",
                                "closed_at": NOW, "closed_by": "admin"},
    "foreign_tenant_device": {"tenant_id": "b"},
    "closer_without_membership": {"status": "closed", "closed_at": NOW, "closed_by": "outsider"},
}


@pytest.mark.parametrize("case", sorted(CONSTRAINT_CASES) + ["cursor_suppressed_alerts", "second_open_key"])
def test_database_constraints_back_the_alert_contract(event_tenants, case):
    ctx = event_tenants
    device_id = UUID(enrolled(ctx.runtime, ctx.admin_a, ctx.a)["device_id"])
    principals = {"admin": principal_id(ctx.owner, ctx.admin_a), "outsider": principal_id(ctx.owner, ctx.admin_b)}
    row = {"tenant_id": ctx.a, "device_id": device_id, "rule": "user_writable_launch", "severity": "low",
           "dedup_key": "a" * 64, "status": "open", "occurrences": 1, "first_event_seq": 1, "last_event_seq": 1,
           "first_seen_at": NOW, "last_seen_at": NOW, "evidence": {"image": downloads("a.exe"), "pid": 1},
           "created_at": NOW, "updated_at": NOW}
    cursor = {"tenant_id": ctx.a, "device_id": device_id, "last_batch_sequence": 1, "last_batch_id": uuid4(),
              "last_batch_digest": "a" * 64, "last_event_seq": 1, "last_received_at": NOW, "stored_events": 0,
              "cap_deleted_events": 0, "suppressed_alerts": 0}
    # The unchanged rows are valid, and so is a closed alert beside an open one of the same key.
    with ctx.owner.session_factory() as session:
        session.add_all([Alert(**row), Alert(**{**row, "status": "closed", "closed_at": NOW,
                                                "closed_by": principals["admin"]}), DeviceEventCursor(**cursor)])
        session.flush()
        session.rollback()
    with pytest.raises(IntegrityError):
        with ctx.owner.session() as session:
            if case == "cursor_suppressed_alerts":
                session.add(DeviceEventCursor(**{**cursor, "suppressed_alerts": -1}))
            elif case == "second_open_key":
                session.add_all([Alert(**row), Alert(**{**row, "status": "acknowledged", "acknowledged_at": NOW,
                                                        "acknowledged_by": principals["admin"]})])
            else:
                change = dict(CONSTRAINT_CASES[case])
                for key in ("acknowledged_by", "closed_by"):
                    if key in change:
                        change[key] = principals[change[key]]
                if change.get("tenant_id") == "b":
                    change["tenant_id"] = ctx.b
                session.add(Alert(**{**row, **change}))


def test_runtime_role_can_raise_and_update_alerts_but_never_delete_them(pg_service_databases):
    _, runtime = pg_service_databases
    granted = {"SELECT", "INSERT", "UPDATE"}
    expected = {privilege: privilege in granted
                for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")}
    with runtime.session() as session:
        actual = {privilege: session.scalar(text("SELECT has_table_privilege(current_user, 'alerts', :privilege)"),
                                            {"privilege": privilege}) for privilege in expected}
        assert session.scalar(text("SELECT has_column_privilege(current_user, 'device_event_cursors', "
                                   "'suppressed_alerts', 'UPDATE')")) is True
    assert actual == expected
