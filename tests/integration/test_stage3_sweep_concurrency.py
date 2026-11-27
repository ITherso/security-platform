"""Real PostgreSQL: `security-platform sweep` next to other transactions.

Which device rows a sweep run locks (only those of silent devices whose episode has no alert yet), two sweeps
racing on the same silence episodes through two real database sessions, and an upsert that would change an
alerted episode. A single sweep run's rules are in test_stage3_alerts.py, whose helpers these tests reuse.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from functools import partial
import re
import threading
import time
from uuid import UUID

import pytest
from sqlalchemy import event as sqlalchemy_event, select, text
from sqlalchemy.exc import OperationalError

from security_platform.models import Device
from security_platform.services import alerts, enrollment, snapshots, sweep
from security_platform.services.common import canonical_utc
from test_events import event_tenants  # noqa: F401  (shared fixtures)
from test_services import NOW, enrolled, pg_service_databases  # noqa: F401  (shared real-database fixture)
from test_stage3_alerts import agent_v3, alert_rows, at, counts, report, run, sha, snapshot, swept, transition


pytestmark = pytest.mark.integration
LOCK = "FOR UPDATE SKIP LOCKED"  # the sweep's device row lock, the only statement of the sweep that locks rows
LOCK_NOT_AVAILABLE = "55P03"  # SQLSTATE of a lock_timeout


def held(database, device):
    """True while another transaction holds the device's row: FOR UPDATE SKIP LOCKED does not get it."""
    with database.session() as session:
        return session.scalar(select(Device.id).where(Device.id == UUID(device["device_id"]))
                              .with_for_update(skip_locked=True)) is None


def report_or_lock_timeout(runtime, device, body, now):
    """A snapshot report that waits at most 200 ms for its device row lock: its sequence, or "lock timeout"."""
    try:
        with runtime.session() as session:
            session.execute(text("SET LOCAL lock_timeout = '200ms'"))
            principal = enrollment.authenticate_device(session, device["credential_secret"], now=now)
            return snapshots.ingest_snapshot(session, principal, body, now=now)["sequence"]
    except OperationalError as exc:
        if getattr(exc.orig, "sqlstate", None) != LOCK_NOT_AVAILABLE:
            raise
        return "lock timeout"


def opening(monkeypatch, action):
    """Run `action` once, inside the sweep's chunk transaction, right after its first agent_silent upsert."""
    original, outcomes = sweep.open_matches, []

    def open_matches(*args, **kwargs):
        outcomes.append(original(*args, **kwargs))
        if len(outcomes) == 1:
            action()
        return outcomes[-1]

    monkeypatch.setattr(sweep, "open_matches", open_matches)
    return outcomes


@contextmanager
def before_the_lock(database, action):
    """Run `action` once, just before the first row-locking sweep statement is sent, while its chunk is open."""
    state = {"ran": False}

    def hook(connection, cursor, statement, parameters, context, executemany):
        if LOCK in statement and not state["ran"]:
            state["ran"] = True
            action()

    sqlalchemy_event.listen(database.engine, "before_cursor_execute", hook)
    try:
        yield state
    finally:
        sqlalchemy_event.remove(database.engine, "before_cursor_execute", hook)


@contextmanager
def sent(database):
    """Every (statement, parameters) the database's engine sends meanwhile."""
    seen = []

    def record(connection, cursor, statement, parameters, context, executemany):
        seen.append((statement, parameters))

    sqlalchemy_event.listen(database.engine, "before_cursor_execute", record)
    try:
        yield seen
    finally:
        sqlalchemy_event.remove(database.engine, "before_cursor_execute", record)


def index_conditions(plan):
    """(index name, index condition) of every index scan of an EXPLAIN (FORMAT JSON) plan tree."""
    found = [(plan["Index Name"], plan.get("Index Cond"))] if "Index Name" in plan else []
    for child in plan.get("Plans", []):
        found += index_conditions(child)
    return found


