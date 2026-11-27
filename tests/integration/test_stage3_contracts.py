"""Stage 3 detection contracts on real PostgreSQL: migration 0005 (head, CHECK parity, the agent_silent null rule,
the two indexes, its statement timeout, upgrade -> downgrade -> upgrade), event v2 batches and Snapshot V3 through
the real HTTP app and signed JWTs, interleaved with v1 and V2.

The pure contracts are tested in tests/unit/test_event_v2_contracts.py and tests/unit/test_snapshot_v3_contracts.py.

Ingestion hands every accepted batch to services.alerts.raise_alerts, whose Stage 3 rules are tested in
tests/integration/test_stage3_alerts.py. Most tests here that store the six new kinds replace events.raise_alerts
with a recording double (the alert_calls fixture) and prove that ingestion hands it exactly the accepted batch's
events, once, and never on a retry, conflict, 413 or 422. A batch of every kind, the coverage_gap view and the
three v1 kinds in their v2 shapes also run through the real alert path.
"""
import hashlib
import io
import json
import re
from uuid import UUID, uuid4

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import CheckConstraint, event, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex

from security_platform.contracts import (MAX_SNAPSHOT_SEQUENCE, PRODUCT_IDS, SnapshotEnvelope, SnapshotEnvelopeV3,
                                         canonical_json, snapshot_digest)
from security_platform.event_contracts import (COVERAGE_SOURCES, EVENT_FIELDS, EVENT_KINDS, EVENT_KINDS_V1,
                                               EVENT_VIEW_FIELDS, EventBatch, EventBatchTooLarge, EventBatchV2,
                                               canonical_event_batch, event_batch_digest, parse_event_batch)
from security_platform.models import Alert, EndpointEvent
from security_platform.services import enrollment, events, snapshots
from security_platform.services.alerts import RULES as ALERT_RULES
from test_api import api_context, api_database, auth, enroll  # noqa: F401  (shared HTTP fixtures)
from test_events import PROJECT, event_tenants, migration_module, stored  # noqa: F401  (shared fixtures)
from test_services import NOW, enrolled, pg_service_databases  # noqa: F401  (shared real-database fixture)


pytestmark = pytest.mark.integration
# The Stage 3 migration; 0006_alert_retention (alert retention) follows it and is the head.
STAGE3 = "0005_stage3_detection"
HEAD = "0006_alert_retention"
# ALERT_RULES is services.alerts.RULES (RULES = tuple(SEVERITY)), the ten alert rules of the P1 brief's section 8 in
# the order of its SEVERITY keys: the single source the schema must mirror.
V1_RULES = ALERT_RULES[:4]
STAGE3_TABLES = ("endpoint_events", "alerts", "device_event_cursors")
EVENTS = "/api/v1/device/events"
SNAPSHOT = "/api/v1/device/snapshot"
MASKED = r"\Device\HarddiskVolume3\Users\*\Downloads\setup.exe"
CREATED = "2030-01-02T02:59:00.000001Z"
CANARY = "private-input-canary"
DIGEST = "0123456789abcdef" * 4


# --- v1 and v2 events (device times before NOW, 2030-01-02T03:04:05Z)

def v1_started(seq, **changes):
    return {"kind": "process_started", "event_seq": seq, "observed_at": "2030-01-02T03:00:00Z", "pid": 4000 + seq,
            "parent_pid": 4, "session_id": 1, "image": MASKED, **changes}


def v1_stopped(seq, **changes):
    return {"kind": "process_stopped", "event_seq": seq, "observed_at": "2030-01-02T03:00:01Z", "pid": 4000 + seq,
            "exit_code": 0, "image": "setup.exe", **changes}


def sensor(seq, **changes):
    return {"kind": "sensor_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:02Z", "state": "lost",
            "error_code": "session_in_use", **changes}


def started(seq, **changes):
    return v1_started(seq, **{"create_time": CREATED, "parent_create_time": "2030-01-02T02:00:00Z", **changes})


def stopped(seq, **changes):
    return v1_stopped(seq, **{"create_time": CREATED, **changes})


def scan(seq, **changes):
    return {"kind": "scan_detected", "event_seq": seq, "observed_at": "2030-01-02T03:00:03Z", "trigger": "startup_scan",
            "path": MASKED, "size": 68, "sha256": DIGEST, "rule_set_id": "a" * 64,
            "hits": [{"rule": "Sample_Rule", "severity": "medium"}], "omitted_hits": 0, "pid": 4321,
            "create_time": CREATED, "action_id": None, **changes}


def behavior(seq, **changes):
    return {"kind": "behavior_match", "event_seq": seq, "observed_at": "2030-01-02T03:00:04Z",
            "rule": "encoded_powershell", "rule_version": 1, "pid": 4321, "create_time": CREATED, "image": MASKED,
            "parent_image": None, "found_at_start": False, "command_line_source": "kernel_logger", **changes}


def persistence(seq, **changes):
    return {"kind": "persistence_change", "event_seq": seq, "observed_at": "2030-01-02T03:00:05Z",
            "location": "run_key", "scope": "user", "change": "added", "entry_id": "b" * 64, "target_image": MASKED,
            "found_at_start": True, **changes}


def agent(seq, **changes):
    return {"kind": "agent_state", "event_seq": seq, "observed_at": "2030-01-02T03:00:06Z", "subject": "rule_set",
            "state": "compiled", "code": None, "rule_set_id": "a" * 64, **changes}


def tamper(seq, **changes):
    return {"kind": "tamper_signal", "event_seq": seq, "observed_at": "2030-01-02T03:00:07Z",
            "signal": "service_config_changed", "detail": None, **changes}


def gap(seq, **changes):
    return {"kind": "coverage_gap", "event_seq": seq, "observed_at": "2030-01-02T03:00:08Z",
            "source": "file_change_sensor", "reason": "usn_journal_reset", "lost": None, **changes}


def every_kind(first):
    """One event of each of the nine kinds, in EVENT_KINDS order, from event_seq ``first``."""
    factories = (started, stopped, sensor, scan, behavior, persistence, agent, tamper, gap)
    return [factory(first + index) for index, factory in enumerate(factories)]


def body(sequence, items, *, schema_version=2, batch_id=None, **changes):
    return {"schema_version": schema_version, "batch_id": batch_id or str(uuid4()), "batch_sequence": sequence,
            "events": items, **changes}


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


@pytest.fixture
def alert_calls(monkeypatch):
    """Replace events.raise_alerts; record the events of every call (see the module docstring)."""
    calls = []

    def record(session, device, batch_events, *, received_at, previous_event_seq, limits):
        calls.append({"events": [event.model_dump(mode="json") for event in batch_events],
                      "previous_event_seq": previous_event_seq})
        return 0

    monkeypatch.setattr(events, "raise_alerts", record)
    return calls


