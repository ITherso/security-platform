"""Real PostgreSQL alert retention: `set-alert-retention`, `alerts prune` and migration 0006.

Closed alerts are deleted once their closed_at is older than the tenant's
alert_retention_days (30..3650, default 60). Open and acknowledged alerts are
never deleted, and a closed agent_silent alert of a device's current silence
episode stays, so that the sweep never opens that episode again.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from functools import partial
import io
import json
from uuid import UUID, uuid4

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import CheckConstraint, func, insert, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.schema import CreateIndex

from security_platform import cli
from security_platform.models import Alert, AuditEvent, Device, Principal, Tenant
from security_platform.services import administration, alerts, audit, sweep
from security_platform.services.common import DEFAULT_LIMITS, NotFound, ServiceError, ServiceLimits
from test_events import PROJECT, database_url, event_tenants, generic_plan_database, migration_module  # noqa: F401
from test_services import NOW, enrolled, pg_service_databases  # noqa: F401  (shared real-database fixture)
from test_stage3_alerts import agent_v3, report, revoke, snapshot, transition
from test_stage3_contracts import settings_per_statement, timeouts


pytestmark = pytest.mark.integration
DAY = timedelta(days=1)
MICROSECOND = timedelta(microseconds=1)
SILENCE = 900
RESULT_KEYS = ["tenants", "deleted_alerts", "episode_alerts_kept", "failed_tenants"]
RETENTION = "0006_alert_retention"


def at(seconds):
    return NOW + timedelta(seconds=seconds)


def principal_id(owner, operator):
    with owner.session() as session:
        return session.scalar(select(Principal.id).where(Principal.issuer == operator.issuer,
                                                         Principal.subject == operator.subject))


def add_alert(owner, tenant, device, closer, *, status="closed", closed_at=None, seen_at=None, rule="event_loss"):
    """One alert written directly by the owner; a closed one needs `closed_at`. Returns its id."""
    seen_at = seen_at or (closed_at - DAY if closed_at else NOW - 400 * DAY)
    row = {"id": uuid4(), "tenant_id": tenant, "device_id": UUID(device["device_id"]), "rule": rule,
           "severity": "medium", "dedup_key": alerts.dedup_key(str(uuid4())), "status": status, "occurrences": 1,
           "first_event_seq": 1, "last_event_seq": 1, "first_seen_at": seen_at, "last_seen_at": seen_at,
           "evidence": {"missing_events": 1}, "created_at": seen_at, "updated_at": seen_at}
    if status == "acknowledged":
        row.update(acknowledged_at=seen_at, acknowledged_by=closer)
    if status == "closed":
        row.update(closed_at=closed_at, closed_by=closer)
    with owner.session() as session:
        session.add(Alert(**row))
    return row["id"]


def alert_ids(owner, device):
    with owner.session() as session:
        return set(session.scalars(select(Alert.id).where(Alert.device_id == UUID(device["device_id"]))))


def silent_alerts(owner, device):
    with owner.session() as session:
        return session.scalars(select(Alert).where(Alert.device_id == UUID(device["device_id"]),
                                                   Alert.rule == "agent_silent").order_by(Alert.created_at)).all()


def pruned(monkeypatch, *tenants):
    """Restrict this test's prunes to its own tenants, still read with their retention from the database."""
    original = alerts._prune_tenants
    monkeypatch.setattr(alerts, "_prune_tenants", lambda session: [row for row in original(session)
                                                                    if row[0] in tenants])


def swept(monkeypatch, *tenants):
    monkeypatch.setattr(sweep, "_tenants", lambda session: sorted(tenants))


def prune(ctx, now, **options):
    return alerts.prune_closed_alerts(ctx.runtime, now=now, **options)


def run_sweep(ctx, now):
    return sweep.sweep_silent_agents(ctx.runtime, silence_alert_seconds=SILENCE, now=now)


def result(tenants=1, deleted=0, kept=0, failed=0):
    return {"tenants": tenants, "deleted_alerts": deleted, "episode_alerts_kept": kept, "failed_tenants": failed}


def prune_records(owner, tenant):
    with owner.session() as session:
        return session.execute(select(AuditEvent.actor_type, AuditEvent.actor_id, AuditEvent.object_type,
                                      AuditEvent.object_id, AuditEvent.details, AuditEvent.created_at)
                               .where(AuditEvent.tenant_id == tenant, AuditEvent.action == "alerts_pruned")
                               .order_by(AuditEvent.created_at, AuditEvent.id)).all()


def audit_count(owner, tenant):
    with owner.session() as session:
        return session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == tenant))


def details(deleted=0, kept=0, complete=True):
    return {"deleted_alerts": deleted, "episode_alerts_kept": kept, "complete": complete}


# --- set-alert-retention -------------------------------------------------------------------------------------

