"""Real PostgreSQL for the Stage 3 rules: the five event rules, the exact parent of a v2 child, and
`security-platform sweep` with its agent_silent alert.

The rules as pure functions are in tests/unit/test_alert_rules.py; the Stage 2 rules, the upsert races and the
alert lifecycle in test_alerts.py; the alert routes in test_alerts_api.py. Device times are before NOW
(2030-01-02T03:04:05Z). The sweep runs on the server clock it is given. Each sweep here is restricted to the
test's own tenants (sweep._tenants), because the shared test database keeps the tenants of earlier runs.
"""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from functools import partial
import json
import re
import time
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event as sqlalchemy_event, select, text
from sqlalchemy.exc import OperationalError

from security_platform import cli
from security_platform.event_contracts import (AGENT_STATE_SUBJECTS, BEHAVIOR_RULES, EVENT_FIELDS, EVENT_MODELS_V2,
    MAX_STORED_EVENT_BYTES)
from security_platform.models import Alert, Device
from security_platform.services import alerts, enrollment, snapshots, sweep
from security_platform.services.common import DEFAULT_LIMITS, UnprocessableContent, canonical_utc, iso
from test_api import api_context, api_database, auth, enroll  # noqa: F401  (shared HTTP fixtures)
from test_events import database_url, event_tenants, send, stored  # noqa: F401  (shared fixtures)
from test_services import NOW, enrolled, pg_service_databases  # noqa: F401  (shared real-database fixture)


pytestmark = pytest.mark.integration
VOLUME = r"\Device\HarddiskVolume3"
NEUTRAL = VOLUME + r"\Windows\System32\svchost.exe"
NOTEPAD = VOLUME + r"\Windows\notepad.exe"
WORD = VOLUME + r"\Program Files\Microsoft Office\root\Office16\WINWORD.EXE"
EXCEL = VOLUME + r"\Program Files\Microsoft Office\root\Office16\EXCEL.EXE"
OUTLOOK = VOLUME + r"\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE"
CHROME = VOLUME + r"\Program Files\Google\Chrome\Application\chrome.exe"
EDGE = VOLUME + r"\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
SETUP = VOLUME + r"\Users\*\Downloads\setup.exe"
WIDE = "\U0001F600"  # four UTF-8 bytes
SHA_A = "a1" * 32
ENTRY_A, ENTRY_B = "c3" * 32, "d4" * 32
RULE_SET = "e5" * 32
# The brief's section 8 table: the five event rules with their severities.
EVENT_RULE_SEVERITY = {"scan_detection": "medium", "behavior_match": "medium", "persistence_added": "low",
                       "capability_down": "medium", "tamper_signal": "medium"}
# The agent_state pairs that raise capability_down (brief section 8); every other pair raises nothing.
CAPABILITY_DOWN_PAIRS = {"realtime_scan": ("stopped", "failed"), "rule_set": ("missing", "invalid", "unreadable"),
                         "file_change_sensor": ("failed",), "command_line_sensor": ("failed",),
                         "persistence_watch": ("failed",), "response_channel": ("journal_invalid",)}
ALERT_KEYS = {"id", "device_id", "rule", "severity", "status", "occurrences", "first_event_seq", "last_event_seq",
              "first_seen_at", "last_seen_at", "evidence", "acknowledged_at", "closed_at", "source",
              "producer_verification"}
SILENCE = 900  # the default SP_SILENCE_ALERT_SECONDS
FIRST_CONTACT = "2030-01-02T03:04:05.000000Z"  # NOW as canonical UTC text: the first episode's key text
sha = alerts.dedup_key


def tool(name):
    return VOLUME + "\\Windows\\System32\\" + name


def downloads(name):
    return VOLUME + "\\Users\\*\\Downloads\\" + name


def wide(folder, count, name):
    """A masked user path whose middle component is `count` four-byte characters."""
    return "\\".join((VOLUME, "Users", "*", folder, WIDE * count, name))


def instant(microseconds):
    """A distinct canonical process create time."""
    return canonical_utc(datetime(2030, 1, 2, 1, 0, tzinfo=timezone.utc) + timedelta(microseconds=microseconds))


WRONG = instant(999999)  # no process of the tests below was created then
REUSED = instant(100000)  # pid 100's second process


def at(seconds):
    return NOW + timedelta(seconds=seconds)


# --- v1 and v2 events

def started(seq, image=NEUTRAL, *, pid=None, parent=4, created=None, parent_created=None):
    pid = 5000 + seq if pid is None else pid
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2030-01-02T03:00:00Z", "pid": pid,
            "parent_pid": parent, "session_id": 1, "image": image,
            "create_time": instant(pid) if created is None else created, "parent_create_time": parent_created}


def stopped(seq, pid, created=None):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2030-01-02T03:00:01Z", "pid": pid,
            "exit_code": 0, "image": None, "create_time": created}


def v1_started(seq, image=NEUTRAL, *, pid=None, parent=4):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2030-01-02T03:00:00Z",
            "pid": 5000 + seq if pid is None else pid, "parent_pid": parent, "session_id": 1, "image": image}


def v1_stopped(seq, pid):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2030-01-02T03:00:01Z", "pid": pid,
            "exit_code": 0, "image": None}


def sensor(seq, state="started", code=None):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:02Z", "state": state,
            "error_code": code}


def scan(seq, **changes):
    return {"kind": "scan_detected", "event_seq": seq, "observed_at": "2030-01-02T03:00:03Z", "trigger": "file_change",
            "path": SETUP, "size": 68, "sha256": SHA_A, "rule_set_id": RULE_SET,
            "hits": [{"rule": "Sample_Rule", "severity": "high"}], "omitted_hits": 0, "pid": 4321,
            "create_time": instant(4321), "action_id": None, **changes}


def behavior(seq, **changes):
    return {"kind": "behavior_match", "event_seq": seq, "observed_at": "2030-01-02T03:00:04Z",
            "rule": "encoded_powershell", "rule_version": 3, "pid": 4322, "create_time": instant(4322),
            "image": tool("powershell.exe"), "parent_image": WORD, "found_at_start": False,
            "command_line_source": "kernel_logger", **changes}


def persistence(seq, **changes):
    return {"kind": "persistence_change", "event_seq": seq, "observed_at": "2030-01-02T03:00:05Z",
            "location": "run_key", "scope": "user", "change": "added", "entry_id": ENTRY_A, "target_image": SETUP,
            "found_at_start": False, **changes}


def agent(seq, subject, state, **changes):
    return {"kind": "agent_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:06Z", "subject": subject,
            "state": state, "code": None, "rule_set_id": RULE_SET if subject == "rule_set" else None, **changes}


def tamper(seq, signal="service_config_changed", detail=None):
    return {"kind": "tamper_signal", "event_seq": seq, "observed_at": "2030-01-02T03:00:07Z", "signal": signal,
            "detail": detail}


def gap(seq, **changes):
    return {"kind": "coverage_gap", "event_seq": seq, "observed_at": "2030-01-02T03:00:08Z", "source": "process_sensor",
            "reason": "etw_events_lost", "lost": 12, **changes}