def one_tenant(checked):
    return partial(counts, tenants=1, devices_checked=checked)


def agent_device(ctx, last_contact):
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    report(ctx.runtime, device, snapshot(3, 1, agent_v3(60)), last_contact)
    return device


# --- the rows a run locks -----------------------------------------------------------------------------------

def test_a_run_locks_only_the_silent_devices_whose_episode_has_no_alert_yet(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    alerted, fresh = agent_device(ctx, NOW), agent_device(ctx, at(600))
    only = one_tenant(2)
    # The first run opens the alerted device's episode; the fresh device is silent for 301 s only.
    assert run(ctx, at(901)) == only(alerts_opened=1)
    seen = {}

    def look_from_outside():
        seen["held"] = {"alerted": held(ctx.runtime, alerted), "fresh": held(ctx.runtime, fresh)}
        # The alerted device comes back while the chunk is still open.
        seen["report"] = report_or_lock_timeout(ctx.runtime, alerted, snapshot(3, 2, agent_v3(60)), at(1501))

    outcomes = opening(monkeypatch, look_from_outside)
    assert run(ctx, at(1501)) == only(alerts_opened=1, already_alerted=1)
    assert outcomes == [["opened"]]
    # The fresh device's row stays locked until its alert commits; the alerted device's row was never locked, so
    # its snapshot was accepted at once.
    assert seen == {"held": {"alerted": False, "fresh": True}, "report": 2}
    assert [(row.dedup_key, row.occurrences, row.last_seen_at) for row in alert_rows(ctx.owner, alerted)] == [
        (sha(canonical_utc(NOW)), 1, at(901))]
    assert [(row.dedup_key, row.first_seen_at) for row in alert_rows(ctx.owner, fresh)] == [
        (sha(canonical_utc(at(600))), at(1501))]


def test_an_alerted_episode_is_counted_without_waiting_for_a_row_another_transaction_holds(event_tenants,
                                                                                         monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    device = agent_device(ctx, NOW)
    only = one_tenant(1)
    assert run(ctx, at(901)) == only(alerts_opened=1)
    with ctx.runtime.session() as holder:
        # The row lock that ingestion holds while the device reports.
        holder.execute(select(Device.id).where(Device.id == UUID(device["device_id"])).with_for_update())
        begun = time.monotonic()
        result = run(ctx, at(1800))
        elapsed = time.monotonic() - begun
    # Its episode has an alert, so the run needs no lock to know that it changes nothing: not devices_busy.
    assert result == only(already_alerted=1)
    assert elapsed < 2.5, elapsed
    [row] = alert_rows(ctx.owner, device)
    assert (row.occurrences, row.last_seen_at, row.updated_at) == (1, at(901), at(901))


def test_the_unlocked_episode_read_probes_the_silence_episode_index_once_per_chunk(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    alerted, closed, fresh = agent_device(ctx, NOW), agent_device(ctx, NOW), agent_device(ctx, at(600))
    ids = [UUID(device["device_id"]) for device in (alerted, closed, fresh)]
    assert run(ctx, at(901)) == one_tenant(3)(alerts_opened=2)
    transition(ctx, "close_alert", alert_rows(ctx.owner, closed)[0].id, at(902))
    with sent(ctx.runtime) as seen:
        assert run(ctx, at(1501)) == one_tenant(3)(alerts_opened=1, already_alerted=2)
    # The chunk's one episode read comes before its one lock statement, which names the fresh device alone.
    reads = [index for index, (statement, _) in enumerate(seen) if "CROSS JOIN LATERAL" in statement]
    locks = [index for index, (statement, _) in enumerate(seen) if LOCK in statement]
    assert len(reads) == len(locks) == 1 and reads[0] < locks[0], seen
    assert [device_id in seen[locks[0]][1].values() for device_id in ids] == [False, False, True]
    now_key, later_key = sha(canonical_utc(NOW)), sha(canonical_utc(at(600)))
    names = ["device_ids", "dedup_keys", "tenant_id"]
    source = sweep._ALERTED_EPISODES.text
    assert sorted(set(re.findall(r":(\w+)", source))) == sorted(names)
    generic = re.sub(r":(\w+)", lambda found: f"${names.index(found.group(1)) + 1}", source)

    def parameters(*pairs):
        return {"device_ids": [device_id for device_id, _ in pairs], "dedup_keys": [key for _, key in pairs],
                "tenant_id": ctx.a}

    with ctx.owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            # Each device matches its own key only; a closed alert counts.
            found = connection.scalars(sweep._ALERTED_EPISODES, parameters(
                (ids[0], now_key), (ids[1], now_key), (ids[2], later_key))).all()
            missed = connection.scalars(sweep._ALERTED_EPISODES, parameters(
                (ids[2], now_key), (ids[0], later_key))).all()
            connection.execute(text("ANALYZE alerts"))
            # A plan that cannot use the index still shows a (penalised) sequential scan.
            connection.execute(text("SET LOCAL enable_seqscan = off"))
            custom = connection.execute(text("EXPLAIN (FORMAT JSON) " + source),
                                        parameters((ids[0], now_key), (ids[2], later_key))).scalar()
            # Sent unprepared: a prepared EXPLAIN would itself demand the $n parameters.
            with connection.connection.dbapi_connection.cursor() as cursor:
                cursor.execute("EXPLAIN (GENERIC_PLAN, FORMAT JSON) " + generic, prepare=False)
                generic_plan = cursor.fetchone()[0]
        finally:
            transaction.rollback()
    assert (sorted(found), missed) == (sorted(ids), [])
    # One probe per pair on all three index columns: the character(64) keys need no conversion of the column.
    for plan in (custom, generic_plan):
        [(index, condition)] = index_conditions(plan[0]["Plan"])
        assert index == "ix_alert_silence_episode", plan
        assert "(device_id = wanted.device_id) AND (dedup_key = wanted.dedup_key)" in condition, plan


# --- two sweeps on the same episode -------------------------------------------------------------------------

def test_a_sweep_whose_lock_follows_a_concurrent_sweeps_commit_finds_the_episode_alerted(event_tenants,
                                                                                       monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    device = agent_device(ctx, NOW)
    only = one_tenant(1)
    results = {}

    def other_sweep():
        # A second session: its whole run commits the episode's alert after this run read the episode as not
        # alerted, and before this run locks the row.
        results["other"] = run(ctx, at(902))

    with before_the_lock(ctx.runtime, other_sweep) as state:
        results["this"] = run(ctx, at(901))
    assert state["ran"]
    # Checked again under the lock, the episode has its alert: this run changed nothing.
    assert results == {"other": only(alerts_opened=1), "this": only(already_alerted=1)}
    [row] = alert_rows(ctx.owner, device)
    assert (row.occurrences, row.first_seen_at, row.last_seen_at, row.updated_at) == (1, at(902), at(902), at(902))


def test_a_sweep_skips_the_row_of_a_concurrent_sweep_that_has_not_yet_committed_the_episode(event_tenants,
                                                                                          monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    device = agent_device(ctx, NOW)
    only = one_tenant(1)
    results = {}

    def other_sweep():
        # A second session, while this run holds the row and its alert is inserted but not committed.
        begun = time.monotonic()
        results["other"] = run(ctx, at(902))
        results["elapsed"] = time.monotonic() - begun

    outcomes = opening(monkeypatch, other_sweep)
    results["this"] = run(ctx, at(901))
    assert outcomes == [["opened"]]
    assert (results["this"], results["other"]) == (only(alerts_opened=1), only(devices_busy=1))
    # SKIP LOCKED: the other run did not wait for this one (the lock timeout is 3 s).
    assert results["elapsed"] < 2.5, results
    [row] = alert_rows(ctx.owner, device)
    assert (row.occurrences, row.first_seen_at, row.last_seen_at) == (1, at(901), at(901))


def test_two_sweeps_racing_on_the_same_episodes_open_each_alert_once(event_tenants, monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    devices = [enrolled(ctx.runtime, ctx.admin_a, ctx.a) for _ in range(12)]
    state = {}

    def together(connection, cursor, statement, parameters, context, executemany):
        if LOCK in statement:
            # Both runs have read every episode of this contact as not alerted; they lock at the same time.
            state["barrier"].wait(timeout=10)

    sqlalchemy_event.listen(ctx.runtime.engine, "before_cursor_execute", together)
    try:
        for sequence, contact in enumerate((NOW, at(2000), at(4000)), start=1):
            for device in devices:
                report(ctx.runtime, device, snapshot(3, sequence, agent_v3(60)), contact)
            now, state["barrier"] = contact + timedelta(seconds=901), threading.Barrier(2)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run, ctx, now) for _ in range(2)]
                results = [future.result(timeout=30) for future in futures]
            # Each run counts every device once: it opened the alert, found it under the lock, or skipped the row
            # the other run held. Together they opened each episode's alert exactly once.
            for result in results:
                assert {key: result[key] for key in ("tenants", "failed_tenants", "devices_checked", "suppressed")} == {
                    "tenants": 1, "failed_tenants": 0, "devices_checked": 12, "suppressed": 0}, results
                assert result["alerts_opened"] + result["already_alerted"] + result["devices_busy"] == 12, results
            assert sum(result["alerts_opened"] for result in results) == 12, results
            key = sha(canonical_utc(contact))
            for device in devices:
                [row] = [row for row in alert_rows(ctx.owner, device, "agent_silent") if row.dedup_key == key]
                assert (row.status, row.occurrences, row.first_seen_at, row.last_seen_at) == ("open", 1, now, now)
    finally:
        sqlalchemy_event.remove(ctx.runtime.engine, "before_cursor_execute", together)
    assert [len(alert_rows(ctx.owner, device)) for device in devices] == [3] * 12


# --- an upsert that would change an alerted episode ---------------------------------------------------------

def test_an_upsert_that_updates_an_alerted_episode_rolls_its_chunk_back_and_fails_the_tenant(event_tenants,
                                                                                           monkeypatch):
    ctx = event_tenants
    swept(monkeypatch, ctx.a)
    device = agent_device(ctx, NOW)
    other = agent_device(ctx, at(600))
    assert run(ctx, at(901)) == one_tenant(2)(alerts_opened=1)
    [opened] = alert_rows(ctx.owner, device)
    # The sweep's episode checks now look for another key and miss the open alert; the upsert, which keys the
    # episode itself, still finds it. No opener of the device's alerts can produce this while it holds the
    # device row lock: this stands in for a broken check.
    monkeypatch.setattr(sweep, "dedup_key", lambda key: alerts.dedup_key("missed " + key))
    outcomes = opening(monkeypatch, lambda: None)
    assert run(ctx, at(1800)) == counts(tenants=1, failed_tenants=1)
    assert ["updated"] in outcomes
    # Never counted as already_alerted: the chunk rolled back, so the alert kept its occurrence count and times,
    # and the other device's opening of the same chunk waits for the next run.
    [same] = alert_rows(ctx.owner, device)
    assert (same.id, same.occurrences, same.last_seen_at, same.updated_at, same.evidence) == (
        opened.id, 1, at(901), at(901), opened.evidence)
    assert alert_rows(ctx.owner, other) == []
    monkeypatch.setattr(sweep, "dedup_key", alerts.dedup_key)
    assert run(ctx, at(1801)) == one_tenant(2)(alerts_opened=1, already_alerted=1)
    [same] = alert_rows(ctx.owner, device)
    assert (same.occurrences, same.last_seen_at) == (1, at(901))