def test_alert_retention_setting_is_bounded_audited_and_backed_by_the_database(event_tenants):
    ctx = event_tenants
    before = audit_count(ctx.owner, ctx.a)
    with ctx.owner.session() as session:
        assert session.get(Tenant, ctx.a).alert_retention_days == 60
        assert administration.set_alert_retention(session, ctx.a, 30, now=NOW) == {
            "tenant_id": str(ctx.a), "alert_retention_days": 30}
        assert administration.set_alert_retention(session, ctx.a, 3650, now=NOW) == {
            "tenant_id": str(ctx.a), "alert_retention_days": 3650}
    for days in (29, 3651, 0, -60, True, 60.0, "60", None):
        with pytest.raises(ServiceError, match="Invalid alert retention"):
            with ctx.owner.session() as session:
                administration.set_alert_retention(session, ctx.a, days, now=NOW)
    with pytest.raises(NotFound):
        with ctx.owner.session() as session:
            administration.set_alert_retention(session, uuid4(), 60, now=NOW)
    with ctx.owner.session() as session:
        assert session.get(Tenant, ctx.a).alert_retention_days == 3650
        assert session.get(Tenant, ctx.b).alert_retention_days == 60
        rows = session.execute(select(AuditEvent.actor_type, AuditEvent.action, AuditEvent.object_type,
                                      AuditEvent.object_id, AuditEvent.details).where(
            AuditEvent.tenant_id == ctx.a, AuditEvent.action == "tenant_alert_retention_set")).all()
    assert [tuple(row) for row in rows] == [("local_admin", "tenant_alert_retention_set", "tenant", ctx.a, None)] * 2
    assert audit_count(ctx.owner, ctx.a) == before + 2
    # The CHECK holds the same bounds for any writer.
    for days in (29, 3651):
        with pytest.raises(IntegrityError):
            with ctx.owner.session() as session:
                session.get(Tenant, ctx.b).alert_retention_days = days
    for days in (30, 3650):
        with ctx.owner.session() as session:
            session.get(Tenant, ctx.b).alert_retention_days = days


def test_set_alert_retention_cli_needs_the_owner_credential(event_tenants, monkeypatch, capsys):
    ctx = event_tenants
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["set-alert-retention", "--tenant-id", str(ctx.a), "--days", "90"]) == 0
    assert json.loads(capsys.readouterr().out) == {"tenant_id": str(ctx.a), "alert_retention_days": 90}
    for days in ("29", "3651"):
        assert cli.main(["set-alert-retention", "--tenant-id", str(ctx.a), "--days", days]) == 1
        assert "Invalid alert retention" in capsys.readouterr().err
    # The runtime role cannot change a tenant's retention (tenants has UPDATE (id) only).
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", database_url(ctx.runtime))
    assert cli.main(["set-alert-retention", "--tenant-id", str(ctx.a), "--days", "45"]) == 1
    assert "Database operation failed" in capsys.readouterr().err
    with ctx.owner.session() as session:
        assert session.get(Tenant, ctx.a).alert_retention_days == 90


# --- alerts prune ----------------------------------------------------------------------------------------------

def test_prune_deletes_only_closed_alerts_past_each_tenants_retention(event_tenants, monkeypatch):
    ctx = event_tenants
    pruned(monkeypatch, ctx.a, ctx.b)
    with ctx.owner.session() as session:
        administration.set_alert_retention(session, ctx.b, 30, now=NOW)
    device_a, device_b = enrolled(ctx.runtime, ctx.admin_a, ctx.a), enrolled(ctx.runtime, ctx.admin_b, ctx.b)
    admin_a, admin_b = principal_id(ctx.owner, ctx.admin_a), principal_id(ctx.owner, ctx.admin_b)
    alert = partial(add_alert, ctx.owner, ctx.a, device_a, admin_a)
    # Tenant a keeps 60 days (the default), tenant b 30. Age counts from closed_at only.
    boundary = alert(closed_at=NOW - 60 * DAY)  # exactly the retention: not older than it
    kept = {alert(status="open"), alert(status="acknowledged"), boundary,
            alert(closed_at=NOW - DAY, seen_at=NOW - 400 * DAY),  # opened long ago, closed recently
            add_alert(ctx.owner, ctx.b, device_b, admin_b, closed_at=NOW - 30 * DAY + MICROSECOND)}
    alert(closed_at=NOW - 60 * DAY - MICROSECOND)
    alert(closed_at=NOW - 400 * DAY)
    add_alert(ctx.owner, ctx.b, device_b, admin_b, closed_at=NOW - 31 * DAY)

    def stored():
        return alert_ids(ctx.owner, device_a) | alert_ids(ctx.owner, device_b)

    assert prune(ctx, NOW) == result(tenants=2, deleted=3)
    assert stored() == kept
    # Nothing is left to delete; the boundary alert goes one microsecond later, the open and acknowledged never.
    assert prune(ctx, NOW) == result(tenants=2)
    assert prune(ctx, NOW + MICROSECOND) == result(tenants=2, deleted=1)
    assert stored() == kept - {boundary}
    assert prune(ctx, NOW + 3000 * DAY) == result(tenants=2, deleted=2)
    with ctx.owner.session() as session:
        assert sorted(session.scalars(select(Alert.status).where(Alert.id.in_(stored())))) == ["acknowledged", "open"]


def silent_device(ctx):
    """A V3 device of tenant a whose one snapshot arrived at NOW: silent from at(901) on."""
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    report(ctx.runtime, device, snapshot(3, 1, agent_v3(60)), NOW)
    return device