def v2(sequence, *items):
    return {"schema_version": 2, "batch_id": str(uuid4()), "batch_sequence": sequence, "events": list(items)}


def v1(sequence, *items):
    return {"schema_version": 1, "batch_id": str(uuid4()), "batch_sequence": sequence, "events": list(items)}


def fill(ctx, device, sequence, first, count, now):
    """`count` neutral v2 events from event_seq `first`, 100 per batch; return the next batch sequence."""
    for start in range(first, first + count, 100):
        send(ctx.runtime, device, v2(sequence, *[sensor(seq) for seq in range(start, min(start + 100, first + count))]),
             now=now)
        sequence += 1
    return sequence


# --- reading back

def alert_rows(owner, device, rule=None):
    """The device's alerts in opening order."""
    with owner.session() as session:
        query = select(Alert).where(Alert.device_id == UUID(device["device_id"]))
        if rule is not None:
            query = query.where(Alert.rule == rule)
        return session.scalars(query.order_by(Alert.created_at, Alert.first_event_seq, Alert.rule, Alert.id)).all()


def payloads(owner, device):
    """The device's stored event payloads by event_seq."""
    return {row.event_seq: row.payload for row in stored(owner, device)[0]}


def own_fields(payload):
    """A stored event's own fields: its kind's timeline fields, under the same names."""
    return {name: payload[name] for name in EVENT_FIELDS[payload["kind"]]}


def stored_size(owner, sql, **parameters):
    with owner.session() as session:
        return session.scalar(text(sql), parameters)


def transition(ctx, action, alert_id, now):
    with ctx.runtime.session() as session:
        return getattr(alerts, action)(session, ctx.admin_a, ctx.a, alert_id, now=now)