def timeline(ctx, device):
    response = ctx["client"].get(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}/events",
                                 headers=auth(ctx["token"]()))
    assert response.status_code == 200, response.text
    return response.json()


def device_view(ctx, device):
    response = ctx["client"].get(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}",
                                 headers=auth(ctx["token"]()))
    assert response.status_code == 200, response.text
    return response.json()


# --- the schema at head and migration 0005

def check_values(connection, table, name):
    definition = connection.scalar(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name "
        "AND conrelid = CAST(:table AS regclass)"), {"name": name, "table": "public." + table})
    return tuple(re.findall(r"'(\w+)'", definition))


def schema_state(connection):
    """Constraints, columns and indexes of the tables migration 0005 changes; None for an absent table."""
    state = {}
    for table in STAGE3_TABLES:
        if not connection.scalar(text("SELECT to_regclass(:table) IS NOT NULL"), {"table": "public." + table}):
            state[table] = None
            continue
        constraints = dict(connection.execute(text(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = CAST(:table AS regclass)"),
            {"table": "public." + table}).all())
        columns = {row[0]: tuple(row[1:]) for row in connection.execute(text(
            "SELECT column_name, data_type, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = :table"), {"table": table})}
        indexes = dict(connection.execute(text(
            "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = 'public' AND tablename = :table"),
            {"table": table}).all())
        state[table] = (constraints, columns, indexes)
    return state


def model_check(model, name):
    [check] = [item for item in model.__table__.constraints if isinstance(item, CheckConstraint) and item.name == name]
    return str(check.sqltext)


def statement_with(statements, marker):
    [statement] = [item for item in statements if marker in item]
    return " ".join(statement.split())


def migration_source_list(name, constraint):
    source = (PROJECT / "migrations/versions" / (name + ".py")).read_text(encoding="utf-8")
    [values] = re.findall(constraint + r" CHECK \(\w+ IN \(([^)]*)\)\)", source)
    return tuple(re.findall(r"'(\w+)'", values))


def test_the_alembic_head_is_0006_on_a_linear_chain(pg_service_databases):
    owner, _ = pg_service_databases
    script = ScriptDirectory.from_config(Config(str(PROJECT / "alembic.ini")))
    assert script.get_heads() == [HEAD]
    assert script.get_revision(HEAD).down_revision == STAGE3
    assert script.get_revision(STAGE3).down_revision == "0004_edr_agent_product"
    with owner.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == HEAD


def test_head_checks_match_the_contract_the_models_and_the_frozen_migrations(pg_service_databases):
    owner, _ = pg_service_databases
    with owner.engine.connect() as connection:
        kinds = check_values(connection, "endpoint_events", "ck_endpoint_event_kind")
        rules = check_values(connection, "alerts", "ck_alert_rule")
    # The single sources: event_contracts.EVENT_KINDS and the brief's ten rules (ALERT_RULES above).
    assert kinds == EVENT_KINDS
    assert rules == ALERT_RULES
    assert tuple(re.findall(r"'(\w+)'", model_check(EndpointEvent, "ck_endpoint_event_kind"))) == EVENT_KINDS
    assert tuple(re.findall(r"'(\w+)'", model_check(Alert, "ck_alert_rule"))) == ALERT_RULES
    # The migration hardcodes the same lists (a migration never imports application constants); its downgrade
    # restores exactly the lists that 0002 and 0003 wrote.
    module = migration_module(STAGE3)
    assert tuple(re.findall(r"'(\w+)'", statement_with(module.DDL_STATEMENTS, "ADD CONSTRAINT ck_endpoint_event_kind"))
                 ) == EVENT_KINDS
    assert tuple(re.findall(r"'(\w+)'", statement_with(module.DDL_STATEMENTS, "ADD CONSTRAINT ck_alert_rule"))
                 ) == ALERT_RULES
    v1_kinds = migration_source_list("0002_endpoint_events", "ck_endpoint_event_kind")
    old_rules = migration_source_list("0003_alerts", "ck_alert_rule")
    assert (v1_kinds, old_rules) == (EVENT_KINDS_V1, V1_RULES)
    assert tuple(re.findall(r"'(\w+)'", statement_with(module.DOWNGRADE_STATEMENTS,
                                                       "ADD CONSTRAINT ck_endpoint_event_kind"))) == v1_kinds
    assert tuple(re.findall(r"'(\w+)'", statement_with(module.DOWNGRADE_STATEMENTS, "ADD CONSTRAINT ck_alert_rule"))
                 ) == old_rules
    # The downgrade's deletions keep exactly what the narrower CHECKs accept.
    assert tuple(re.findall(r"'(\w+)'", statement_with(module.DOWNGRADE_STATEMENTS, "DELETE FROM endpoint_events"))
                 ) == v1_kinds
    assert tuple(re.findall(r"'(\w+)'", statement_with(module.DOWNGRADE_STATEMENTS, "DELETE FROM alerts"))) == old_rules
    # The sequence CHECK and both indexes are written alike in the model and the migration.
    assert statement_with(module.DDL_STATEMENTS, "ADD CONSTRAINT ck_alert_event_seq").endswith(
        "CHECK (" + " ".join(model_check(Alert, "ck_alert_event_seq").split()) + ")")
    for table, name in ((EndpointEvent, "ix_endpoint_events_process_identity"), (Alert, "ix_alert_silence_episode")):
        [index] = [item for item in table.__table__.indexes if item.name == name]
        compiled = " ".join(str(CreateIndex(index).compile(dialect=postgresql.dialect())).split())
        assert compiled == statement_with(module.DDL_STATEMENTS, "CREATE INDEX " + name)


def test_head_columns_and_indexes(pg_service_databases):
    owner, _ = pg_service_databases
    with owner.engine.connect() as connection:
        state = schema_state(connection)
    _, alert_columns, alert_indexes = state["alerts"]
    _, _, event_indexes = state["endpoint_events"]
    assert alert_columns["first_event_seq"][:2] == alert_columns["last_event_seq"][:2] == ("bigint", "YES")
    assert (Alert.__table__.c.first_event_seq.nullable, Alert.__table__.c.last_event_seq.nullable) == (True, True)
    assert event_indexes["ix_endpoint_events_process_identity"] == (
        "CREATE INDEX ix_endpoint_events_process_identity ON public.endpoint_events USING btree "
        "(tenant_id, device_id, ((payload ->> 'pid'::text)), ((payload ->> 'create_time'::text))) "
        "WHERE (((kind)::text = 'process_started'::text) AND (payload ? 'create_time'::text))")
    # Not unique: an episode key may hold a closed and a later alert; services/sweep.py (RULES) looks for any.
    assert alert_indexes["ix_alert_silence_episode"] == (
        "CREATE INDEX ix_alert_silence_episode ON public.alerts USING btree (tenant_id, device_id, dedup_key) "
        "WHERE (rule = 'agent_silent'::text)")


def insert_event(connection, tenant, device, seq, kind, payload=None):
    connection.execute(text(
        "INSERT INTO endpoint_events (tenant_id, device_id, event_seq, kind, observed_at, received_at, payload) "
        "VALUES (:tenant, :device, :seq, :kind, :at, :at, CAST(:payload AS jsonb))"),
        {"tenant": tenant, "device": device, "seq": seq, "kind": kind, "at": NOW,
         "payload": json.dumps(payload if payload is not None else {"kind": kind, "event_seq": seq})})


def insert_cursor(connection, tenant, device, *, stored_events, last_event_seq):
    connection.execute(text(
        "INSERT INTO device_event_cursors (tenant_id, device_id, last_batch_sequence, last_batch_id, "
        "last_batch_digest, last_event_seq, last_received_at, stored_events, cap_deleted_events, suppressed_alerts) "
        "VALUES (:tenant, :device, 1, :batch, :digest, :last, :at, :stored, 0, 0)"),
        {"tenant": tenant, "device": device, "batch": uuid4(), "digest": "a" * 64, "last": last_event_seq, "at": NOW,
         "stored": stored_events})


def insert_alert(connection, tenant, device, rule, first=1, last=1):
    connection.execute(text(
        "INSERT INTO alerts (id, tenant_id, device_id, rule, severity, dedup_key, status, occurrences, "
        "first_event_seq, last_event_seq, first_seen_at, last_seen_at, evidence, created_at, updated_at) "
        "VALUES (:id, :tenant, :device, :rule, 'medium', :key, 'open', 1, :first, :last, :at, :at, "
        "CAST('{}' AS jsonb), :at, :at)"),
        {"id": uuid4(), "tenant": tenant, "device": device, "rule": rule,
         "key": hashlib.sha256(str(uuid4()).encode()).hexdigest(), "first": first, "last": last, "at": NOW})


def device_kinds(connection, device):
    return connection.scalars(text("SELECT kind FROM endpoint_events WHERE device_id = :device ORDER BY event_seq"),
                              {"device": device}).all()


def device_rules(connection, device):
    return sorted(connection.scalars(text("SELECT rule FROM alerts WHERE device_id = :device"),
                                     {"device": device}).all())


def stored_counts(connection, devices):
    return {device: connection.scalar(text("SELECT stored_events FROM device_event_cursors WHERE device_id = :device"),
                                      {"device": device}) for device in devices}


def test_migration_0005_down_and_up_in_a_rolled_back_transaction(event_tenants):
    """Downgrade deletes only what the narrower CHECKs refuse and restores 0002/0003's schema exactly; the
    upgrade gives the head schema again."""
    ctx = event_tenants
    full, old_only, new_only = (UUID(enrolled(ctx.runtime, ctx.admin_a, ctx.a)["device_id"]) for _ in range(3))
    module = migration_module(STAGE3)
    assert (module.revision, module.down_revision) == (STAGE3, "0004_edr_agent_product")
    # 0006 adds ix_alert_tenant_closed after 0005: it is downgraded first and upgraded last.
    retention = migration_module(HEAD)
    assert retention.down_revision == STAGE3
    endpoint_events, alerts_migration = migration_module("0002_endpoint_events"), migration_module("0003_alerts")
    v2_started = parse_event_batch(body(1, [started(1)])).events[0].model_dump(mode="json")
    with ctx.owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            head = schema_state(connection)
            for seq, kind in enumerate(EVENT_KINDS, start=1):
                insert_event(connection, ctx.a, full, seq, kind, v2_started if kind == "process_started" else None)
            for seq, kind in enumerate(EVENT_KINDS_V1, start=1):
                insert_event(connection, ctx.a, old_only, seq, kind)
            insert_event(connection, ctx.a, new_only, 1, "scan_detected")
            insert_event(connection, ctx.a, new_only, 2, "coverage_gap")
            insert_cursor(connection, ctx.a, full, stored_events=9, last_event_seq=9)
            insert_cursor(connection, ctx.a, old_only, stored_events=3, last_event_seq=3)
            # A count below the device's rows (as after a cap race) is lowered to 0, never below.
            insert_cursor(connection, ctx.a, new_only, stored_events=1, last_event_seq=2)
            for rule in ALERT_RULES:
                insert_alert(connection, ctx.a, full, rule, *((None, None) if rule == "agent_silent" else (1, 2)))
            for rule in V1_RULES:
                insert_alert(connection, ctx.a, old_only, rule)
            with Operations.context(MigrationContext.configure(connection)):
                retention.downgrade()
                at_0005 = schema_state(connection)
                module.downgrade()
                assert device_kinds(connection, full) == device_kinds(connection, old_only) == list(EVENT_KINDS_V1)
                assert device_kinds(connection, new_only) == []
                # A v2-shaped event of a v1 kind stays: the v1 CHECK accepts it.
                assert connection.scalar(text("SELECT payload FROM endpoint_events WHERE device_id = :device "
                                              "AND event_seq = 1"), {"device": full}) == v2_started
                assert stored_counts(connection, (full, old_only, new_only)) == {full: 3, old_only: 3, new_only: 0}
                assert device_rules(connection, full) == device_rules(connection, old_only) == sorted(V1_RULES)
                at_0004 = schema_state(connection)
                assert at_0004 != head
                # The Stage 2 CHECKs and NOT NULL are back.
                for refused in (lambda: insert_event(connection, ctx.a, old_only, 10, "scan_detected"),
                                lambda: insert_alert(connection, ctx.a, old_only, "scan_detection"),
                                lambda: insert_alert(connection, ctx.a, old_only, "agent_silent", None, None),
                                lambda: insert_alert(connection, ctx.a, old_only, "event_loss", None, None)):
                    with pytest.raises(IntegrityError):
                        with connection.begin_nested():
                            refused()
                # 0002 and 0003 run again from their own DDL and build exactly this schema.
                alerts_migration.downgrade()
                endpoint_events.downgrade()
                assert schema_state(connection) == {table: None for table in STAGE3_TABLES}
                endpoint_events.upgrade()
                alerts_migration.upgrade()
                assert schema_state(connection) == at_0004
                module.upgrade()
                assert schema_state(connection) == at_0005
                retention.upgrade()
                assert schema_state(connection) == head
        finally:
            transaction.rollback()
    with ctx.owner.engine.connect() as connection:
        assert schema_state(connection) == head


def normalized(statements):
    return [" ".join(statement.split()) for statement in statements]


def offline_sql(run):
    """The statements that a migration step emits in alembic's offline (--sql) mode, in order."""
    buffer = io.StringIO()
    with Operations.context(MigrationContext.configure(dialect_name="postgresql",
                                                       opts={"as_sql": True, "output_buffer": buffer})):
        run()
    return normalized(item for item in buffer.getvalue().split(";\n\n") if item.strip())


def test_migration_0005_lifts_the_statement_timeout_around_its_own_statements_only():
    # env.py bounds every statement of the one migration transaction at 5 s. 0005's CHECK validation, index build
    # and downgrade deletion read the event table whole, so each direction lifts statement_timeout before its first
    # statement and restores env.py's value after its last; lock_timeout is never touched.
    module = migration_module(STAGE3)
    assert (module.LIFT_STATEMENT_TIMEOUT, module.RESTORE_STATEMENT_TIMEOUT) == (
        "SET LOCAL statement_timeout = 0", "SET LOCAL statement_timeout TO DEFAULT")
    for run, statements in ((module.upgrade, module.DDL_STATEMENTS), (module.downgrade, module.DOWNGRADE_STATEMENTS)):
        emitted = offline_sql(run)
        assert emitted == [module.LIFT_STATEMENT_TIMEOUT, *normalized(statements), module.RESTORE_STATEMENT_TIMEOUT]
        assert not [statement for statement in emitted if "lock_timeout" in statement]


def settings_per_statement(connection, run):
    """(statement, statement_timeout, lock_timeout) in effect for each statement that ``run`` sends on
    ``connection``, read on the same session and transaction just before the statement runs."""
    seen = []

    def before(conn, cursor, statement, parameters, context, executemany):
        probe = cursor.connection.cursor()
        try:
            probe.execute("SELECT current_setting('statement_timeout'), current_setting('lock_timeout')")
            seen.append((" ".join(statement.split()), *probe.fetchone()))
        finally:
            probe.close()

    event.listen(connection, "before_cursor_execute", before)
    try:
        run()
    finally:
        event.remove(connection, "before_cursor_execute", before)
    return seen


def timeouts(connection):
    return (connection.scalar(text("SHOW statement_timeout")), connection.scalar(text("SHOW lock_timeout")))


def test_migration_0005_statements_run_unbounded_with_env_lock_timeout_then_env_timeouts_return(
        pg_service_databases):
    # On PostgreSQL itself: SET LOCAL reaches every 0005 statement, and TO DEFAULT gives back the value that the
    # connection's options set (env.py's and db.py's 5 s), so later migrations of the same run keep their bound.
    owner, _ = pg_service_databases
    module = migration_module(STAGE3)
    lift, restore = module.LIFT_STATEMENT_TIMEOUT, module.RESTORE_STATEMENT_TIMEOUT
    with owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            head = schema_state(connection)
            assert timeouts(connection) == ("5s", "3s")
            with Operations.context(MigrationContext.configure(connection)):
                for run, statements in ((module.downgrade, module.DOWNGRADE_STATEMENTS),
                                        (module.upgrade, module.DDL_STATEMENTS)):
                    assert settings_per_statement(connection, run) == [
                        (lift, "5s", "3s"), *((statement, "0", "3s") for statement in normalized(statements)),
                        (restore, "0", "3s")]
                    assert timeouts(connection) == ("5s", "3s")
            assert schema_state(connection) == head
        finally:
            transaction.rollback()


SEQUENCE_PAIRS = [(None, None), (None, 1), (1, None), (0, 0), (0, 1), (2, 1), (1, 1), (1, 2)]


@pytest.mark.parametrize("rule", ALERT_RULES)
def test_alert_sequences_are_null_exactly_for_agent_silent(event_tenants, rule):
    ctx = event_tenants
    device = UUID(enrolled(ctx.runtime, ctx.admin_a, ctx.a)["device_id"])
    with ctx.owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            for first, last in SEQUENCE_PAIRS:
                if rule == "agent_silent":
                    valid = (first, last) == (None, None)
                else:
                    valid = (first, last) in {(1, 1), (1, 2)}
                if valid:
                    with connection.begin_nested():
                        insert_alert(connection, ctx.a, device, rule, first, last)
                else:
                    # A CHECK whose result is null would pass: the rule tests nullness explicitly.
                    with pytest.raises(IntegrityError, match="ck_alert_event_seq"):
                        with connection.begin_nested():
                            insert_alert(connection, ctx.a, device, rule, first, last)
        finally:
            transaction.rollback()


def test_rule_and_kind_checks_accept_exactly_the_stage3_lists(event_tenants):
    ctx = event_tenants
    device = UUID(enrolled(ctx.runtime, ctx.admin_a, ctx.a)["device_id"])
    with ctx.owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            for rule in ALERT_RULES:
                with connection.begin_nested():
                    insert_alert(connection, ctx.a, device, rule, *((None, None) if rule == "agent_silent" else (1, 1)))
            for rule in ("network_beacon", "Agent_Silent", "", "scan_detected"):
                with pytest.raises(IntegrityError, match="ck_alert_rule"):
                    with connection.begin_nested():
                        insert_alert(connection, ctx.a, device, rule)
            for seq, kind in enumerate(EVENT_KINDS, start=1):
                with connection.begin_nested():
                    insert_event(connection, ctx.a, device, seq, kind)
            for kind in ("network_connection", "Scan_Detected", "", "scan_detection"):
                with pytest.raises(IntegrityError, match="ck_endpoint_event_kind"):
                    with connection.begin_nested():
                        insert_event(connection, ctx.a, device, 100, kind)
        finally:
            transaction.rollback()
    # The model maps the nullable columns: an agent_silent row is written through the ORM as well.
    with ctx.owner.session_factory() as session:
        session.add(Alert(tenant_id=ctx.a, device_id=device, rule="agent_silent", severity="medium",
                          dedup_key="c" * 64, status="open", occurrences=1, first_event_seq=None, last_event_seq=None,
                          first_seen_at=NOW, last_seen_at=NOW, evidence={"last_received_at": "2030-01-02T03:00:00Z"},
                          created_at=NOW, updated_at=NOW))
        session.flush()
        session.rollback()


def plan_text(connection, statement, parameters):
    return json.dumps(connection.execute(text("EXPLAIN (FORMAT JSON) " + statement), parameters).scalar())


def test_both_indexes_serve_their_lookups(event_tenants):
    ctx = event_tenants
    device = UUID(enrolled(ctx.runtime, ctx.admin_a, ctx.a)["device_id"])
    with ctx.owner.engine.connect() as connection:
        transaction = connection.begin()
        try:
            for seq in range(1, 41):
                insert_event(connection, ctx.a, device, seq, "process_started",
                             {"kind": "process_started", "pid": seq, "create_time": f"2030-01-02T02:00:{seq:02d}.000000Z"})
            insert_alert(connection, ctx.a, device, "agent_silent", None, None)
            connection.execute(text("ANALYZE endpoint_events"))
            connection.execute(text("ANALYZE alerts"))
            connection.execute(text("SET LOCAL enable_seqscan = off"))
            # The exact parent of a v2 child: (pid, create_time) as payload text, v2 process_started rows only.
            parent = plan_text(connection,
                "SELECT event_seq FROM endpoint_events WHERE tenant_id = :tenant AND device_id = :device "
                "AND kind = 'process_started' AND payload ? 'create_time' AND payload ->> 'pid' = :pid "
                "AND payload ->> 'create_time' = :created",
                {"tenant": ctx.a, "device": device, "pid": "7", "created": "2030-01-02T02:00:07.000000Z"})
            assert "ix_endpoint_events_process_identity" in parent
            silence = plan_text(connection,
                "SELECT id FROM alerts WHERE tenant_id = :tenant AND device_id = :device AND rule = 'agent_silent' "
                "AND dedup_key = :key", {"tenant": ctx.a, "device": device, "key": "a" * 64})
            assert "ix_alert_silence_episode" in silence
        finally:
            transaction.rollback()


# --- event v2 through the real API

def test_device_routes_take_the_versioned_unions(api_context):
    schema = api_context["app"].openapi()

    def body_refs(path, method):
        content = schema["paths"][path][method]["requestBody"]["content"]["application/json"]["schema"]
        return sorted(item["$ref"].rsplit("/", 1)[1] for item in content["oneOf"])

    assert body_refs(EVENTS, "post") == ["EventBatch", "EventBatchV2"]
    assert body_refs(SNAPSHOT, "put") == ["SnapshotEnvelope", "SnapshotEnvelopeV3"]


def test_a_v2_batch_of_every_kind_is_stored_shown_and_retried_exactly(pg_service_databases, api_context, alert_calls):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = {**auth(device["credential_secret"]), "Content-Type": "application/json"}
    message = body(1, every_kind(1))
    raw = compact(message)
    first = client.post(EVENTS, content=raw, headers=headers)
    assert first.status_code == 200, first.text
    ack = first.json()
    assert (ack["accepted"], ack["batch_id"], ack["batch_sequence"], ack["last_event_seq"]) == (
        True, message["batch_id"], 1, 9)
    model = parse_event_batch(message)
    assert type(model) is EventBatchV2
    dumps = [event.model_dump(mode="json") for event in model.events]
    assert alert_calls == [{"events": dumps, "previous_event_seq": None}]
    # The byte-identical resend and an equivalent representation get the stored acceptance and change nothing.
    assert client.post(EVENTS, content=raw, headers=headers).json() == ack
    equivalent = json.loads(raw)
    equivalent["events"] = [dict(reversed(list(item.items()))) for item in equivalent["events"]]
    equivalent["events"][0]["parent_create_time"] = "2030-01-02T02:00:00.0Z"
    equivalent["events"][8]["observed_at"] = "2030-01-02T03:00:08.000Z"
    del equivalent["events"][8]["lost"]
    assert client.post(EVENTS, json=equivalent, headers=auth(device["credential_secret"])).json() == ack
    assert len(alert_calls) == 1
    rows, cursor = stored(ctx["owner"], device)
    assert [(row.event_seq, row.kind) for row in rows] == list(enumerate(EVENT_KINDS, start=1))
    assert [row.payload for row in rows] == dumps
    assert (cursor.stored_events, cursor.last_event_seq, cursor.last_batch_digest) == (9, 9, event_batch_digest(model))
    items = timeline(ctx, device)["items"]
    assert [item["kind"] for item in items] == list(reversed(EVENT_KINDS))
    for item, dumped in zip(reversed(items), dumps):
        kind = item["kind"]
        assert set(item) == {"event_seq", "kind", "observed_at", "received_at", "source", "producer_verification",
                             *EVENT_VIEW_FIELDS[kind]}
        # The trust labels keep their meaning; coverage_gap's own source arrives as gap_source (EVENT_VIEW_FIELDS).
        assert (item["source"], item["producer_verification"]) == ("self_reported", "not_verified")
        assert {view: item[view] for view in EVENT_VIEW_FIELDS[kind]} == {
            view: dumped[name] for name, view in zip(EVENT_FIELDS[kind], EVENT_VIEW_FIELDS[kind])}
        # sha256 and size appear only in scan_detected.
        assert ("sha256" in item, "size" in item) == ((kind == "scan_detected"),) * 2


def device_alerts(ctx, device):
    response = ctx["client"].get(f"/api/v1/tenants/{ctx['a']}/alerts", params={"device_id": device["device_id"]},
                                 headers=auth(ctx["token"]()))
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_a_v2_batch_of_every_kind_runs_through_the_real_alert_rules(pg_service_databases, api_context):
    # Ingestion and the Stage 3 rules together, without the recording double: a v2 batch of all nine kinds is
    # accepted and stored, and opens exactly the alerts its events match.
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    response = client.post(EVENTS, json=body(1, every_kind(1)), headers=auth(device["credential_secret"]))
    assert response.status_code == 200, response.text
    assert response.json()["last_event_seq"] == 9
    rows, cursor = stored(ctx["owner"], device)
    assert [(row.event_seq, row.kind) for row in rows] == list(enumerate(EVENT_KINDS, start=1))
    assert cursor.stored_events == 9
    # rule_set compiled and the coverage gap raise nothing; the device's first batch has no event loss.
    assert sorted((alert["rule"], alert["occurrences"], alert["first_event_seq"], alert["last_event_seq"])
                  for alert in device_alerts(ctx, device)) == [
        ("behavior_match", 1, 5, 5), ("persistence_added", 1, 6, 6), ("scan_detection", 1, 4, 4),
        ("sensor_unstable", 1, 3, 3), ("tamper_signal", 1, 8, 8), ("user_writable_launch", 1, 1, 1)]


def test_coverage_gap_source_is_shown_as_gap_source_beside_the_trust_label(pg_service_databases, api_context):
    # P1 brief, section 5 addendum: the wire field and the stored payload keep `source`; the timeline item shows the
    # agent's value as gap_source, and `source` there stays the trust label. coverage_gap raises no alert, so this
    # runs through the real ingestion and alert path.
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    gaps = [gap(seq, source=value) for seq, value in enumerate(COVERAGE_SOURCES, start=1)]
    response = client.post(EVENTS, json=body(1, gaps), headers=auth(device["credential_secret"]))
    assert response.status_code == 200, response.text
    rows, _ = stored(ctx["owner"], device)
    assert [row.payload["source"] for row in rows] == list(COVERAGE_SOURCES)
    assert not any("gap_source" in row.payload for row in rows)
    items = timeline(ctx, device)["items"]
    assert [item["gap_source"] for item in reversed(items)] == list(COVERAGE_SOURCES)
    for item in items:
        assert set(item) == {"event_seq", "kind", "observed_at", "received_at", "source", "producer_verification",
                             "gap_source", "reason", "lost"}
        assert (item["source"], item["producer_verification"]) == ("self_reported", "not_verified")
    assert device_alerts(ctx, device) == []


def test_v2_shapes_of_the_v1_kinds_use_the_real_alert_path(pg_service_databases, api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    assert client.post(EVENTS, json=body(1, [v1_started(1)], schema_version=1), headers=headers).status_code == 200
    second = client.post(EVENTS, json=body(2, [started(2), stopped(3), sensor(4)]), headers=headers)
    assert second.status_code == 200, second.text
    alerts = client.get(f"/api/v1/tenants/{ctx['a']}/alerts", params={"device_id": device["device_id"]},
                        headers=auth(ctx["token"]())).json()["items"]
    # The same launch image in v1 and v2 is one alert of two occurrences; the v2 lost sensor is sensor_unstable.
    assert sorted((alert["rule"], alert["occurrences"], alert["first_event_seq"], alert["last_event_seq"])
                  for alert in alerts) == [("sensor_unstable", 1, 4, 4), ("user_writable_launch", 2, 1, 2)]
    by_seq = {item["event_seq"]: item for item in timeline(ctx, device)["items"]}
    # A v1 row shows null for the fields that exist only in v2.
    assert (by_seq[1]["create_time"], by_seq[1]["parent_create_time"]) == (None, None)
    assert (by_seq[2]["create_time"], by_seq[2]["parent_create_time"]) == (CREATED, "2030-01-02T02:00:00.000000Z")
    assert by_seq[3]["create_time"] == CREATED and by_seq[4]["error_code"] == "session_in_use"


def test_v1_and_v2_batches_interleave_on_one_cursor(pg_service_databases, api_context, alert_calls):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    first = body(1, [v1_started(1), sensor(2)], schema_version=1)
    second = body(2, [scan(3), gap(4), started(5)])
    for message, last in ((first, 2), (second, 5)):
        response = client.post(EVENTS, json=message, headers=headers)
        assert response.status_code == 200 and response.json()["last_event_seq"] == last, response.text
    identity = "Event batch identity or sequence conflicts with current state"
    for conflicting, detail in (
            # The same identity resent as v1 (schema_version is part of the digest) is new content.
            ({**second, "schema_version": 1, "events": [v1_started(3), sensor(4), v1_started(5)]}, identity),
            (body(2, [scan(6)]), identity), ({**second, "batch_sequence": 3, "events": [gap(6)]}, identity),
            (body(1, [gap(6)]), "Event batch sequence is stale"),
            (body(3, [gap(5)]), "Event sequence does not follow the last accepted event"),
            (body(3, [v1_stopped(5)], schema_version=1), "Event sequence does not follow the last accepted event")):
        response = client.post(EVENTS, json=conflicting, headers=headers)
        assert response.status_code == 409, response.text
        assert response.json() == {"detail": detail, "last_batch_sequence": 2, "last_event_seq": 5}
    third = body(3, [v1_stopped(6)], schema_version=1)
    accepted = client.post(EVENTS, json=third, headers=headers)
    assert accepted.status_code == 200 and accepted.json()["last_event_seq"] == 6
    assert client.post(EVENTS, json=third, headers=headers).json() == accepted.json()
    stale = client.post(EVENTS, json=second, headers=headers)
    assert stale.status_code == 409 and stale.json()["detail"] == "Event batch sequence is stale"
    # Each accepted batch reached the alert step once, with the cursor's previous position.
    assert [([event["event_seq"] for event in call["events"]], call["previous_event_seq"]) for call in alert_calls] == [
        ([1, 2], None), ([3, 4, 5], 2), ([6], 5)]
    items = timeline(ctx, device)["items"]
    assert [(item["event_seq"], item["kind"]) for item in items] == [
        (6, "process_stopped"), (5, "process_started"), (4, "coverage_gap"), (3, "scan_detected"),
        (2, "sensor_state"), (1, "process_started")]
    assert items[0]["create_time"] is None and items[5]["create_time"] is None and items[1]["create_time"] == CREATED
    rows, cursor = stored(ctx["owner"], device)
    assert len(rows) == cursor.stored_events == 6 and cursor.last_batch_sequence == 3


def test_invalid_v2_bodies_are_422_without_echo_write_or_alert_step(pg_service_databases, api_context, alert_calls):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    no_version = body(1, [scan(1)])
    del no_version["schema_version"]
    malformed = [
        body(1, [scan(1)], schema_version=True), body(1, [scan(1)], schema_version="2"),
        body(1, [scan(1)], schema_version=2.0), body(1, [scan(1)], schema_version=3),
        body(1, [scan(1)], schema_version=None), no_version,
        # Homogeneity: a v2 kind or a v2 shape in a v1 batch, the v1 process_started shape in a v2 batch.
        body(1, [scan(1)], schema_version=1), body(1, [started(1)], schema_version=1), body(1, [v1_started(1)]),
        # Privacy and identity.
        body(1, [scan(1, command_line=CANARY)]), body(1, [behavior(1, user=CANARY)]),
        body(1, [persistence(1, sid=CANARY)]), body(1, [agent(1, username=CANARY)]),
        body(1, [tamper(1, content=CANARY)]), body(1, [behavior(1, sha256="a" * 64)]), body(1, [gap(1, size=1)]),
        body(1, [scan(1, device_id=device["device_id"])]), body(1, [scan(1)], tenant_id=str(ctx["b"])),
        body(1, [scan(1, path="\\Device\\HarddiskVolume3\\Users\\" + CANARY + "\\a.exe")]),
        body(1, [scan(1, hits=[{"rule": "Sample_Rule", "severity": "low", "description": CANARY}])]),
        # Closed values and cross-field rules.
        body(1, [behavior(1, rule=CANARY)]), body(1, [scan(1, sha256=CANARY)]),
        body(1, [agent(1, subject="isolation", state="compiled", rule_set_id=None)]),
        body(1, [tamper(1, signal="event_log_cleared", detail=None)]),
        body(1, [started(1, create_time="1601-01-01T00:00:00Z")]), body(1, [scan(2), gap(1)]),
    ]
    for payload in malformed:
        response = client.post(EVENTS, json=payload, headers=headers)
        assert response.status_code == 422, (payload, response.text)
        assert response.json() == {"detail": "invalid_request"} and CANARY not in response.text
    assert timeline(ctx, device)["items"] == [] and alert_calls == []
    assert stored(ctx["owner"], device) == ([], None)
    accepted = client.post(EVENTS, json=body(1, [scan(1)]), headers=headers)
    assert accepted.status_code == 200 and accepted.json()["batch_sequence"] == 1


def test_v2_batch_limits(pg_service_databases, api_context, alert_calls):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = {**auth(device["credential_secret"]), "Content-Type": "application/json"}
    # Within 16 KiB as sent, above it in canonical form (explicit null, microsecond times): 413 after validation.
    gaps = [{"kind": "coverage_gap", "event_seq": seq, "observed_at": "2030-01-02T03:00:00Z",
             "source": "process_sensor", "reason": "etw_events_lost"} for seq in range(1, 121)]
    payload = body(1, gaps)
    encoded = compact(payload)
    assert len(encoded) <= 16384
    with pytest.raises(EventBatchTooLarge, match="event_batch_too_large"):
        canonical_event_batch(parse_event_batch(payload))
    response = client.post(EVENTS, content=encoded, headers=headers)
    assert response.status_code == 413 and response.json() == {"detail": "Event batch too large"}
    # Above 16 KiB as sent: the request boundary refuses it before validation.
    oversized = compact(body(1, [scan(seq, path="\\" + "a" * 1000) for seq in range(1, 18)]))
    assert len(oversized) > 16384
    response = client.post(EVENTS, content=oversized, headers=headers)
    assert response.status_code == 413 and response.json() == {"detail": "request_too_large"}
    assert timeline(ctx, device)["items"] == [] and alert_calls == []
    assert client.post(EVENTS, content=compact(body(1, gaps[:10])), headers=headers).json()["batch_sequence"] == 1


def test_services_take_parsed_models_of_every_version(event_tenants, alert_calls):
    ctx = event_tenants
    device = enrolled(ctx.runtime, ctx.admin_a, ctx.a)

    def ingest(message):
        with ctx.runtime.session() as session:
            principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
            return events.ingest_events(session, principal, message, now=NOW)

    v1 = EventBatch.model_validate(body(1, [v1_started(1)], schema_version=1))
    v2 = EventBatchV2.model_validate(body(2, [agent(2), tamper(3)]))
    assert ingest(v1)["last_event_seq"] == 1 and ingest(v2)["last_event_seq"] == 3
    assert ingest(v2) == ingest(v2.model_dump(mode="json"))
    assert [row.kind for row in stored(ctx.owner, device)[0]] == ["process_started", "agent_state", "tamper_signal"]
    message = SnapshotEnvelopeV3.model_validate(v3_body(1, products=v1_products() + [agent_v3()]))
    with ctx.runtime.session() as session:
        principal = enrollment.authenticate_device(session, device["credential_secret"], now=NOW)
        accepted = snapshots.ingest_snapshot(session, principal, message, now=NOW)
    assert (accepted["sequence"], accepted["message_id"]) == (1, message.message_id)


# --- Snapshot V3 through the real API

def v1_products():
    return [{"product_id": "hostbasedfirewall", "status": "running", "firewall_mode": "enforce"},
            {"product_id": "termivar", "status": "experimental", "report_presence": "none"},
            {"product_id": "antivirus", "status": "planned", "availability": "unavailable"}]


def v2_agent(**changes):
    status = {"product_id": "edr_agent", "status": "running", "version": "0.3.0",
              "source_observed_at": "2030-01-02T03:00:00Z", "agent_started_at": "2030-01-02T01:00:00Z",
              "engine_id": "edr-agent/0.3.0", "rule_file_present": True, "sensor_state": "started"}
    status.update(changes)
    return status


def agent_v3(**changes):
    status = {"product_id": "edr_agent", "status": "running", "version": "0.4.0",
              "source_observed_at": "2030-01-02T03:00:00Z", "agent_started_at": "2030-01-02T01:00:00Z",
              "engine_id": "edr-agent/0.4.0", "sensor_state": "started", "rule_set_state": "compiled",
              "rule_set_id": "c" * 64, "realtime_scan_state": "running", "file_change_sensor_state": "not_available",
              "command_line_sensor_state": "degraded", "persistence_watch_state": "running", "scans_completed": 12,
              "scans_detected": 1, "etw_events_lost": None, "response_channel_state": "awaiting_tenant_binding",
              "response_actions_enabled": [], "response_key_ids": [], "isolation_state": "inactive",
              "isolation_checked_at": "2030-01-02T02:59:00Z", "service_config_state": "as_installed",
              "previous_run_end": "clean", "heartbeat_interval_seconds": 60,
              "behavior_rules_version": "altay-behavior/v1"}
    status.update(changes)
    return status


def v3_body(sequence, *, schema_version=3, products=None, message_id=None, **changes):
    return {"schema_version": schema_version, "message_id": message_id or str(uuid4()), "sequence": sequence,
            "source_observed_at": "2030-01-02T03:00:00Z",
            "products": [agent_v3()] if products is None else products, **changes}


def agent_state(ctx, device):
    [state] = [item["state"] for item in device_view(ctx, device)["products"] if item["product_id"] == "edr_agent"]
    return state


def test_v3_snapshot_detail_retry_conflicts_and_replacement_over_http(pg_service_databases, api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    headers = auth(device["credential_secret"])
    message = v3_body(1, products=v1_products() + [agent_v3()])
    raw = compact(message)
    first = client.put(SNAPSHOT, content=raw, headers={**headers, "Content-Type": "application/json"})
    assert first.status_code == 200, first.text
    assert set(first.json()) == {"accepted", "message_id", "sequence", "received_at"}
    again = client.put(SNAPSHOT, content=raw, headers={**headers, "Content-Type": "application/json"})
    assert again.status_code == 200 and again.json() == first.json()
    view = device_view(ctx, device)
    assert view["missing_products"] == [] and view["last_sequence"] == 1
    assert [product["product_id"] for product in view["products"]] == sorted(PRODUCT_IDS)
    state = agent_state(ctx, device)
    # The stored payload is the V3 dump; the console tells V3 from V2 by its key set.
    assert state == SnapshotEnvelopeV3.model_validate(message).products[3].model_dump(mode="json")
    assert "rule_set_state" in state and "rule_file_present" not in state
    assert (state["source"], state["producer_verification"]) == ("self_reported", "not_verified")
    identity = "Snapshot identity or sequence conflicts with current state"
    for conflicting in ({**message, "schema_version": 2, "products": v1_products()},
                        v3_body(1, schema_version=2, products=[v2_agent()]), v3_body(1),
                        v3_body(2, message_id=message["message_id"])):
        response = client.put(SNAPSHOT, json=conflicting, headers=headers)
        assert response.status_code == 409 and response.json() == {"detail": identity}, response.text
    # Every version is a whole state: a later snapshot of either version replaces every product.
    second = client.put(SNAPSHOT, json=v3_body(2, schema_version=2, products=[v2_agent()]), headers=headers)
    assert second.status_code == 200, second.text
    assert device_view(ctx, device)["missing_products"] == ["antivirus", "hostbasedfirewall", "termivar"]
    state = agent_state(ctx, device)
    assert "rule_file_present" in state and "rule_set_state" not in state
    stale = client.put(SNAPSHOT, json=v3_body(1), headers=headers)
    assert stale.status_code == 409 and stale.json() == {"detail": "Snapshot sequence is stale"}
    assert client.put(SNAPSHOT, json=v3_body(3, products=v1_products()), headers=headers).status_code == 200
    assert device_view(ctx, device)["missing_products"] == ["edr_agent"]
    fourth = v3_body(4, products=[agent_v3(rule_set_state="missing", rule_set_id=None)])
    assert client.put(SNAPSHOT, json=fourth, headers=headers).status_code == 200
    state = agent_state(ctx, device)
    assert state["rule_set_state"] == "missing" and "rule_file_present" not in state
    with ctx["owner"].session() as session:
        digest = session.scalar(text("SELECT last_content_digest FROM devices WHERE id = :id"),
                                {"id": UUID(device["device_id"])})
    assert digest == snapshot_digest(SnapshotEnvelopeV3.model_validate(fourth))
    listing = client.get(f"/api/v1/tenants/{ctx['a']}/devices", headers=auth(ctx["token"]())).json()["items"]
    assert [row["last_sequence"] for row in listing if row["id"] == device["device_id"]] == [4]


INVALID_V3 = {
    "v2_agent_shape": v3_body(1, products=[v2_agent()]),
    "rule_file_present": v3_body(1, products=[agent_v3(rule_file_present=True)]),
    "catalog_claim": v3_body(1, products=[agent_v3(catalog_available=False)]),
    "protection_active": v3_body(1, products=[agent_v3(protection_active=True)]),
    "rules_loaded": v3_body(1, products=[agent_v3(rules_loaded=True)]),
    "realtime_protection": v3_body(1, products=[agent_v3(realtime_protection=True)]),
    "private_engine_id": v3_body(1, products=[agent_v3(engine_id="edr-agent/çanary-private")]),
    "actions_unsorted": v3_body(1, products=[agent_v3(response_actions_enabled=["scan_path", "isolate_host"])]),
    "five_key_ids": v3_body(1, products=[agent_v3(response_key_ids=["a" * 64] * 5)]),
    "isolation_until_out_of_range": v3_body(1, products=[agent_v3(isolation_until="9999-12-31T23:59:59Z")]),
    "heartbeat_below_30": v3_body(1, products=[agent_v3(heartbeat_interval_seconds=5)]),
    "behavior_rules_v0": v3_body(1, products=[agent_v3(behavior_rules_version="altay-behavior/v0")]),
    "code_while_started": v3_body(1, products=[agent_v3(sensor_state="started", sensor_error_code="access_denied")]),
    "agent_twice": v3_body(1, products=[agent_v3(), agent_v3()]),
    "version_text": v3_body(1, schema_version="3"), "version_float": v3_body(1, schema_version=3.0),
    "version_bool": v3_body(1, schema_version=True), "version_4": v3_body(1, schema_version=4),
    "command": v3_body(1, command=False), "desired_policy": v3_body(1, desired_policy={}),
    "execution_authorized": v3_body(1, execution_authorized=False),
    "sequence_above_2_53": v3_body(MAX_SNAPSHOT_SEQUENCE + 1),
    "envelope_time_out_of_range": v3_body(1, source_observed_at="9999-12-31T23:59:59Z"),
    "v3_agent_in_v2": v3_body(1, schema_version=2, products=[agent_v3()]),
}


@pytest.mark.parametrize("message", list(INVALID_V3.values()), ids=list(INVALID_V3))
def test_invalid_v3_bodies_are_422_without_echo_or_write(pg_service_databases, api_context, message):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    result = client.put(SNAPSHOT, json=message, headers=auth(device["credential_secret"]))
    assert result.status_code == 422 and result.json() == {"detail": "invalid_request"}
    assert "anary-private" not in result.text
    view = device_view(ctx, device)
    assert view["connection_status"] == "never_seen" and view["last_sequence"] is None and view["products"] == []


# Stage 2 bodies whose canonical bytes and digests tests/unit/test_snapshot_v2_contracts.py pins (the Stage 1 V1
# body and the reference V2 body), repeated here for the stored digest.
PINNED_STAGE2 = {
    "v1_stage1": ({"schema_version": 1, "message_id": "00000000-0000-4000-8000-000000000002", "sequence": 7,
                   "products": []},
                  b'{"message_id":"00000000-0000-4000-8000-000000000002","products":[],"schema_version":1,"sequence":7,'
                  b'"source_observed_at":null}',
                  "b517d12011cf681a111d88f320da0eaae1001b90cd40a5b6bf357c47b43c128c"),
    "v2_reference": ({"schema_version": 2, "message_id": "00000000-0000-4000-8000-000000000003", "sequence": 7,
                      "source_observed_at": "2026-11-24T10:00:00Z",
                      "products": [{"product_id": "edr_agent", "status": "running", "version": "0.3.0",
                                    "source_observed_at": "2026-11-24T10:00:00Z",
                                    "agent_started_at": "2026-11-24T08:00:00.5Z", "engine_id": "edr-agent/0.3.0",
                                    "rule_file_present": True, "sensor_state": "started", "sensor_error_code": None,
                                    "events_queue_dropped": 0, "events_write_failed": 1, "events_unmapped": 2,
                                    "events_skipped": 3, "events_evicted": 4, "events_discarded": 5,
                                    "events_degraded": 6, "outbox_backlog": 7}]},
                     b'{"message_id":"00000000-0000-4000-8000-000000000003","products":[{"agent_started_at":'
                     b'"2026-11-24T08:00:00.500000Z","catalog_available":null,"engine_id":"edr-agent/0.3.0",'
                     b'"events_degraded":6,"events_discarded":5,"events_evicted":4,"events_queue_dropped":0,'
                     b'"events_skipped":3,"events_unmapped":2,"events_write_failed":1,"outbox_backlog":7,'
                     b'"producer_verification":"not_verified","product_id":"edr_agent","rule_file_present":true,'
                     b'"sensor_error_code":null,"sensor_state":"started","source":"self_reported",'
                     b'"source_observed_at":"2026-11-24T10:00:00.000000Z","status":"running","version":"0.3.0"}],'
                     b'"schema_version":2,"sequence":7,"source_observed_at":"2026-11-24T10:00:00.000000Z"}',
                     "7ac17abca2ed25cb0933044178d1bcad1461451b9f38ad3e933e2b599f2be5ec"),
}


@pytest.mark.parametrize("message,canonical,digest", list(PINNED_STAGE2.values()), ids=list(PINNED_STAGE2))
def test_v1_and_v2_snapshot_digests_are_unchanged_when_stored(pg_service_databases, api_context, message, canonical,
                                                              digest):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    model = SnapshotEnvelope.model_validate(message)
    assert canonical_json(model) == canonical and snapshot_digest(model) == digest
    assert client.put(SNAPSHOT, json=message, headers=auth(device["credential_secret"])).status_code == 200
    with ctx["owner"].session() as session:
        stored_digest = session.scalar(text("SELECT last_content_digest FROM devices WHERE id = :id"),
                                       {"id": UUID(device["device_id"])})
    assert stored_digest == digest