def test_the_episode_rule_keeps_the_current_silence_alert_until_the_device_reports_again(event_tenants,
                                                                                         monkeypatch):
    ctx = event_tenants
    pruned(monkeypatch, ctx.a)
    swept(monkeypatch, ctx.a)
    silent, revoked = silent_device(ctx), silent_device(ctx)
    assert run_sweep(ctx, at(SILENCE + 1))["alerts_opened"] == 2
    [episode], [gone] = silent_alerts(ctx.owner, silent), silent_alerts(ctx.owner, revoked)
    transition(ctx, "close_alert", episode.id, at(1000))
    transition(ctx, "close_alert", gone.id, at(1000))
    # Another rule's expired closed alert on the same silent device goes as usual.
    other = add_alert(ctx.owner, ctx.a, silent, principal_id(ctx.owner, ctx.admin_a), closed_at=at(1000))
    # A revoked device is never swept again: its alerts go like any other.
    revoke(ctx, revoked, at(1100))
    later = at(1000) + 61 * DAY
    assert prune(ctx, later) == result(deleted=2, kept=1)
    assert alert_ids(ctx.owner, silent) == {episode.id} and alert_ids(ctx.owner, revoked) == set()
    assert other not in alert_ids(ctx.owner, silent)
    # Every run keeps and counts it again, however old it gets.
    assert prune(ctx, later + 3000 * DAY) == result(kept=1)
    # A new snapshot moves the device's key forward: the old episode's alert goes on the next run. (The
    # snapshot is received within the credential's one-day lifetime; prune compares keys, not times.)
    report(ctx.runtime, silent, snapshot(3, 2, agent_v3(60)), at(2000))
    assert prune(ctx, later + MICROSECOND) == result(deleted=1)
    assert alert_ids(ctx.owner, silent) == set()


def test_prune_and_sweep_over_the_same_silent_device_open_no_second_alert(event_tenants, monkeypatch):
    # Decision 3a: the sweep's unlocked episode read stays true, because prune never deletes the alert of the
    # current episode; without the episode rule the sweep after a prune would open the episode a second time.
    ctx = event_tenants
    pruned(monkeypatch, ctx.a)
    swept(monkeypatch, ctx.a)
    device = silent_device(ctx)
    assert run_sweep(ctx, at(SILENCE + 1))["alerts_opened"] == 1
    [episode] = silent_alerts(ctx.owner, device)
    transition(ctx, "close_alert", episode.id, at(1000))
    unchanged = {"tenants": 1, "failed_tenants": 0, "devices_checked": 1, "alerts_opened": 0, "already_alerted": 1,
                 "suppressed": 0, "devices_busy": 0}
    for days in (61, 62, 400):
        when = at(1000) + days * DAY
        assert prune(ctx, when) == result(kept=1)
        assert run_sweep(ctx, when) == unchanged
    # Run side by side as well.
    with ThreadPoolExecutor(max_workers=2) as pool:
        for round_ in range(5):
            when = at(1000) + (500 + round_) * DAY
            pruning, sweeping = pool.submit(prune, ctx, when), pool.submit(run_sweep, ctx, when)
            assert pruning.result(timeout=20) == result(kept=1)
            assert sweeping.result(timeout=20) == unchanged
    [still] = silent_alerts(ctx.owner, device)
    assert (still.id, still.status, still.occurrences, still.closed_at) == (episode.id, "closed", 1, at(1000))


def test_prune_walks_bounded_chunks_past_the_kept_alerts(event_tenants, monkeypatch):
    ctx = event_tenants
    pruned(monkeypatch, ctx.a)
    swept(monkeypatch, ctx.a)
    device = silent_device(ctx)
    run_sweep(ctx, at(SILENCE + 1))
    [episode] = silent_alerts(ctx.owner, device)
    transition(ctx, "close_alert", episode.id, at(1000))
    closer = principal_id(ctx.owner, ctx.admin_a)
    # Three expired alerts closed before the episode's alert and three after it, all past 60 days.
    others = [add_alert(ctx.owner, ctx.a, device, closer, closed_at=at(1000) + hours * timedelta(hours=1))
              for hours in (-3, -2, -1, 1, 2, 3)]
    chunks, original = [], alerts._prune_chunk

    def observed(session, tenant_id, cutoff, after, batch_size):
        read, last, deleted, kept = original(session, tenant_id, cutoff, after, batch_size)
        chunks.append((read, deleted, kept))
        return read, last, deleted, kept

    monkeypatch.setattr(alerts, "_prune_chunk", observed)
    later = at(1000) + 61 * DAY
    assert prune(ctx, later, batch_size=2) == result(deleted=6, kept=1)
    # Keyset chunks of two by (closed_at, id): the kept alert is read once, in the second chunk.
    assert chunks == [(2, 2, 0), (2, 1, 1), (2, 2, 0), (1, 1, 0)]
    assert alert_ids(ctx.owner, device) == {episode.id} and not set(others) & alert_ids(ctx.owner, device)
    chunks.clear()
    assert prune(ctx, later, batch_size=2) == result(kept=1)
    assert chunks == [(1, 0, 1)]


@pytest.mark.parametrize("size", [0, 5001, True, 2.0])
def test_prune_batch_size_is_bounded(event_tenants, size):
    with pytest.raises(ValueError, match="Invalid prune batch size"):
        prune(event_tenants, NOW, batch_size=size)