def spy(monkeypatch, name):
    """Record the arguments of every call of an alerts.py function, which still runs."""
    calls, original = [], getattr(alerts, name)

    def recording(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(alerts, name, recording)
    return calls


@contextmanager
def statements(database):
    """Every SQL statement text the database's engine sends meanwhile."""
    seen = []

    def record(connection, cursor, statement, parameters, context, executemany):
        seen.append(statement)

    sqlalchemy_event.listen(database.engine, "before_cursor_execute", record)
    try:
        yield seen
    finally:
        sqlalchemy_event.remove(database.engine, "before_cursor_execute", record)


def exact_parent_statements(seen):
    return sum("CROSS JOIN LATERAL" in statement for statement in seen)


# --- the five event rules -----------------------------------------------------------------------------------

def test_each_stage3_event_rule_opens_its_alert_with_the_events_own_fields(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    later_scan = scan(13, trigger="startup_scan", path=VOLUME + r"\Users\*\AppData\Local\Temp\b.dll", pid=None,
                      create_time=None, hits=[{"rule": "Other_Rule", "severity": "low"}], omitted_hits=2)
    send(ctx.runtime, device, v2(1,
        scan(1), behavior(2), persistence(3), persistence(4, change="removed", entry_id=ENTRY_B),
        agent(5, "realtime_scan", "failed"), agent(6, "realtime_scan", "degraded"),
        agent(7, "file_change_sensor", "not_available"), agent(8, "service", "stopping"),
        agent(9, "rule_set", "compiled"), tamper(10, "event_log_cleared", "security"), gap(11),
        sensor(12, "started"), later_scan))
    keys = {"scan_detection": SHA_A, "behavior_match": "encoded_powershell>" + tool("powershell.exe").casefold(),
            "persistence_added": ENTRY_A, "capability_down": "realtime_scan", "tamper_signal": "event_log_cleared"}
    sequences = {"scan_detection": (2, 1, 13), "behavior_match": (1, 2, 2), "persistence_added": (1, 3, 3),
                 "capability_down": (1, 5, 5), "tamper_signal": (1, 10, 10)}
    rows = {row.rule: row for row in alert_rows(ctx.owner, device)}
    # A removal, degraded, not_available, stopping, compiled, a coverage gap and a started sensor raise nothing.
    assert set(rows) == set(EVENT_RULE_SEVERITY)
    latest = payloads(ctx.owner, device)
    for rule, row in rows.items():
        assert (row.severity, row.occurrences, row.first_event_seq, row.last_event_seq) == (
            EVENT_RULE_SEVERITY[rule], *sequences[rule]), rule
        assert (row.dedup_key, row.status, row.first_seen_at, row.last_seen_at) == (sha(keys[rule]), "open", NOW, NOW)
        # The latest triggering event's own fields, unshortened.
        assert row.evidence == own_fields(latest[row.last_event_seq]), rule
    # A "high" hit is the scanner's rule metadata; the alert's severity is the server's.
    assert rows["scan_detection"].evidence == {
        "trigger": "startup_scan", "path": VOLUME + r"\Users\*\AppData\Local\Temp\b.dll", "size": 68, "sha256": SHA_A,
        "rule_set_id": RULE_SET, "hits": [{"rule": "Other_Rule", "severity": "low"}], "omitted_hits": 2, "pid": None,
        "create_time": None, "action_id": None}
    assert rows["capability_down"].evidence == {"subject": "realtime_scan", "state": "failed", "code": None,
                                                "rule_set_id": None}
    assert rows["tamper_signal"].evidence == {"signal": "event_log_cleared", "detail": "security"}


def test_stage3_matches_update_the_open_alert_until_it_is_closed_and_then_open_a_new_one(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)

    def round_of_matches(sequence, first, seconds, later):
        send(ctx.runtime, device, v2(sequence, scan(first, size=first), behavior(first + 1, found_at_start=later),
             persistence(first + 2, change="modified" if later else "added"),
             agent(first + 3, "realtime_scan", "stopped" if later else "failed"),
             tamper(first + 4, "previous_run_unclean")), now=at(seconds))

    round_of_matches(1, 1, 0, False)
    round_of_matches(2, 6, 10, True)
    first = {row.rule: row for row in alert_rows(ctx.owner, device)}
    assert set(first) == set(EVENT_RULE_SEVERITY)
    latest = payloads(ctx.owner, device)
    for row in first.values():
        assert (row.status, row.occurrences, row.first_seen_at, row.last_seen_at) == ("open", 2, NOW, at(10))
        assert row.last_event_seq == row.first_event_seq + 5 and row.evidence == own_fields(latest[row.last_event_seq])
    # A modification raises persistence_added too, and capability_down keeps the subject's latest state.
    assert (first["persistence_added"].evidence["change"], first["capability_down"].evidence["state"]) == (
        "modified", "stopped")
    for row in first.values():
        transition(ctx, "close_alert", row.id, at(20))
    round_of_matches(3, 11, 30, True)
    rows = alert_rows(ctx.owner, device)
    closed = {row.id: row for row in rows if row.status == "closed"}
    reopened = {row.rule: row for row in rows if row.status == "open"}
    assert set(closed) == {row.id for row in first.values()} and all(row.occurrences == 2 for row in closed.values())
    assert set(reopened) == set(first) and len(rows) == 10
    for rule, row in reopened.items():
        assert (row.dedup_key, row.occurrences, row.first_seen_at, row.first_event_seq) == (
            first[rule].dedup_key, 1, at(30), first[rule].first_event_seq + 10)


def test_capability_down_opens_exactly_on_the_listed_pairs_of_every_agent_state(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    pairs = [(subject, state) for subject, states in AGENT_STATE_SUBJECTS.items() for state in states]
    seq_of = {pair: seq for seq, pair in enumerate(pairs, start=1)}
    send(ctx.runtime, device, v2(1, *[
        agent(seq, subject, state, code="clean_stop" if (subject, state) == ("service", "started") else None)
        for (subject, state), seq in seq_of.items()]))
    rows = {row.dedup_key: row for row in alert_rows(ctx.owner, device)}
    assert {row.rule for row in rows.values()} == {"capability_down"}
    assert set(rows) == {sha(subject) for subject in CAPABILITY_DOWN_PAIRS}
    latest = payloads(ctx.owner, device)
    for subject, states in CAPABILITY_DOWN_PAIRS.items():
        row = rows[sha(subject)]
        assert (row.severity, row.occurrences, row.first_event_seq, row.last_event_seq) == (
            "medium", len(states), seq_of[(subject, states[0])], seq_of[(subject, states[-1])]), subject
        assert row.evidence == own_fields(latest[row.last_event_seq])
        assert (row.evidence["subject"], row.evidence["state"]) == (subject, states[-1])
    assert rows[sha("rule_set")].evidence["rule_set_id"] == RULE_SET


def test_a_behavior_match_alerts_severity_is_the_servers_per_rule_and_never_the_events(event_tenants, monkeypatch):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, v2(1, *[behavior(seq, rule=rule) for seq, rule in enumerate(BEHAVIOR_RULES, start=1)]))
    image = tool("powershell.exe").casefold()
    assert {row.dedup_key: row.severity for row in alert_rows(ctx.owner, device, "behavior_match")} == {
        sha(f"{rule}>{image}"): "medium" for rule in BEHAVIOR_RULES}
    # The server's table decides per rule id: changed here, where no event could have chosen it.
    monkeypatch.setattr(alerts, "BEHAVIOR_SEVERITY", {**alerts.BEHAVIOR_SEVERITY, "shadow_copy_deletion": "low"})
    send(ctx.runtime, device, v2(2, behavior(11, rule="shadow_copy_deletion", image=tool("wmic.exe")),
                                 behavior(12, image=tool("pwsh.exe"))), now=at(1))
    assert {row.dedup_key: row.severity for row in alert_rows(ctx.owner, device, "behavior_match")
            if row.first_event_seq > 10} == {sha("shadow_copy_deletion>" + tool("wmic.exe").casefold()): "low",
                                             sha("encoded_powershell>" + tool("pwsh.exe").casefold()): "medium"}
    # An event that carries a severity is refused whole: nothing stored and nothing raised.
    before = (stored(ctx.owner, device)[1].last_batch_sequence, len(alert_rows(ctx.owner, device)))
    for severity in ("low", "medium", "high"):
        with pytest.raises(UnprocessableContent):
            send(ctx.runtime, device, v2(3, behavior(13, rule="bitsadmin_transfer", severity=severity)), now=at(2))
    assert (stored(ctx.owner, device)[1].last_batch_sequence, len(alert_rows(ctx.owner, device))) == before
    assert max(payloads(ctx.owner, device)) == 12


MAXIMAL_HITS = [{"rule": f"R{index}" + "x" * 62, "severity": "high"} for index in range(8)]
MAXIMAL = {
    "scan_detection": lambda count: scan(1, path=wide("Downloads", count, "sample.dll"), size=2**53 - 1,
        hits=MAXIMAL_HITS, omitted_hits=4096, pid=2**32 - 1, create_time=instant(1),
        action_id="ffffffff-ffff-ffff-ffff-ffffffffffff"),
    "behavior_match": lambda count: behavior(1, rule="defender_tampering_command", rule_version=65535,
        pid=2**32 - 1, image=wide("AppData", count, "powershell.exe"),
        parent_image=wide("Downloads", count, "WINWORD.EXE"), found_at_start=True, command_line_source="process_query"),
    "persistence_added": lambda count: persistence(1, location="scheduled_task", scope="machine", change="modified",
        target_image=wide("AppData", count, "updater.exe"), found_at_start=True),
}


def largest(build):
    """build(count) for the largest count its v2 model accepts: the event then fills its own 4 KiB."""
    low, high = 0, 1024
    while low < high:
        middle = (low + high + 1) // 2
        candidate = build(middle)
        try:
            EVENT_MODELS_V2[candidate["kind"]].model_validate(candidate)
        except ValueError:
            high = middle - 1
        else:
            low = middle
    return build(low)


@pytest.mark.parametrize("rule", sorted(MAXIMAL))
def test_the_evidence_of_a_maximal_event_is_its_own_fields_unshortened_within_4_kib(event_tenants, rule):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, v2(1, largest(MAXIMAL[rule])))
    [row] = alert_rows(ctx.owner, device, rule)
    event_size = stored_size(ctx.owner, "SELECT octet_length(payload::text) FROM endpoint_events "
                             "WHERE device_id = :device AND event_seq = 1", device=UUID(device["device_id"]))
    evidence_size = stored_size(ctx.owner, "SELECT octet_length(evidence::text) FROM alerts WHERE id = :id",
                                id=row.id)
    # The event fills its own 4 KiB payload CHECK as PostgreSQL measures it...
    assert MAX_STORED_EVENT_BYTES - 8 < event_size <= MAX_STORED_EVENT_BYTES
    # ...and its evidence is its own fields, whole, under the 4 KiB evidence CHECK.
    assert row.evidence == own_fields(payloads(ctx.owner, device)[1])
    assert alerts.ELLIPSIS not in json.dumps(row.evidence, ensure_ascii=False)
    assert evidence_size == alerts._stored_bytes(row.evidence) < event_size


def test_office_evidence_of_two_maximal_v2_processes_matched_by_exact_identity_is_bounded(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    parent = largest(lambda count: started(1, wide("AppData", count, "WINWORD.EXE"), pid=100))
    child = largest(lambda count: started(2, wide("Downloads", count, "cmd.exe"), pid=200, parent=100,
                                          parent_created=instant(100)))
    send(ctx.runtime, device, v2(1, parent))
    send(ctx.runtime, device, v2(2, child), now=at(1))
    [row] = alert_rows(ctx.owner, device, "office_browser_spawned_tool")
    assert row.dedup_key == sha("winword.exe>cmd.exe") and (row.evidence["pid"], row.evidence["parent_pid"]) == (200, 100)
    assert row.evidence["image"].startswith(alerts.ELLIPSIS) and row.evidence["image"].endswith("\\cmd.exe")
    assert (row.evidence["parent_image"].startswith(alerts.ELLIPSIS)
            and row.evidence["parent_image"].endswith("\\WINWORD.EXE"))
    size = stored_size(ctx.owner, "SELECT octet_length(evidence::text) FROM alerts WHERE id = :id", id=row.id)
    assert alerts.MAX_EVIDENCE_BYTES - 8 <= size <= alerts.MAX_EVIDENCE_BYTES and size == alerts._stored_bytes(row.evidence)


# --- the exact parent of a v2 child -------------------------------------------------------------------------

def test_a_v2_childs_exact_parent_is_found_in_the_batch_or_in_stored_events_at_any_distance(event_tenants,
                                                                                            monkeypatch):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    # WORD's create time as a shorter text of the instant the children name: stored canonical, matched canonical.
    send(ctx.runtime, device, v2(1, started(1, WORD, pid=100, created="2030-01-02T01:00:00.0001Z"),
                                 started(2, CHROME, pid=200), stopped(3, 200, instant(200)), started(4, EXCEL, pid=300)))
    # 2600 stored events: every parent above is now outside the 2000-event window.
    sequence = fill(ctx, device, 2, 5, 2600, at(1))
    send(ctx.runtime, device, v2(sequence, started(2605, EXCEL, pid=302)), now=at(2))  # inside the window
    exact, window = spy(monkeypatch, "_stored_exact_parents"), spy(monkeypatch, "_stored_process_events")
    with statements(ctx.runtime) as seen:
        send(ctx.runtime, device, v2(sequence + 1,
            # Stored WORD, 2605 events back.
            started(2606, tool("cmd.exe"), pid=601, parent=100, parent_created=instant(100)),
            # No parent_create_time: the window, which no longer reaches WORD.
            started(2607, tool("wscript.exe"), pid=602, parent=100),
            # Stored CHROME, although it stopped: the identity is exact, so there is no stop check.
            started(2608, tool("mshta.exe"), pid=603, parent=200, parent_created=instant(200)),
            # A wrong identity is no parent, stored outside or inside the window or in the batch: no fallback.
            started(2609, tool("rundll32.exe"), pid=604, parent=300, parent_created=WRONG),
            started(2610, tool("msbuild.exe"), pid=605, parent=302, parent_created=WRONG),
            started(2611, EXCEL, pid=301),
            started(2612, tool("regsvr32.exe"), pid=606, parent=301, parent_created=WRONG),
            # In the batch.
            started(2613, EDGE, pid=400),
            started(2614, tool("certutil.exe"), pid=607, parent=400, parent_created=instant(400)),
            # pid 100 reused: the named create time still picks WORD; the reuse's own child sees NOTEPAD.
            started(2615, NOTEPAD, pid=100, created=REUSED),
            started(2616, tool("powershell.exe"), pid=608, parent=100, parent_created=instant(100)),
            started(2617, tool("schtasks.exe"), pid=609, parent=100, parent_created=REUSED),
            started(2618, tool("bitsadmin.exe"), pid=610, parent=100),
            # A parent later in the batch than its child is no parent.
            started(2619, tool("wmic.exe"), pid=611, parent=500, parent_created=instant(500)),
            started(2620, OUTLOOK, pid=500),
            # The batch's own parent after its stop.
            stopped(2621, 400, instant(400)),
            started(2622, tool("cscript.exe"), pid=612, parent=400, parent_created=instant(400))), now=at(3))
    # One stored lookup, in one statement, for every identity the batch did not resolve itself.
    assert [args[2] for args in exact] == [{(100, instant(100)), (200, instant(200)), (300, WRONG), (302, WRONG),
                                            (301, WRONG), (500, instant(500))}]
    assert exact_parent_statements(seen) == 1
    # The window ran once, for the one child without parent_create_time whose parent pid had no earlier batch event.
    assert [[child.event_seq for child, _ in args[2]] for args in window] == [[2607]]

    def spawned(image, pid, parent_image, parent_pid):
        return {"image": tool(image), "pid": pid, "parent_image": parent_image, "parent_pid": parent_pid}

    expected = {sha("winword.exe>cmd.exe"): (2606, spawned("cmd.exe", 601, WORD, 100)),
                sha("chrome.exe>mshta.exe"): (2608, spawned("mshta.exe", 603, CHROME, 200)),
                sha("msedge.exe>certutil.exe"): (2614, spawned("certutil.exe", 607, EDGE, 400)),
                sha("winword.exe>powershell.exe"): (2616, spawned("powershell.exe", 608, WORD, 100)),
                sha("msedge.exe>cscript.exe"): (2622, spawned("cscript.exe", 612, EDGE, 400))}
    office = {row.dedup_key: (row.first_event_seq, row.evidence)
              for row in alert_rows(ctx.owner, device, "office_browser_spawned_tool")}
    assert office == expected
    # Children that all name their parents: one stored lookup and no window at all.
    exact.clear()
    window.clear()
    with statements(ctx.runtime) as seen:
        send(ctx.runtime, device, v2(sequence + 2,
            started(2623, tool("pwsh.exe"), pid=613, parent=200, parent_created=instant(200)),
            started(2624, tool("installutil.exe"), pid=614, parent=100, parent_created=instant(100))), now=at(4))
    assert (len(exact), window, exact_parent_statements(seen)) == (1, [], 1)
    office = {row.dedup_key for row in alert_rows(ctx.owner, device, "office_browser_spawned_tool")}
    assert office == set(expected) | {sha("chrome.exe>pwsh.exe"), sha("winword.exe>installutil.exe")}
    # The numbering is contiguous (no event_loss) and no other rule matched.
    assert {row.rule for row in alert_rows(ctx.owner, device)} == {"office_browser_spawned_tool"}


def test_a_v1_stored_parent_is_never_an_exact_parent_but_stays_in_the_window(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, v1(1, v1_started(1, WORD, pid=100), v1_started(2, CHROME, pid=200)))
    send(ctx.runtime, device, v2(2, started(3, tool("cmd.exe"), pid=301, parent=100, parent_created=instant(100)),
                                 started(4, tool("wscript.exe"), pid=302, parent=100),
                                 started(5, tool("mshta.exe"), pid=303, parent=200, parent_created=instant(200))),
         now=at(1))
    assert [row.dedup_key for row in alert_rows(ctx.owner, device)] == [sha("winword.exe>wscript.exe")]


def plan_indexes(plan):
    """The names of every index an EXPLAIN (FORMAT JSON) plan tree uses."""
    found = {plan["Index Name"]} if "Index Name" in plan else set()
    for child in plan.get("Plans", []):
        found |= plan_indexes(child)
    return found


def test_the_exact_parent_statement_uses_the_process_identity_index_in_custom_and_generic_plans(event_tenants):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    send(ctx.runtime, device, v2(1, *[started(seq, pid=seq) for seq in range(1, 41)]))
    names = ["pids", "create_times", "tenant_id", "device_id", "first_seq"]
    source = alerts._EXACT_PARENTS.text
    assert sorted(set(re.findall(r":(\w+)", source))) == sorted(names)
    generic = re.sub(r":(\w+)", lambda found: f"${names.index(found.group(1)) + 1}", source)
    parameters = {"pids": ["7", "8", "77"], "create_times": [instant(7), instant(8), instant(77)], "tenant_id": ctx.a,
                  "device_id": UUID(device["device_id"]), "first_seq": 41}
    with ctx.owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.execute(text("ANALYZE endpoint_events"))
            # A plan that cannot use the index still shows a (penalised) sequential scan.
            connection.execute(text("SET LOCAL enable_seqscan = off"))
            custom = connection.execute(text("EXPLAIN (FORMAT JSON) " + source), parameters).scalar()
            # Sent unprepared: a prepared EXPLAIN would itself demand the $n parameters.
            with connection.connection.dbapi_connection.cursor() as cursor:
                cursor.execute("EXPLAIN (GENERIC_PLAN, FORMAT JSON) " + generic, prepare=False)
                generic_plan = cursor.fetchone()[0]
            rows = connection.execute(alerts._EXACT_PARENTS, parameters).all()
        finally:
            transaction.rollback()
    assert "ix_endpoint_events_process_identity" in plan_indexes(custom[0]["Plan"]), custom
    assert "ix_endpoint_events_process_identity" in plan_indexes(generic_plan[0]["Plan"]), generic_plan
    # One row per identity that has a stored parent before first_seq; the unknown identity has none.
    assert sorted(tuple(row) for row in rows) == [("7", instant(7), NEUTRAL), ("8", instant(8), NEUTRAL)]


def test_v2_shapes_of_the_v1_kinds_without_parent_create_times_raise_exactly_the_v1_alerts(event_tenants):
    ctx = event_tenants
    twins = [enrolled(ctx.runtime, ctx.admin_a, ctx.a) for _ in range(2)]
    first = [v1_started(1, WORD, pid=100), v1_started(2, tool("cmd.exe"), parent=100), v1_started(3, SETUP),
             sensor(4, "lost", "session_in_use"), v1_started(5, CHROME, pid=200), v1_stopped(6, 200),
             v1_started(7, tool("mshta.exe"), parent=200)]
    second = [v1_started(10, tool("wscript.exe"), parent=100), sensor(11, "failed", "access_denied"),
              v1_started(13, SETUP)]

    def upgraded(item):
        """The v2 shape: the same fields plus create_time, and no parent_create_time."""
        if item["kind"] == "process_started":
            return {**item, "create_time": instant(item["pid"])}
        if item["kind"] == "process_stopped":
            return {**item, "create_time": None}
        return item

    for device, version, shape in ((twins[0], v1, dict), (twins[1], v2, upgraded)):
        send(ctx.runtime, device, version(1, *map(shape, first)))
        send(ctx.runtime, device, version(2, *map(shape, second)), now=at(1))

    def alerts_of(device):
        return {(row.rule, row.dedup_key): (row.severity, row.occurrences, row.first_event_seq, row.last_event_seq,
                                            row.evidence, row.first_seen_at, row.last_seen_at)
                for row in alert_rows(ctx.owner, device)}

    v1_alerts = alerts_of(twins[0])
    assert v1_alerts == alerts_of(twins[1])
    assert {rule for rule, _ in v1_alerts} == {"user_writable_launch", "office_browser_spawned_tool", "sensor_unstable",
                                              "event_loss"}
    # The Stage 2 results: Chrome had stopped, WORD was found in the batch and then in the window.
    assert {key for rule, key in v1_alerts if rule == "office_browser_spawned_tool"} == {
        sha("winword.exe>cmd.exe"), sha("winword.exe>wscript.exe")}
    assert v1_alerts[("event_loss", sha("event_loss"))][4] == {"missing_events": 3}
    assert v1_alerts[("user_writable_launch", sha(SETUP.casefold()))][1] == 2


# --- security-platform sweep: agent_silent ------------------------------------------------------------------

HBF = {"product_id": "hostbasedfirewall", "status": "running", "firewall_mode": "enforce", "reported_running": True}


def agent_v3(interval=60, **changes):
    return {"product_id": "edr_agent", "status": "running", "rule_set_state": "compiled", "rule_set_id": RULE_SET,
            "heartbeat_interval_seconds": interval, **changes}


def agent_v2(**changes):
    return {"product_id": "edr_agent", "status": "running", "rule_file_present": True, "sensor_state": "started",
            **changes}


def snapshot(version, sequence, *products):
    return {"schema_version": version, "message_id": str(uuid4()), "sequence": sequence, "products": list(products)}


def report(runtime, device, body, now):
    with runtime.session() as session:
        principal = enrollment.authenticate_device(session, device["credential_secret"], now=now)
        return snapshots.ingest_snapshot(session, principal, body, now=now)


def revoke(ctx, device, now):
    with ctx.runtime.session() as session:
        enrollment.revoke_device(session, ctx.admin_a, ctx.a, UUID(device["device_id"]), now=now)


def swept(monkeypatch, *tenants):
    """Restrict this test's sweeps to its own tenants."""
    monkeypatch.setattr(sweep, "_tenants", lambda session: sorted(tenants))


def run(ctx, now, setting=SILENCE, **options):
    return sweep.sweep_silent_agents(ctx.runtime, silence_alert_seconds=setting, now=now, **options)


def counts(**values):
    """A sweep result: every count zero but the given ones, for the two fixture tenants."""
    return {"tenants": 2, "failed_tenants": 0, "devices_checked": 0, "alerts_opened": 0, "already_alerted": 0,
            "suppressed": 0, "devices_busy": 0, **values}


def by_id(devices):
    return sorted(devices, key=lambda device: UUID(device["device_id"]))


def test_the_sweep_lists_every_tenant_in_id_order(event_tenants):
    ctx = event_tenants
    with ctx.runtime.session() as session:
        tenants = sweep._tenants(session)
    assert {ctx.a, ctx.b} <= set(tenants) and tenants == sorted(tenants)


def test_the_sweep_opens_agent_silent_past_the_larger_of_the_setting_and_three_heartbeats(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a, ctx.b)
    names = ("v3_60", "v3_600", "v3_none", "v2", "fresh", "hbf", "v2_without_agent", "v3_without_agent", "dropped",
             "revoked", "never")
    devices = {name: enrolled(ctx.runtime, ctx.admin_a, ctx.a) for name in names}
    other = enrolled(ctx.runtime, ctx.admin_b, ctx.b)
    for name, body in (("v3_60", snapshot(3, 1, HBF, agent_v3(60))), ("v3_600", snapshot(3, 1, agent_v3(600))),
                       ("v3_none", snapshot(3, 1, agent_v3(None))), ("v2", snapshot(2, 1, HBF, agent_v2())),
                       # HBF's one-shot sender never sends edr_agent.
                       ("hbf", snapshot(1, 1, HBF)), ("v2_without_agent", snapshot(2, 1, HBF)),
                       ("v3_without_agent", snapshot(3, 1, HBF)), ("revoked", snapshot(3, 1, agent_v3(60)))):
        report(ctx.runtime, devices[name], body, NOW)
    report(ctx.runtime, other, snapshot(3, 1, agent_v3(60)), NOW)
    # Every snapshot is a whole state: a later one without edr_agent removes it.
    report(ctx.runtime, devices["dropped"], snapshot(3, 1, agent_v3(60)), at(-3600))
    report(ctx.runtime, devices["dropped"], snapshot(1, 2, HBF), NOW)
    report(ctx.runtime, devices["fresh"], snapshot(3, 1, agent_v3(60)), at(1500))
    revoke(ctx, devices["revoked"], at(1))
    checked = 6  # v3_60, v3_600, v3_none, v2, fresh and the other tenant's device

    def silent():
        return {name for name, device in devices.items() if alert_rows(ctx.owner, device)}

    # Exactly the threshold is no silence; strictly more is.
    assert run(ctx, at(900)) == counts(devices_checked=checked)
    assert silent() == set()
    assert run(ctx, at(900) + timedelta(microseconds=1)) == counts(devices_checked=checked, alerts_opened=4)
    assert silent() == {"v3_60", "v3_none", "v2"} and len(alert_rows(ctx.owner, other, "agent_silent")) == 1
    # Three heartbeats of 600 s are 1800 s.
    assert run(ctx, at(1800)) == counts(devices_checked=checked, already_alerted=4)
    # A setting above three heartbeats wins.
    assert run(ctx, at(1800) + timedelta(microseconds=1), setting=3600) == counts(devices_checked=checked)
    assert run(ctx, at(1800) + timedelta(microseconds=1)) == counts(devices_checked=checked, alerts_opened=1,
                                                                    already_alerted=4)
    assert silent() == {"v3_60", "v3_none", "v2", "v3_600"}
    opened_at = {"v3_60": at(900) + timedelta(microseconds=1), "v3_600": at(1800) + timedelta(microseconds=1)}
    # The V2 payload has no interval and a V3 payload without one gives none: the setting alone.
    thresholds = {"v3_60": 900, "v3_600": 1800, "v3_none": 900, "v2": 900}
    for name, threshold in thresholds.items():
        [row] = alert_rows(ctx.owner, devices[name])
        assert (row.rule, row.severity, row.status, row.occurrences, row.first_event_seq, row.last_event_seq) == (
            "agent_silent", "medium", "open", 1, None, None)
        assert row.first_seen_at == row.last_seen_at == row.created_at == row.updated_at == opened_at.get(
            name, opened_at["v3_60"])
        assert row.evidence == {"last_received_at": FIRST_CONTACT, "threshold_seconds": threshold}
        assert row.dedup_key == sha(FIRST_CONTACT) and row.acknowledged_at is None and row.closed_at is None


def test_one_alert_per_silence_episode_whatever_the_operator_did_until_a_new_contact(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    first_snapshot = snapshot(3, 1, agent_v3(60))
    report(ctx.runtime, device, first_snapshot, NOW)
    only = partial(counts, tenants=1, devices_checked=1)
    assert run(ctx, at(901)) == only(alerts_opened=1)
    [opened] = alert_rows(ctx.owner, device)
    transition(ctx, "acknowledge_alert", opened.id, at(950))
    [acknowledged] = alert_rows(ctx.owner, device)
    assert run(ctx, at(2000)) == only(already_alerted=1)
    # No new alert, no occurrence and no last_seen_at change.
    [same] = alert_rows(ctx.owner, device)
    assert (same.status, same.occurrences, same.last_seen_at, same.updated_at, same.evidence) == (
        "acknowledged", 1, at(901), acknowledged.updated_at, opened.evidence)
    transition(ctx, "close_alert", opened.id, at(2100))
    assert run(ctx, at(3000)) == only(already_alerted=1)
    [closed] = alert_rows(ctx.owner, device)
    assert (closed.id, closed.status, closed.occurrences, closed.last_seen_at) == (opened.id, "closed", 1, at(901))
    # Neither an exact snapshot retry nor an event batch is a new contact.
    assert report(ctx.runtime, device, first_snapshot, at(3100))["received_at"] == iso(NOW)
    send(ctx.runtime, device, v2(1, sensor(1)), now=at(3200))
    with ctx.owner.session() as session:
        assert session.get(Device, UUID(device["device_id"])).last_received_at == NOW
    assert run(ctx, at(3300)) == only(already_alerted=1) and len(alert_rows(ctx.owner, device)) == 1
    # A new snapshot is a new contact: its silence is the next episode, with its own key text.
    report(ctx.runtime, device, snapshot(3, 2, agent_v3(60)), at(4000))
    assert run(ctx, at(4900)) == only()
    assert run(ctx, at(4901)) == only(alerts_opened=1)
    # A third episode opens even while the second one's alert is still open.
    report(ctx.runtime, device, snapshot(3, 3, agent_v3(60)), at(6000))
    assert run(ctx, at(6901)) == only(alerts_opened=1)
    episodes = [(row.status, row.dedup_key, row.evidence["last_received_at"], row.first_seen_at)
                for row in alert_rows(ctx.owner, device)]
    assert episodes == [("closed", sha(FIRST_CONTACT), FIRST_CONTACT, at(901)),
                        ("open", sha(canonical_utc(at(4000))), canonical_utc(at(4000)), at(4901)),
                        ("open", sha(canonical_utc(at(6000))), canonical_utc(at(6000)), at(6901))]


def silence_match(key):
    return alerts.Match("agent_silent", key, None, None, 1, {"last_received_at": key, "threshold_seconds": SILENCE},
                        "medium")


def test_null_sequence_rows_go_through_the_upsert_and_the_open_alert_cap(event_tenants):
    ctx = event_tenants
    limits = replace(DEFAULT_LIMITS, max_open_alerts_per_device=10)
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    first, second = FIRST_CONTACT, canonical_utc(at(60))

    def upsert(key, seconds):
        with ctx.runtime.session() as session:
            locked = session.scalar(select(Device).where(Device.id == UUID(device["device_id"])).with_for_update())
            return alerts.open_matches(session, locked, [silence_match(key)], received_at=at(seconds), limits=limits)

    assert upsert(first, 1) == ["opened"]
    # The upsert updates a key that is not closed (the sweep never asks it to: it checks the episode first), and
    # greatest() of two null sequences stays null.
    assert upsert(first, 2) == ["updated"]
    [row] = alert_rows(ctx.owner, device)
    assert (row.occurrences, row.first_event_seq, row.last_event_seq, row.first_seen_at, row.last_seen_at) == (
        2, None, None, at(1), at(2))
    # Nine event alerts: with the silence alert the device is at its cap of 10.
    send(ctx.runtime, device, v1(1, *[v1_started(seq, downloads(f"tool{seq}.exe")) for seq in range(1, 10)]),
         limits=limits, now=at(3))
    assert len(alert_rows(ctx.owner, device)) == 10
    assert upsert(second, 4) == ["suppressed"]
    assert upsert(first, 5) == ["updated"]
    # The silence alert counts towards the cap of the event rules' openings too.
    send(ctx.runtime, device, v1(2, v1_started(10, downloads("new.exe"))), limits=limits, now=at(6))
    assert stored(ctx.owner, device)[1].suppressed_alerts == 1 and len(alert_rows(ctx.owner, device)) == 10
    # A close frees the slot: the key opens a new alert, again with null sequences.
    transition(ctx, "close_alert", row.id, at(7))
    assert upsert(first, 8) == ["opened"]
    assert [(item.status, item.occurrences, item.first_event_seq, item.last_event_seq, item.first_seen_at)
            for item in alert_rows(ctx.owner, device, "agent_silent")] == [("closed", 3, None, None, at(1)),
                                                                           ("open", 1, None, None, at(8))]


def test_the_sweep_opens_under_the_ingestion_cap_and_counts_what_it_suppressed(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    limits = replace(DEFAULT_LIMITS, max_open_alerts_per_device=10)
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    report(ctx.runtime, device, snapshot(3, 1, agent_v3(60)), NOW)
    send(ctx.runtime, device, v1(1, *[v1_started(seq, downloads(f"tool{seq}.exe")) for seq in range(1, 11)]),
         limits=limits, now=at(1))
    only = partial(counts, tenants=1, devices_checked=1)
    assert run(ctx, at(901), limits=limits) == only(suppressed=1)
    assert alert_rows(ctx.owner, device, "agent_silent") == []
    # The event cursor's suppressed_alerts stays ingestion's own count.
    assert stored(ctx.owner, device)[1].suppressed_alerts == 0
    # The next run tries again: after a close it opens.
    assert run(ctx, at(902), limits=limits) == only(suppressed=1)
    transition(ctx, "close_alert", alert_rows(ctx.owner, device)[0].id, at(903))
    assert run(ctx, at(904), limits=limits) == only(alerts_opened=1)
    [row] = alert_rows(ctx.owner, device, "agent_silent")
    assert (row.first_seen_at, row.first_event_seq, row.last_event_seq) == (at(904), None, None)


def test_the_sweep_skips_a_device_row_another_transaction_holds(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    busy, idle = enrolled(ctx.runtime, ctx.admin_a, ctx.a), enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    for device in (busy, idle):
        report(ctx.runtime, device, snapshot(3, 1, agent_v3(60)), NOW)
    with ctx.runtime.session() as holder:
        # The row lock that ingestion holds while the device reports.
        holder.execute(select(Device.id).where(Device.id == UUID(busy["device_id"])).with_for_update())
        begun = time.monotonic()
        result = run(ctx, at(901))
        elapsed = time.monotonic() - begun
    assert result == counts(tenants=1, devices_checked=2, alerts_opened=1, devices_busy=1)
    # SKIP LOCKED: the sweep did not wait for the holder (the lock timeout is 3 s).
    assert elapsed < 2.5, elapsed
    assert (len(alert_rows(ctx.owner, busy)), len(alert_rows(ctx.owner, idle))) == (0, 1)
    assert run(ctx, at(902)) == counts(tenants=1, devices_checked=2, alerts_opened=1, already_alerted=1)
    assert len(alert_rows(ctx.owner, busy, "agent_silent")) == 1


def test_each_locked_candidate_is_checked_again_before_its_alert_opens(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    reporting, revoked, dropped, silent = devices = [enrolled(ctx.runtime, ctx.admin_a, ctx.a) for _ in range(4)]
    for device in devices:
        report(ctx.runtime, device, snapshot(3, 1, agent_v3(60)), NOW)
    original, reads = sweep._candidates, []

    def candidates_then_changes(session, tenant_id, after, limit):
        rows = original(session, tenant_id, after, limit)
        reads.append(len(rows))
        if len(reads) == 1:
            # Committed after the candidates were read, before their rows are locked.
            report(ctx.runtime, reporting, snapshot(3, 2, agent_v3(60)), at(900))
            report(ctx.runtime, dropped, snapshot(1, 2, HBF), at(900))
            revoke(ctx, revoked, at(900))
        return rows

    monkeypatch.setattr(sweep, "_candidates", candidates_then_changes)
    assert run(ctx, at(901)) == counts(tenants=1, devices_checked=4, alerts_opened=1)
    assert reads == [4]
    assert [len(alert_rows(ctx.owner, device)) for device in devices] == [0, 0, 0, 1]


def failing_chunks(tenant, *, after):
    """A _sweep_chunk that fails for one tenant once `after` of its chunks have been committed."""
    original, calls = sweep._sweep_chunk, []

    def chunk(session, tenant_id, *args):
        if tenant_id == tenant:
            calls.append(tenant_id)
            if len(calls) > after:
                raise OperationalError("SELECT devices", {}, Exception("canceling statement due to lock timeout"))
        return original(session, tenant_id, *args)

    return chunk


def test_a_failing_tenant_is_counted_and_skipped_and_its_committed_chunks_stay(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a, ctx.b)
    first, second = by_id([enrolled(ctx.runtime, ctx.admin_a, ctx.a) for _ in range(2)])
    other = enrolled(ctx.runtime, ctx.admin_b, ctx.b)
    for device in (first, second, other):
        report(ctx.runtime, device, snapshot(3, 1, agent_v3(60)), NOW)
    original = sweep._sweep_chunk
    monkeypatch.setattr(sweep, "_sweep_chunk", failing_chunks(ctx.a, after=1))
    # One-device chunks: tenant A commits one chunk, then its second fails; tenant B is swept anyway.
    assert run(ctx, at(901), chunk_size=1) == counts(failed_tenants=1, devices_checked=2, alerts_opened=2)
    assert [len(alert_rows(ctx.owner, device)) for device in (first, second, other)] == [1, 0, 1]
    monkeypatch.setattr(sweep, "_sweep_chunk", original)
    assert run(ctx, at(902), chunk_size=1) == counts(devices_checked=3, alerts_opened=1, already_alerted=2)
    assert [len(alert_rows(ctx.owner, device)) for device in (first, second, other)] == [1, 1, 1]


def test_candidates_are_read_in_chunks_by_device_id_without_a_skip_or_a_repeat(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    devices = by_id([enrolled(ctx.runtime, ctx.admin_a, ctx.a) for _ in range(5)])
    for device in devices:
        report(ctx.runtime, device, snapshot(3, 1, agent_v3(60)), NOW)
    original, reads = sweep._candidates, []

    def recording(session, tenant_id, after, limit):
        rows = original(session, tenant_id, after, limit)
        reads.append((after, limit, [row[0] for row in rows]))
        return rows

    monkeypatch.setattr(sweep, "_candidates", recording)
    assert run(ctx, at(901), chunk_size=2) == counts(tenants=1, devices_checked=5, alerts_opened=5)
    ids = [UUID(device["device_id"]) for device in devices]
    assert reads == [(None, 2, ids[:2]), (ids[1], 2, ids[2:4]), (ids[3], 2, ids[4:])]
    assert [len(alert_rows(ctx.owner, device, "agent_silent")) for device in devices] == [1] * 5


# --- the CLI ------------------------------------------------------------------------------------------------

OPERATOR_SETTINGS = ("SP_OPERATOR_ISSUER", "SP_OPERATOR_AUDIENCE", "SP_JWKS_FILE", "SP_ALLOWED_HOSTS",
                     "SP_ALLOW_LOOPBACK_HTTP")


def silent_for_hours(ctx, hours=2):
    """A V3 device whose last snapshot arrived `hours` ago on the real clock: the CLI sweeps at the real time."""
    real_now = datetime.now(timezone.utc)
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a, now=real_now - timedelta(hours=hours, minutes=5))
    report(ctx.runtime, device, snapshot(3, 1, agent_v3(60)), real_now - timedelta(hours=hours))
    return device


def sweep_environment(monkeypatch):
    for name in OPERATOR_SETTINGS + ("SP_SILENCE_ALERT_SECONDS", "SP_MAX_OPEN_ALERTS_PER_DEVICE"):
        monkeypatch.delenv(name, raising=False)


def test_sweep_cli_runs_only_with_the_runtime_credential_and_prints_one_json_line(event_tenants, monkeypatch, capsys):
    ctx = event_tenants
    swept(monkeypatch, ctx.a, ctx.b)
    device = silent_for_hours(ctx)
    sweep_environment(monkeypatch)
    monkeypatch.delenv("SP_DATABASE_URL", raising=False)
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["sweep"]) == 1
    assert capsys.readouterr().err.strip() == "SP_DATABASE_URL is required for the silence sweep"
    # The owner credential is refused before anything is read or written.
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["sweep"]) == 1
    output = capsys.readouterr()
    assert (output.out, output.err.strip()) == ("", "sweep requires the separate unprivileged runtime database role")
    assert alert_rows(ctx.owner, device) == []
    # With the runtime credential and none of the HTTP server's operator settings. Two hours are no silence under
    # the largest setting...
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.runtime))
    monkeypatch.setenv("SP_SILENCE_ALERT_SECONDS", "86400")
    assert cli.main(["sweep"]) == 0
    output = capsys.readouterr()
    assert (json.loads(output.out), output.err) == (counts(devices_checked=1), "")
    assert alert_rows(ctx.owner, device) == []
    # ...and silence under the default, 900 s.
    monkeypatch.delenv("SP_SILENCE_ALERT_SECONDS")
    assert cli.main(["sweep"]) == 0
    output = capsys.readouterr()
    assert output.out.count("\n") == 1 and output.out.endswith("\n") and output.err == ""
    summary = json.loads(output.out)
    assert list(summary) == list(sweep.RESULT_KEYS) and all(type(value) is int for value in summary.values())
    assert summary == counts(devices_checked=1, alerts_opened=1)
    assert "postgresql" not in output.out + output.err
    [row] = alert_rows(ctx.owner, device, "agent_silent")
    assert row.evidence["threshold_seconds"] == 900 and row.first_event_seq is None


def test_sweep_cli_exits_1_when_a_tenant_failed_after_committed_chunks(event_tenants, monkeypatch, capsys):
    ctx = event_tenants
    swept(monkeypatch, ctx.a, ctx.b)
    first, second = by_id([silent_for_hours(ctx) for _ in range(2)])
    monkeypatch.setattr(sweep, "sweep_silent_agents", partial(sweep.sweep_silent_agents, chunk_size=1))
    monkeypatch.setattr(sweep, "_sweep_chunk", failing_chunks(ctx.a, after=1))
    sweep_environment(monkeypatch)
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.runtime))
    assert cli.main(["sweep"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == counts(failed_tenants=1, devices_checked=1, alerts_opened=1)
    assert output.err.startswith("sweep incomplete: 1 tenant(s) failed")
    assert "no success was recorded" not in output.err and "postgresql" not in output.out + output.err
    # The committed chunk's alert stays open; the next run retries the rest.
    assert [len(alert_rows(ctx.owner, device)) for device in (first, second)] == [1, 0]


# --- the alert routes ---------------------------------------------------------------------------------------

EVIDENCE_KEYS = {"scan_detection": set(EVENT_FIELDS["scan_detected"]), "behavior_match": set(EVENT_FIELDS["behavior_match"]),
                 "persistence_added": set(EVENT_FIELDS["persistence_change"]),
                 "capability_down": {"subject", "state", "code", "rule_set_id"}, "tamper_signal": {"signal", "detail"},
                 "agent_silent": {"last_received_at", "threshold_seconds"}}


def test_stage3_alerts_through_the_alert_routes(pg_service_databases, api_context, monkeypatch):
    ctx = api_context; client = ctx["client"]
    monkeypatch.setattr(sweep, "_tenants", lambda session: [ctx["a"]])
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    response = client.put("/api/v1/device/snapshot", json=snapshot(3, 1, agent_v3(60)), headers=headers)
    assert response.status_code == 200, response.text
    accepted = client.post("/api/v1/device/events", json=v2(1, scan(1), behavior(2), persistence(3),
                                                            agent(4, "rule_set", "invalid"), tamper(5)), headers=headers)
    assert accepted.status_code == 200, accepted.text
    # A behavior event that carries a severity is refused before anything is written.
    refused = client.post("/api/v1/device/events", json=v2(2, behavior(6, severity="high")), headers=headers)
    assert (refused.status_code, refused.json()) == (422, {"detail": "invalid_request"})
    later = datetime.now(timezone.utc) + timedelta(hours=1)
    assert sweep.sweep_silent_agents(ctx["app"].state.database, silence_alert_seconds=SILENCE, now=later) == counts(
        tenants=1, devices_checked=1, alerts_opened=1)
    listed = client.get(f"/api/v1/tenants/{ctx['a']}/alerts", headers=auth(ctx["token"]("viewer")))
    assert listed.status_code == 200, listed.text
    items = {item["rule"]: item for item in listed.json()["items"]}
    assert set(items) == set(EVIDENCE_KEYS)
    for rule, item in items.items():
        assert set(item) == ALERT_KEYS and set(item["evidence"]) == EVIDENCE_KEYS[rule], rule
        assert (item["severity"], item["status"], item["occurrences"]) == (
            EVENT_RULE_SEVERITY.get(rule, "medium"), "open", 1)
        assert (item["source"], item["producer_verification"]) == ("self_reported", "not_verified")
    for rule, seq in (("scan_detection", 1), ("behavior_match", 2), ("persistence_added", 3), ("capability_down", 4),
                      ("tamper_signal", 5)):
        assert (items[rule]["first_event_seq"], items[rule]["last_event_seq"]) == (seq, seq)
    silent = items["agent_silent"]
    assert (silent["first_event_seq"], silent["last_event_seq"]) == (None, None)
    assert silent["first_seen_at"] == silent["last_seen_at"] == iso(later)
    detail = client.get(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}", headers=auth(ctx["token"]()))
    contact = datetime.fromisoformat(detail.json()["last_received_at"].replace("Z", "+00:00"))
    assert silent["evidence"] == {"last_received_at": canonical_utc(contact), "threshold_seconds": SILENCE}
    # Operators acknowledge and close it like any alert; the next sweep then changes nothing.
    for action, status in (("acknowledge", "acknowledged"), ("close", "closed")):
        changed = client.post(f"/api/v1/tenants/{ctx['a']}/alerts/{silent['id']}/{action}", json={},
                              headers=auth(ctx["token"]()))
        assert changed.status_code == 200, changed.text
        assert (changed.json()["status"], changed.json()["first_event_seq"], changed.json()["last_event_seq"]) == (
            status, None, None)
    assert sweep.sweep_silent_agents(ctx["app"].state.database, silence_alert_seconds=SILENCE,
                                     now=later + timedelta(minutes=5)) == counts(tenants=1, devices_checked=1,
                                                                                 already_alerted=1)
    closed = client.get(f"/api/v1/tenants/{ctx['a']}/alerts?status=closed", headers=auth(ctx["token"]()))
    assert [(item["id"], item["occurrences"]) for item in closed.json()["items"]] == [(silent["id"], 1)]