def test_every_run_writes_one_audit_record_per_tenant_with_its_counts(event_tenants, monkeypatch):
    ctx = event_tenants
    pruned(monkeypatch, ctx.a, ctx.b)
    swept(monkeypatch, ctx.a)
    device = silent_device(ctx)
    run_sweep(ctx, at(SILENCE + 1))
    [episode] = silent_alerts(ctx.owner, device)
    transition(ctx, "close_alert", episode.id, at(1000))
    closer = principal_id(ctx.owner, ctx.admin_a)
    later = at(1000) + 61 * DAY
    for hours in (1, 2, 3):
        add_alert(ctx.owner, ctx.a, device, closer, closed_at=at(1000) + hours * timedelta(hours=1))
    before = {tenant: audit_count(ctx.owner, tenant) for tenant in (ctx.a, ctx.b)}
    again = later + timedelta(seconds=1)
    assert prune(ctx, later) == result(tenants=2, deleted=3, kept=1)
    assert prune(ctx, again) == result(tenants=2, kept=1)
    assert [tuple(row) for row in prune_records(ctx.owner, ctx.a)] == [
        ("local_admin", None, "tenant", ctx.a, details(deleted=3, kept=1), later),
        ("local_admin", None, "tenant", ctx.a, details(kept=1), again)]
    # A tenant with nothing to delete gets its record too.
    assert [tuple(row) for row in prune_records(ctx.owner, ctx.b)] == [
        ("local_admin", None, "tenant", ctx.b, details(), later), ("local_admin", None, "tenant", ctx.b, details(), again)]
    assert {tenant: audit_count(ctx.owner, tenant) - before[tenant] for tenant in (ctx.a, ctx.b)} == {ctx.a: 2, ctx.b: 2}
    # The audit API is unchanged: the record's counts are never returned.
    with ctx.runtime.session() as session:
        items = audit.list_audit(session, ctx.admin_a, ctx.a, limit=2)["items"]
    assert [item["action"] for item in items] == ["alerts_pruned", "alerts_pruned"]
    assert all(set(item) == {"id", "tenant_id", "actor_type", "actor_id", "action", "object_type", "object_id",
                             "outcome", "created_at"} for item in items)


def three_tenants_with_expired_alerts(ctx, now):
    """Tenants first < middle < last by id; each holds two closed alerts expired at `now` and one fresh."""
    with ctx.owner.session() as session:
        created = [UUID(administration.create_tenant(session, f"Alert prune {index}", now=NOW)["id"])
                   for index in range(3)]
        for tenant in created:
            administration.set_membership(session, tenant, ctx.admin_a.issuer, ctx.admin_a.subject, "tenant_admin",
                                          now=NOW)
    ordered = sorted(created)
    closer = principal_id(ctx.owner, ctx.admin_a)
    devices = [enrolled(ctx.runtime, ctx.admin_a, tenant) for tenant in ordered]
    for tenant, device in zip(ordered, devices):
        for days in (90, 80, 1):
            add_alert(ctx.owner, tenant, device, closer, closed_at=now - days * DAY)
    return ordered, devices


def test_a_failing_tenant_is_skipped_counted_and_audited_as_incomplete(event_tenants, monkeypatch):
    ctx = event_tenants
    (first, middle, last), devices = three_tenants_with_expired_alerts(ctx, NOW)
    pruned(monkeypatch, first, middle, last)
    # Another transaction holds the middle tenant's expired alerts: its chunk runs into the 3 s lock timeout.
    blocker = ctx.owner.session_factory()
    try:
        blocker.execute(select(Alert).where(Alert.tenant_id == middle, Alert.status == "closed").with_for_update())
        summary = prune(ctx, NOW)
    finally:
        blocker.rollback()
        blocker.close()
    assert summary == result(tenants=3, deleted=4, failed=1)
    assert [len(alert_ids(ctx.owner, device)) for device in devices] == [1, 3, 1]
    assert [row.details for row in prune_records(ctx.owner, middle)] == [details(complete=False)]
    assert [row.details for row in prune_records(ctx.owner, first)] == [details(deleted=2)]
    # The next run (a second later, so that its records sort after the first run's) retries it.
    assert prune(ctx, NOW + timedelta(seconds=1)) == result(tenants=3, deleted=2)
    assert [row.details for row in prune_records(ctx.owner, middle)] == [details(complete=False), details(deleted=2)]


def test_a_tenant_whose_audit_record_cannot_be_written_counts_as_failed(event_tenants, monkeypatch):
    ctx = event_tenants
    (first, middle, last), devices = three_tenants_with_expired_alerts(ctx, NOW)
    pruned(monkeypatch, first, middle, last)
    blocker = ctx.owner.session_factory()
    try:
        # The record needs the tenant row lock; the deletions do not.
        blocker.execute(select(Tenant).where(Tenant.id == middle).with_for_update())
        summary = prune(ctx, NOW)
    finally:
        blocker.rollback()
        blocker.close()
    assert summary == result(tenants=3, deleted=6, failed=1)
    assert [len(alert_ids(ctx.owner, device)) for device in devices] == [1, 1, 1]
    assert prune_records(ctx.owner, middle) == []


def failing_chunk(tenant_id, *, after):
    """A _prune_chunk that fails for one tenant once `after` of its chunks have been committed."""
    original, calls = alerts._prune_chunk, []

    def chunk(session, tenant, cutoff, position, batch_size):
        if tenant == tenant_id:
            calls.append(tenant)
            if len(calls) > after:
                raise OperationalError("DELETE FROM alerts", {}, Exception("canceling statement due to lock timeout"))
        return original(session, tenant, cutoff, position, batch_size)
    return chunk


def test_alerts_prune_cli_runs_only_with_the_runtime_credential(event_tenants, monkeypatch, capsys):
    ctx = event_tenants
    pruned(monkeypatch, ctx.a, ctx.b)
    real_now = datetime.now(timezone.utc)
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)
    closer = principal_id(ctx.owner, ctx.admin_a)
    expired = add_alert(ctx.owner, ctx.a, device, closer, closed_at=real_now - 61 * DAY)
    fresh = add_alert(ctx.owner, ctx.a, device, closer, closed_at=real_now - 59 * DAY)
    monkeypatch.delenv("SP_DATABASE_URL", raising=False)
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["alerts", "prune"]) == 1
    output = capsys.readouterr()
    assert (output.out, output.err.strip()) == ("", "SP_DATABASE_URL is required for alert retention")
    # The owner credential is refused before anything is read or written: there is no owner fallback.
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["alerts", "prune"]) == 1
    output = capsys.readouterr()
    assert (output.out, output.err.strip()) == ("", "alerts prune requires the separate unprivileged runtime "
                                                    "database role")
    assert alert_ids(ctx.owner, device) == {expired, fresh} and prune_records(ctx.owner, ctx.a) == []
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.runtime))
    assert cli.main(["alerts", "prune"]) == 0
    output = capsys.readouterr()
    assert output.out.count("\n") == 1 and output.err == ""
    summary = json.loads(output.out)
    assert list(summary) == RESULT_KEYS and summary == result(tenants=2, deleted=1)
    assert "postgresql" not in output.out + output.err
    assert alert_ids(ctx.owner, device) == {fresh}
    assert [row.details for row in prune_records(ctx.owner, ctx.a)] == [details(deleted=1)]


def test_alerts_prune_cli_exits_1_when_a_tenant_failed_after_committed_chunks(event_tenants, monkeypatch, capsys):
    ctx = event_tenants
    (first, middle, last), devices = three_tenants_with_expired_alerts(ctx, datetime.now(timezone.utc))
    pruned(monkeypatch, first, middle, last)
    # One-alert chunks: the middle tenant commits one chunk, then its second fails.
    monkeypatch.setattr(alerts, "prune_closed_alerts", partial(alerts.prune_closed_alerts, batch_size=1))
    monkeypatch.setattr(alerts, "_prune_chunk", failing_chunk(middle, after=1))
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.runtime))
    assert cli.main(["alerts", "prune"]) == 1
    output = capsys.readouterr()
    assert json.loads(output.out) == result(tenants=3, deleted=5, failed=1)
    assert output.err.startswith("alerts prune incomplete: 1 tenant(s) failed and were skipped")
    assert "no success was recorded" not in output.err and "postgresql" not in output.out + output.err
    # The committed chunk of the failing tenant stays deleted, counted and audited as incomplete.
    assert [len(alert_ids(ctx.owner, device)) for device in devices] == [1, 2, 1]
    assert [row.details for row in prune_records(ctx.owner, middle)] == [details(deleted=1, complete=False)]


# --- the audit cap ---------------------------------------------------------------------------------------------

def fill_audit(owner, tenant, total):
    """Old local_admin audit rows written directly by the owner until the tenant holds `total`; returns the oldest."""
    with owner.session() as session:
        held = session.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == tenant))
        rows = [{"id": uuid4(), "tenant_id": tenant, "actor_type": "local_admin", "actor_id": None,
                 "action": "membership_set", "object_type": "tenant", "object_id": tenant, "outcome": "success",
                 "created_at": NOW - 400 * DAY + index * MICROSECOND} for index in range(total - held)]
        session.execute(insert(AuditEvent), rows)
    return rows[0]["id"]


def audit_exists(owner, audit_id):
    with owner.session() as session:
        return session.get(AuditEvent, audit_id) is not None


def test_prune_and_the_retention_setters_keep_the_audit_cap_of_sp_max_audit_events_per_tenant(event_tenants,
                                                                                              monkeypatch, capsys):
    """A tenant above the default 10000 audit rows under a raised cap loses none of them to a prune or a setter."""
    ctx = event_tenants
    pruned(monkeypatch, ctx.a)
    above = DEFAULT_LIMITS.max_audits + 50
    oldest = fill_audit(ctx.owner, ctx.a, above)
    assert prune(ctx, NOW, limits=ServiceLimits(max_audits=20000)) == result()
    assert audit_count(ctx.owner, ctx.a) == above + 1
    monkeypatch.setenv("SP_MAX_AUDIT_EVENTS_PER_TENANT", "20000")
    monkeypatch.setenv("SP_DATABASE_URL", database_url(ctx.runtime))
    monkeypatch.setenv("SP_MIGRATION_DATABASE_URL", database_url(ctx.owner))
    assert cli.main(["alerts", "prune"]) == 0
    assert json.loads(capsys.readouterr().out) == result()
    assert cli.main(["set-alert-retention", "--tenant-id", str(ctx.a), "--days", "90"]) == 0
    assert cli.main(["set-event-retention", "--tenant-id", str(ctx.a), "--days", "30"]) == 0
    capsys.readouterr()
    assert audit_count(ctx.owner, ctx.a) == above + 4 and audit_exists(ctx.owner, oldest)
    # The configured cap still evicts, oldest first: 5 rows go so that the new record fits under 10050.
    monkeypatch.setenv("SP_MAX_AUDIT_EVENTS_PER_TENANT", str(above))
    assert cli.main(["alerts", "prune"]) == 0
    capsys.readouterr()
    assert audit_count(ctx.owner, ctx.a) == above and not audit_exists(ctx.owner, oldest)
    # Without the variable the cap is the default 10000: one run evicts the 51 oldest records.
    monkeypatch.delenv("SP_MAX_AUDIT_EVENTS_PER_TENANT")
    assert cli.main(["alerts", "prune"]) == 0
    capsys.readouterr()
    assert audit_count(ctx.owner, ctx.a) == DEFAULT_LIMITS.max_audits
    # An invalid cap stops every command before it reads or writes anything.
    records = len(prune_records(ctx.owner, ctx.a))
    for value, message in (("9", "Invalid bounded platform setting"), ("1000001", "Invalid bounded platform setting"),
                           ("many", "Invalid integer setting: SP_MAX_AUDIT_EVENTS_PER_TENANT")):
        monkeypatch.setenv("SP_MAX_AUDIT_EVENTS_PER_TENANT", value)
        for argv in (["alerts", "prune"], ["set-alert-retention", "--tenant-id", str(ctx.a), "--days", "45"],
                     ["set-event-retention", "--tenant-id", str(ctx.a), "--days", "7"]):
            assert cli.main(argv) == 1
            output = capsys.readouterr()
            assert (output.out, output.err.strip()) == ("", message)
    assert len(prune_records(ctx.owner, ctx.a)) == records and audit_count(ctx.owner, ctx.a) == DEFAULT_LIMITS.max_audits
    with ctx.owner.session() as session:
        tenant = session.get(Tenant, ctx.a)
        assert (tenant.alert_retention_days, tenant.event_retention_days) == (90, 30)


def plan_scans(plan):
    """Every (node type, index name, index condition) of an EXPLAIN (FORMAT JSON) plan tree."""
    found = [(plan["Node Type"], plan.get("Index Name"), plan.get("Index Cond", ""))]
    for child in plan.get("Plans", []):
        found += plan_scans(child)
    return found


def generic_plan(session, statement):
    # Sent unprepared: a prepared EXPLAIN would itself demand the $n parameters.
    with session.connection().connection.dbapi_connection.cursor() as cursor:
        cursor.execute("EXPLAIN (GENERIC_PLAN, FORMAT JSON) " + statement, prepare=False)
        return plan_scans(cursor.fetchone()[0][0]["Plan"])


def bulk_alerts(owner, tenant, device_id, closer, count, *, closed_every, open_every):
    """`count` event_loss alerts of one device in one statement: every `open_every`-th open, the rest closed,
    closed_at spread back from NOW by `closed_every` per alert."""
    with owner.session() as session:
        session.execute(text(
            "INSERT INTO alerts (id, tenant_id, device_id, rule, severity, dedup_key, status, occurrences, "
            "first_event_seq, last_event_seq, first_seen_at, last_seen_at, evidence, closed_at, closed_by, "
            "created_at, updated_at) "
            "SELECT gen_random_uuid(), CAST(:tenant AS uuid), CAST(:device AS uuid), 'event_loss', 'medium', "
            "encode(sha256(convert_to(CAST(:device AS text) || n, 'UTF8')), 'hex'), "
            "CASE WHEN n % :open_every = 0 THEN 'open' ELSE 'closed' END, 1, 1, 1, "
            "CAST(:now AS timestamptz) - interval '400 days', CAST(:now AS timestamptz) - interval '400 days', "
            "CAST('{\"missing_events\": 1}' AS jsonb), "
            "CASE WHEN n % :open_every = 0 THEN NULL ELSE CAST(:now AS timestamptz) - n * CAST(:every AS interval) END, "
            "CASE WHEN n % :open_every = 0 THEN NULL ELSE CAST(:closer AS uuid) END, "
            "CAST(:now AS timestamptz) - interval '400 days', CAST(:now AS timestamptz) - interval '400 days' "
            "FROM generate_series(1, :count) AS n"),
            {"tenant": tenant, "device": device_id, "closer": closer, "now": NOW, "count": count,
             "open_every": open_every, "every": closed_every})


def test_the_prune_statements_use_the_closed_alert_index_under_a_generic_plan(event_tenants, monkeypatch):
    # psycopg prepares a statement after five runs on a pooled connection, and PostgreSQL then may switch it to its
    # generic plan. Here every statement is prepared at once and planned generically: the read and the delete must
    # both stay a range of ix_alert_tenant_closed, the partial index whose predicate they repeat with a literal.
    ctx = event_tenants
    pruned(monkeypatch, ctx.a)
    devices = [UUID(enrolled(ctx.runtime, admin, tenant)["device_id"])
               for admin, tenant in ((ctx.admin_a, ctx.a), (ctx.admin_a, ctx.a), (ctx.admin_b, ctx.b))]
    closers = {ctx.a: principal_id(ctx.owner, ctx.admin_a), ctx.b: principal_id(ctx.owner, ctx.admin_b)}
    generic = generic_plan_database(ctx.runtime)
    try:
        # A deployment's shape: most alerts closed, in several tenants and devices, a few open.
        bulk_alerts(ctx.owner, ctx.b, devices[2], closers[ctx.b], 20000, closed_every="20 minutes", open_every=10)
        bulk_alerts(ctx.owner, ctx.a, devices[1], closers[ctx.a], 5000, closed_every="30 minutes", open_every=5)
        bulk_alerts(ctx.owner, ctx.a, devices[0], closers[ctx.a], 1000, closed_every="2 hours", open_every=4)
        with ctx.owner.session() as session:
            session.execute(text("ANALYZE alerts"))
            expired = session.scalar(text(
                "SELECT count(*) FROM alerts WHERE tenant_id = :tenant AND status = 'closed' "
                "AND closed_at < CAST(:cutoff AS timestamptz)"), {"tenant": ctx.a, "cutoff": NOW - 60 * DAY})
        summary = alerts.prune_closed_alerts(generic, now=NOW, batch_size=500)
        assert summary == result(deleted=expired) and expired > 1000
        with generic.session() as session:
            prepared = session.execute(text("SELECT statement, generic_plans FROM pg_prepared_statements")).all()
            statements = {kind: [(statement, count) for statement, count in prepared
                                 if " ".join(statement.split()).upper().startswith(prefix)]
                          for kind, prefix in (("read", "SELECT ID, DEVICE_ID, RULE, DEDUP_KEY, CLOSED_AT FROM ALERTS"),
                                               ("delete", "DELETE FROM ALERTS"))}
            plans = {kind: [generic_plan(session, statement) for statement, _ in found]
                     for kind, found in statements.items()}
        for kind in ("read", "delete"):
            # Each ran prepared, with its generic plan.
            assert len(statements[kind]) == 1 and statements[kind][0][1] >= 1, prepared
            [nodes] = plans[kind]
            # A Bitmap Heap Scan names no index: it reads the rows that its Bitmap Index Scan child found. The planner
            # picks it or an Index Scan by cost (CI's PostgreSQL 18 picked it for the delete), and either way every
            # row comes through the partial index, as INDEX_RANGE_NODES in test_events.py allows for the cap delete.
            # Every other scan node must name ix_alert_tenant_closed, so a Seq Scan or another index still fails.
            scans = [node for node in nodes if "Scan" in node[0] and node[0] != "Bitmap Heap Scan"]
            assert scans and all(name == "ix_alert_tenant_closed" for _, name, _ in scans), nodes
            assert any("tenant_id = $1" in condition and "closed_at" in condition for _, _, condition in scans), nodes
    finally:
        generic.close()
        with ctx.owner.session() as session:
            session.execute(text("DELETE FROM alerts WHERE device_id = ANY(CAST(:devices AS uuid[]))"),
                            {"devices": devices})


# --- grants, schema and migration 0006 -------------------------------------------------------------------------

def test_runtime_role_may_delete_alerts_but_not_set_retention(pg_service_databases):
    _, runtime = pg_service_databases
    with runtime.session() as session:
        privilege = {name: session.scalar(text("SELECT has_table_privilege(current_user, 'alerts', :name)"),
                                          {"name": name}) for name in ("DELETE", "TRUNCATE")}
        retention = session.scalar(text("SELECT has_column_privilege(current_user, 'tenants', "
                                        "'alert_retention_days', 'UPDATE')"))
        details_update = session.scalar(text("SELECT has_table_privilege(current_user, 'audit_events', 'UPDATE')"))
    assert privilege == {"DELETE": True, "TRUNCATE": False} and retention is False and details_update is False


def retention_schema(connection):
    """What 0006 adds: the tenant column and CHECK, the audit column and CHECK, the alerts index."""
    def column(table, name):
        row = connection.execute(text(
            "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table AND column_name = :name"),
            {"table": table, "name": name}).first()
        return None if row is None else tuple(row)

    def check(table, name):
        return connection.scalar(text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name "
            "AND conrelid = CAST(:table AS regclass)"), {"name": name, "table": "public." + table})

    return {"tenant_column": column("tenants", "alert_retention_days"),
            "tenant_check": check("tenants", "ck_tenant_alert_retention"),
            "audit_column": column("audit_events", "details"),
            "audit_check": check("audit_events", "ck_audit_details"),
            "index": connection.scalar(text("SELECT indexdef FROM pg_indexes WHERE schemaname = 'public' "
                                            "AND indexname = 'ix_alert_tenant_closed'"))}


HEAD_SCHEMA = {
    "tenant_column": ("integer", "NO", "60"),
    "tenant_check": "CHECK (((alert_retention_days >= 30) AND (alert_retention_days <= 3650)))",
    "audit_column": ("jsonb", "YES", None),
    "audit_check": "CHECK (((details IS NULL) OR ((jsonb_typeof(details) = 'object'::text) AND "
                   "(octet_length((details)::text) <= 1024))))",
    "index": "CREATE INDEX ix_alert_tenant_closed ON public.alerts USING btree (tenant_id, closed_at) "
             "WHERE (status = 'closed'::text)",
}


def test_the_head_is_0006_and_its_schema_matches_the_models(pg_service_databases):
    owner, _ = pg_service_databases
    script = ScriptDirectory.from_config(Config(str(PROJECT / "alembic.ini")))
    assert script.get_heads() == [RETENTION]
    assert script.get_revision(RETENTION).down_revision == "0005_stage3_detection"
    with owner.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == RETENTION
        assert retention_schema(connection) == HEAD_SCHEMA
    column = Tenant.__table__.c.alert_retention_days
    assert (type(column.type).__name__, column.nullable, column.server_default.arg.text) == ("Integer", False, "60")
    assert AuditEvent.__table__.c.details.nullable is True

    def model_check(model, name):
        [check] = [item for item in model.__table__.constraints
                   if isinstance(item, CheckConstraint) and item.name == name]
        return " ".join(str(check.sqltext).split())

    module = migration_module(RETENTION)
    statements = [" ".join(statement.split()) for statement in module.DDL_STATEMENTS]
    assert ("ALTER TABLE tenants ADD COLUMN alert_retention_days INTEGER DEFAULT 60 NOT NULL CONSTRAINT "
            "ck_tenant_alert_retention CHECK (" + model_check(Tenant, "ck_tenant_alert_retention") + ")") in statements
    assert ("ALTER TABLE audit_events ADD COLUMN details JSONB CONSTRAINT ck_audit_details CHECK ("
            + model_check(AuditEvent, "ck_audit_details") + ")") in statements
    [index] = [item for item in Alert.__table__.indexes if item.name == "ix_alert_tenant_closed"]
    assert " ".join(str(CreateIndex(index).compile(dialect=postgresql.dialect())).split()) in statements


def offline_sql(run):
    """The statements that a migration step emits in alembic's offline (--sql) mode, in order."""
    buffer = io.StringIO()
    with Operations.context(MigrationContext.configure(dialect_name="postgresql",
                                                       opts={"as_sql": True, "output_buffer": buffer})):
        run()
    return [" ".join(item.split()) for item in buffer.getvalue().split(";\n\n") if item.strip()]


LOCKS_UP = ["LOCK TABLE tenants IN ACCESS EXCLUSIVE MODE", "LOCK TABLE alerts IN SHARE MODE",
            "LOCK TABLE audit_events IN ACCESS EXCLUSIVE MODE"]
LOCKS_DOWN = ["LOCK TABLE tenants IN ACCESS EXCLUSIVE MODE", "LOCK TABLE alerts IN ACCESS EXCLUSIVE MODE",
              "LOCK TABLE audit_events IN ACCESS EXCLUSIVE MODE"]


def test_migration_0006_takes_its_locks_first_in_a_fixed_order_with_the_statement_timeout_lifted():
    # Round 1 measured that a late lock wait keeps the earlier locks held: each direction takes all three table
    # locks before any work, in the order an operator's acknowledge or close takes them (tenant, alert, audit).
    module = migration_module(RETENTION)
    assert (module.revision, module.down_revision) == (RETENTION, "0005_stage3_detection")
    assert (module.LIFT_STATEMENT_TIMEOUT, module.RESTORE_STATEMENT_TIMEOUT) == (
        "SET LOCAL statement_timeout = 0", "SET LOCAL statement_timeout TO DEFAULT")
    for run, statements, locks in ((module.upgrade, module.DDL_STATEMENTS, LOCKS_UP),
                                   (module.downgrade, module.DOWNGRADE_STATEMENTS, LOCKS_DOWN)):
        emitted = offline_sql(run)
        assert emitted == [module.LIFT_STATEMENT_TIMEOUT, *(" ".join(item.split()) for item in statements),
                           module.RESTORE_STATEMENT_TIMEOUT]
        assert emitted[1:4] == locks
        assert not [statement for statement in emitted[4:] if statement.startswith("LOCK")]
        assert not [statement for statement in emitted if "lock_timeout" in statement]


def test_migration_0006_down_and_up_in_a_rolled_back_transaction(event_tenants):
    ctx = event_tenants
    module = migration_module(RETENTION)
    with ctx.owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            assert retention_schema(connection) == HEAD_SCHEMA and timeouts(connection) == ("5s", "3s")
            connection.execute(text("UPDATE tenants SET alert_retention_days = 45 WHERE id = :tenant"),
                               {"tenant": ctx.a})
            records = {}
            for action in ("alerts_pruned", "tenant_alert_retention_set", "tenant_event_retention_set"):
                records[action] = uuid4()
                connection.execute(text(
                    "INSERT INTO audit_events (id, tenant_id, actor_type, action, object_type, object_id, outcome, "
                    "created_at, details) VALUES (:id, :tenant, 'local_admin', :action, 'tenant', :tenant, "
                    "'success', :at, CAST(:details AS jsonb))"),
                    {"id": records[action], "tenant": ctx.a, "action": action, "at": NOW,
                     "details": json.dumps(details()) if action == "alerts_pruned" else None})

            def remaining():
                return set(connection.scalars(text("SELECT action FROM audit_events WHERE id = ANY(CAST(:ids AS "
                                                   "uuid[]))"), {"ids": list(records.values())}))

            with Operations.context(MigrationContext.configure(connection)):
                # Every statement runs without a statement bound and with env.py's lock bound, both ways.
                for run, statements, expected in (
                        (module.downgrade, module.DOWNGRADE_STATEMENTS, {key: None for key in HEAD_SCHEMA}),
                        (module.upgrade, module.DDL_STATEMENTS, HEAD_SCHEMA)):
                    seen = settings_per_statement(connection, run)
                    assert seen == [(module.LIFT_STATEMENT_TIMEOUT, "5s", "3s"),
                                    *((" ".join(item.split()), "0", "3s") for item in statements),
                                    (module.RESTORE_STATEMENT_TIMEOUT, "0", "3s")]
                    assert retention_schema(connection) == expected and timeouts(connection) == ("5s", "3s")
                    if run is module.downgrade:
                        # The 0005 code knows neither action, and the console rejects an unknown one.
                        assert remaining() == {"tenant_event_retention_set"}
                # Up again: every tenant starts at the default; the deleted records do not return.
                assert connection.scalar(text("SELECT alert_retention_days FROM tenants WHERE id = :tenant"),
                                         {"tenant": ctx.a}) == 60
                assert remaining() == {"tenant_event_retention_set"}
                module.downgrade()
                module.upgrade()
                assert retention_schema(connection) == HEAD_SCHEMA
        finally:
            transaction.rollback()
    with ctx.owner.engine.connect() as connection:
        assert retention_schema(connection) == HEAD_SCHEMA
