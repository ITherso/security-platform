"""Actual PostgreSQL transactions in freshly provisioned lab-only databases."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from uuid import uuid4

import psycopg
import pytest

from security_platform.connectors.hostbased_firewall.private_files import read_private_json, write_private_json
from security_platform.policy_contracts.fingerprints import canonical_bytes
from security_platform.policy_contracts.hbf_bridge import load_hbf_adapter
from security_platform.policy_contracts.models import PolicyBundle
from tools.policy_revision_lab.controller_store import ControllerStore
from tools.policy_revision_lab.models import AppendRequest, LabBinding, LabError

from pg_fixture import cleanup_created, private_root, provision, restart_owned_cluster

pytestmark = pytest.mark.integration
PROJECT = Path(__file__).resolve().parents[2]
_explicit_hbf = os.environ.get("SP_HBF_SOURCE")
HBF_ROOT = (Path(_explicit_hbf) if _explicit_hbf else next(
    (path for path in (PROJECT.parent / "HostBasedFirewall-main", PROJECT.parent / "HostBasedFirewall")
     if (path / "src/policy_engine.py").is_file()), PROJECT.parent / "HostBasedFirewall-main"))


@pytest.fixture(scope="module")
def adapter():
    result = load_hbf_adapter(HBF_ROOT)
    if result is None:
        pytest.skip("Explicit sibling HBF source fixture unavailable")
    return result


@pytest.fixture
def target(tmp_path):
    # No environmental DSN fallback. Missing owned fixture is an explicit skip,
    # not permission to connect to a production/application database.
    if not (PROJECT.parent / ".tooling/platform-test-env.json").is_file():
        pytest.skip("Owned portable PostgreSQL fixture unavailable")
    with private_root(tmp_path) as root:
        config = provision(root / "controller.json")
        try:
            yield config, root
        finally:
            cleanup_created(config)


def binding(**changes):
    return LabBinding.model_validate({"kind": "controller_draft", "tenant_id": str(uuid4()),
        "subject_id": str(uuid4()), **changes})


def bundle(action="ALLOW", zones=()):
    return PolicyBundle.model_validate({"schema_version": 1,
        "ordered_zones": [{"name": name, "cidrs": list(cidrs)} for name, cidrs in zones],
        "objects": {}, "policies": {"default_action": action, "policies": []}})


def request(head, *, content=None, operation=None, **changes):
    return AppendRequest.model_validate({"binding": head.binding, "operation_id": operation or str(uuid4()),
        "expected_lineage": head.lineage, "expected_revision": head.revision,
        "base_fingerprint": head.bundle_fingerprint, "bundle": content or bundle(), **changes})


def raw(config_path):
    config = read_private_json(config_path)
    return psycopg.connect(host=config["host"], port=config["port"], dbname=config["database_name"],
                           user=config["role"], password=config["connection_secret"], connect_timeout=5)


def store(target, adapter):
    return ControllerStore.init(target[0], binding(), adapter=adapter)


def test_explicit_init_open_restart_and_fixed_non_authority(target, adapter):
    config, _ = target
    identity = binding()
    with pytest.raises(LabError):
        ControllerStore.open(config, identity, adapter=adapter)
    created = ControllerStore.init(config, identity, adapter=adapter)
    head = created.read()
    assert head.revision == head.draft_revision == 0 and head.bundle is None
    assert head.staged_revision is None
    assert head.authority == "unbound" and head.operational_binding == "absent"
    assert head.controller_desired_revision is head.device_policy_revision is None
    assert not head.execution_authorized and head.verification == "not_performed"
    first = created.append(request(head, content=bundle("DENY")))
    reopened = ControllerStore.open(config, identity, adapter=adapter)
    assert reopened.read().lineage == head.lineage
    assert reopened.read().last_commit == first
    assert reopened.check().checked_entries == 1
    with pytest.raises(LabError, match="invalid_lab_area"):
        ControllerStore.init(config, identity, adapter=adapter)
    assert reopened.read().last_commit == first


def test_real_database_restart_keeps_lineage_head_and_exact_result(target, adapter):
    current = store(target, adapter)
    pending = request(current.read(), content=bundle("DENY"))
    committed = current.append(pending)
    restart_owned_cluster()  # real server stop/start; no physical power-loss claim
    reopened = ControllerStore.open(target[0], current.binding, adapter=adapter)
    assert reopened.read().last_commit == committed
    assert reopened.append(pending) == committed


@pytest.mark.parametrize("same_operation,same_content", [(False, False), (True, True), (True, False)])
def test_separate_connections_barrier_race(target, adapter, same_operation, same_content, monkeypatch):
    current = store(target, adapter)
    head = current.read()
    op = str(uuid4())
    requests = [request(head, operation=op, content=bundle("ALLOW")),
                request(head, operation=op if same_operation else str(uuid4()),
                        content=bundle("ALLOW" if same_content else "DENY"))]
    barrier, pids, mutex = threading.Barrier(2), set(), threading.Lock()
    original = ControllerStore._read

    def blocked(self, connection, *, write=False):
        if write:
            with mutex:
                pids.add(connection.info.backend_pid)
            barrier.wait(timeout=5)
        return original(self, connection, write=write)

    monkeypatch.setattr(ControllerStore, "_read", blocked)

    def attempt(value):
        try:
            return current.append(value)
        except LabError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, requests))
    assert len(pids) == 2
    successes = [item for item in outcomes if not isinstance(item, str)]
    if same_operation and same_content:
        assert len(successes) == 2 and successes[0] == successes[1]
    else:
        assert len(successes) == 1
        expected = "lab_operation_conflict" if same_operation else "lab_cas_conflict"
        assert expected in outcomes
    assert current.read().revision == 1
    with raw(target[0]) as connection:
        assert connection.execute("SELECT count(*) FROM lab.entries").fetchone()[0] == 1


def test_aba_same_content_new_operation_and_all_history_exact_retry(target, adapter):
    current = store(target, adapter)
    first_request = request(current.read(), content=bundle("ALLOW"))
    first = current.append(first_request)
    second = current.append(request(current.read(), content=bundle("DENY")))
    third = current.append(request(current.read(), content=bundle("ALLOW")))
    fourth = current.append(request(current.read(), content=bundle("ALLOW")))
    assert [item.draft_revision for item in (first, second, third, fourth)] == [1, 2, 3, 4]
    assert first.bundle_fingerprint == third.bundle_fingerprint == fourth.bundle_fingerprint
    assert second.bundle_fingerprint != third.bundle_fingerprint
    reopened = ControllerStore.open(target[0], current.binding, adapter=adapter)
    assert reopened.append(first_request) == first
    assert reopened.read().last_commit == fourth  # old retry is not presented as current head
    changed = first_request.model_copy(update={"bundle": bundle("DENY")})
    with pytest.raises(LabError, match="lab_operation_conflict"):
        reopened.append(changed)
    assert reopened.read().revision == 4


@pytest.mark.parametrize("field", ["lineage", "revision", "base", "tenant", "subject", "kind", "product", "scope"])
def test_wrong_preconditions_and_binding_are_side_effect_free(target, adapter, field):
    current = store(target, adapter)
    current.append(request(current.read()))
    head = current.read()
    data = request(head).model_dump(mode="json")
    if field == "lineage": data["expected_lineage"] = str(uuid4())
    elif field == "revision": data["expected_revision"], data["base_fingerprint"] = 0, None
    elif field == "base": data["base_fingerprint"] = "sp-hbf-bundle-v1:sha256:" + "0" * 64
    elif field == "tenant": data["binding"]["tenant_id"] = str(uuid4())
    elif field == "subject": data["binding"]["subject_id"] = str(uuid4())
    elif field == "kind": data["binding"]["kind"] = "endpoint_staged"
    elif field == "product": data["binding"]["product_id"] = "antivirus"
    else: data["binding"]["enforcement_scope"] = "native_enforcement"
    with pytest.raises(LabError):
        current.append(data)
    assert current.read() == head


@pytest.mark.parametrize("damage", ["missing_entry", "head", "payload", "fingerprint", "result", "operation", "constraint"])
def test_corrupt_persistent_state_fails_closed_without_repair(target, adapter, damage):
    current = store(target, adapter)
    current.append(request(current.read()))
    with raw(target[0]) as connection:
        if damage == "missing_entry": connection.execute("DELETE FROM lab.entries")
        elif damage == "head": connection.execute("UPDATE lab.stream SET head_revision=2")
        elif damage == "payload": connection.execute("UPDATE lab.entries SET request_json='{}'")
        elif damage == "fingerprint": connection.execute("UPDATE lab.entries SET bundle_fingerprint=%s", ("sp-hbf-bundle-v1:sha256:" + "0"*64,))
        elif damage == "result": connection.execute("UPDATE lab.entries SET result_json='{}'")
        elif damage == "operation": connection.execute("UPDATE lab.entries SET operation_id=%s", (uuid4(),))
        else: connection.execute("ALTER TABLE lab.entries DROP CONSTRAINT entries_operation_id_key")
    with pytest.raises(LabError):
        ControllerStore.open(target[0], current.binding, adapter=adapter)
    with pytest.raises(LabError):
        current.append(request(make_head_for_test(current, adapter)))


def make_head_for_test(current, adapter):
    from tools.policy_revision_lab.models import make_head
    return make_head(current.binding, str(uuid4()), 0, adapter)


@pytest.mark.parametrize("schema", ["public", "extra_schema", "lab"])
def test_init_refuses_unknown_or_dense_area_without_adoption(target, adapter, schema):
    # Bootstrap only for deliberately constructing forbidden foreign-area fixtures.
    from scripts import managed_postgres as owned
    config = read_private_json(target[0])
    fixture = owned._read_config()
    with owned._admin_connection(fixture, dbname=config["database_name"]) as connection:
        if schema == "extra_schema": connection.execute("CREATE SCHEMA extra_schema")
        connection.execute(f"CREATE TABLE {schema}.foreign_table (value integer)")
    with pytest.raises(LabError, match="invalid_lab_area"):
        ControllerStore.init(target[0], binding(), adapter=adapter)
    with raw(target[0]) as connection:
        assert not connection.execute("SELECT 1 FROM pg_tables WHERE schemaname='lab' AND tablename='stream'").fetchone()


@pytest.mark.parametrize("field,value", [
    ("host", "example.invalid"), ("database_name", "security_platform_test"),
    ("role", "sp_migration"), ("owner", "foreign"), ("cluster_dir", "C:/foreign"),
    ("connection_secret", "not-a-secret"), ("url", "postgresql://foreign.invalid/production"),
])
def test_foreign_target_rejected_before_connection(target, adapter, monkeypatch, field, value):
    config = read_private_json(target[0])
    config[field] = value
    write_private_json(target[0], config)
    called = []
    monkeypatch.setattr(psycopg, "connect", lambda *a, **kw: called.append(True))
    with pytest.raises(LabError, match="invalid_lab_target"):
        ControllerStore.open(target[0], binding(), adapter=adapter)
    assert called == []


def test_lab_role_cannot_connect_app_db_or_modify_marker(target, adapter):
    current = store(target, adapter)
    with raw(target[0]) as connection:
        assert connection.execute("SELECT NOT has_database_privilege(current_user,'security_platform_test','CONNECT')").fetchone()[0]
        assert connection.execute("SELECT NOT has_table_privilege(current_user,'lab_identity.area','UPDATE')").fetchone()[0]
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            connection.execute("UPDATE lab_identity.area SET marker='{}'")
    assert current.read().revision == 0


def test_order_is_preserved_and_equal_prefix_ambiguity_rejected(target, adapter):
    current = store(target, adapter)
    ordered = bundle(zones=(("NARROW", ("10.1.0.0/16",)), ("WIDE", ("10.0.0.0/8",))))
    current.append(request(current.read(), content=ordered))
    assert [zone.name for zone in current.read().bundle.ordered_zones] == ["NARROW", "WIDE"]
    ties = bundle(zones=(("A", ("10.0.0.0/8",)), ("B", ("10.0.0.0/8",))))
    reverse = ties.model_copy(update={"ordered_zones": tuple(reversed(ties.ordered_zones))})
    assert adapter.legacy_version(adapter.normalize(ties)) == adapter.legacy_version(adapter.normalize(reverse))
    before = current.read()
    with pytest.raises(LabError, match="invalid_lab_bundle"):
        current.append(request(before, content=ties))
    assert current.read() == before


def test_consistent_old_restore_cannot_claim_rollback_detection(target, adapter):
    current = store(target, adapter)
    current.append(request(current.read()))
    old = current.read()
    with raw(target[0]) as connection:
        saved = connection.execute("SELECT * FROM lab.stream").fetchone()
    current.append(request(old, content=bundle("DENY")))
    with raw(target[0]) as connection:
        connection.execute("DELETE FROM lab.entries WHERE revision>1")
        connection.execute("UPDATE lab.stream SET head_revision=%s,head_fingerprint=%s,head_digest=%s", (saved[5], saved[6], saved[7]))
    restored = ControllerStore.open(target[0], current.binding, adapter=adapter).read()
    assert restored == old and restored.rollback_protection == "not_established"


CHILD = r'''
from contextlib import contextmanager
import json,os,time
from pathlib import Path
from security_platform.policy_contracts.hbf_bridge import load_hbf_adapter
from tools.policy_revision_lab.controller_store import ControllerStore
data=json.loads(Path(os.environ['LAB_CHILD_INPUT']).read_text(encoding='utf-8'))
adapter=load_hbf_adapter(data['hbf_root'])
store=ControllerStore.open(data['config'],data['request']['binding'],adapter=adapter)
if data['phase']=='before_commit':
    original=ControllerStore._connection
    @contextmanager
    def paused(self):
        with original(self) as connection:
            yield connection
            Path(data['ready']).write_text('uncommitted',encoding='ascii')
            time.sleep(30)
    ControllerStore._connection=paused
store.append(data['request'])
os._exit(23)  # committed response is deliberately lost
'''


@pytest.mark.parametrize("phase", ["before_commit", "after_commit"])
def test_actual_writer_process_death_and_exact_retry(target, adapter, phase):
    current = store(target, adapter)
    before = current.read()
    pending = request(before, content=bundle("DENY"))
    config, root = target
    ready, input_file = root / "ready.txt", root / "child.json"
    write_private_json(input_file, {"config": str(config), "hbf_root": str(HBF_ROOT), "phase": phase,
        "ready": str(ready), "request": pending.model_dump(mode="json")})
    environment = {**os.environ, "LAB_CHILD_INPUT": str(input_file),
                   "PYTHONPATH": str(PROJECT / "src") + os.pathsep + str(PROJECT)}
    child = subprocess.Popen([sys.executable, "-c", CHILD], cwd=PROJECT, env=environment,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if phase == "before_commit":
            deadline = time.monotonic() + 10
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.02)
            assert ready.exists()
            child.kill()
        assert child.wait(timeout=10) != 0
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)
    reopened = ControllerStore.open(config, current.binding, adapter=adapter)
    if phase == "before_commit":
        assert reopened.read() == before
    else:
        assert reopened.read().revision == 1
    committed = reopened.append(pending)
    assert committed.draft_revision == 1
    assert reopened.append(pending) == committed
    assert reopened.read().revision == 1


def test_lock_wait_is_bounded_and_retry_uses_original_cas(target, adapter):
    current = store(target, adapter)
    pending = request(current.read())
    with raw(target[0]) as blocker:
        blocker.execute("SELECT * FROM lab.stream FOR UPDATE").fetchall()
        started = time.monotonic()
        with pytest.raises(LabError, match="lab_store_busy"):
            current.append(pending)
        assert time.monotonic() - started < 5
    assert current.append(pending).draft_revision == 1


@pytest.mark.parametrize("object_kind", ["trigger", "function", "rule", "rls"])
def test_unknown_program_objects_refuse_append_before_any_write(target, adapter, object_kind):
    current = store(target, adapter)
    before = current.read()
    with raw(target[0]) as connection:
        if object_kind in {"trigger", "function"}:
            connection.execute("CREATE FUNCTION lab.keep_old() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN OLD; END$$")
            if object_kind == "trigger":
                connection.execute("CREATE TRIGGER keep_old BEFORE UPDATE ON lab.stream FOR EACH ROW EXECUTE FUNCTION lab.keep_old()")
        elif object_kind == "rule":
            connection.execute("CREATE RULE keep_old AS ON UPDATE TO lab.stream DO INSTEAD NOTHING")
        else:
            connection.execute("ALTER TABLE lab.stream ENABLE ROW LEVEL SECURITY")
    with pytest.raises(LabError, match="invalid_lab_area"):
        current.append(request(before))
    with raw(target[0]) as connection:
        assert connection.execute("SELECT head_revision FROM lab.stream").fetchone()[0] == 0
        assert connection.execute("SELECT count(*) FROM lab.entries").fetchone()[0] == 0


def test_postwrite_recheck_rolls_back_if_database_suppresses_head_update(target, adapter, monkeypatch):
    current = store(target, adapter)
    before = current.read()
    original = ControllerStore._read
    fired = []

    def sabotage(self, connection, *, write=False):
        result = original(self, connection, write=write)
        if write and not fired:
            fired.append(True)
            # Controlled in-transaction DDL after the precheck reproduces the
            # peer-review finding without any production hook or fake DB.
            connection.execute("CREATE FUNCTION lab.keep_old() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN RETURN OLD; END$$")
            connection.execute("CREATE TRIGGER keep_old BEFORE UPDATE ON lab.stream FOR EACH ROW EXECUTE FUNCTION lab.keep_old()")
        return result

    monkeypatch.setattr(ControllerStore, "_read", sabotage)
    with pytest.raises(LabError):
        current.append(request(before))
    assert current.read() == before  # DDL, artifact and head all rolled back
    with raw(target[0]) as connection:
        assert connection.execute("SELECT count(*) FROM lab.entries").fetchone()[0] == 0


def test_old_history_and_valid_timestamp_edits_break_journal_chain(target, adapter):
    import json
    current = store(target, adapter)
    current.append(request(current.read()))
    current.append(request(current.read(), content=bundle("DENY")))
    with raw(target[0]) as connection:
        raw_result = connection.execute("SELECT result_json FROM lab.entries WHERE revision=1").fetchone()[0]
        result = json.loads(raw_result)
        result["committed_at"] = "2001-01-01T00:00:00.000000Z"
        connection.execute("UPDATE lab.entries SET result_json=%s WHERE revision=1", (canonical_bytes(result).decode("utf-8"),))
    with pytest.raises(LabError, match="lab_store_corrupt"):
        current.read()


def test_invalid_copied_adapter_identity_cannot_initialize(target, adapter):
    from dataclasses import replace
    bad = replace(adapter, identity=adapter.identity.model_copy(update={"contract_version": "invalid"}))
    with pytest.raises(LabError):
        ControllerStore.init(target[0], binding(), adapter=bad)
    with raw(target[0]) as connection:
        assert connection.execute("SELECT count(*) FROM pg_tables WHERE schemaname='lab'").fetchone()[0] == 0


def test_actual_constraints_and_foreign_binding_open(target, adapter):
    current = store(target, adapter)
    initial = request(current.read())
    committed = current.append(initial)
    for revision in (-1, 129):
        with pytest.raises(psycopg.errors.CheckViolation):
            with raw(target[0]) as connection:
                connection.execute("UPDATE lab.entries SET revision=%s", (revision,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        with raw(target[0]) as connection:
            connection.execute("INSERT INTO lab.entries SELECT 2,operation_id,request_json,result_json,request_digest,bundle_fingerprint,previous_digest,%s "
                               "FROM lab.entries WHERE revision=1", ("0" * 64,))
    changed = current.binding.model_copy(update={"subject_id": str(uuid4())})
    with pytest.raises(LabError, match="lab_binding_conflict"):
        ControllerStore.open(target[0], changed, adapter=adapter)
    assert current.read().last_commit == committed


def test_capacity_does_not_hide_old_idempotent_result(target, adapter, monkeypatch):
    import tools.policy_revision_lab.controller_store as module
    current = store(target, adapter)
    initial = request(current.read())
    committed = current.append(initial)
    monkeypatch.setattr(module, "MAX_ENTRIES", 1)
    with pytest.raises(LabError, match="lab_capacity_exceeded"):
        current.append(request(current.read()))
    assert current.append(initial) == committed
    assert current.read().revision == 1


def test_actual_controller_cli_flow_never_promotes_revision_or_overwrites_config(target, adapter):
    import json
    config, root = target
    identity = binding()
    binding_file, input_file = root / "binding.json", root / "append.json"
    write_private_json(binding_file, identity.model_dump(mode="json"))
    original_config = config.read_bytes()
    secret = read_private_json(config)["connection_secret"]
    output_text = []
    environment = {**os.environ, "PYTHONPATH": str(PROJECT / "src") + os.pathsep + str(PROJECT)}

    def invoke(command, output, *, with_input=False):
        arguments = [sys.executable, "-m", "tools.policy_revision_lab.cli", command,
            "--backend", "controller", "--location", str(config), "--binding-file", str(binding_file),
            "--hbf-root", str(HBF_ROOT), "--output", str(output)]
        if with_input:
            arguments += ["--input", str(input_file)]
        result = subprocess.run(arguments, cwd=PROJECT, env=environment, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True, timeout=15)
        output_text.extend((result.stdout, result.stderr))
        assert secret not in result.stdout + result.stderr
        return result

    rejected = invoke("init", config)
    assert rejected.returncode == 1 and rejected.stderr.strip() == "lab_output_is_input"
    assert config.read_bytes() == original_config
    with raw(config) as connection:
        assert connection.execute("SELECT count(*) FROM pg_tables WHERE schemaname='lab'").fetchone()[0] == 0
    assert invoke("init", root / "init-output.json").returncode == 0
    current = ControllerStore.open(config, identity, adapter=adapter)
    write_private_json(input_file, request(current.read(), content=bundle("DENY")).model_dump(mode="json"))
    assert invoke("append", root / "append-output.json", with_input=True).returncode == 0
    for command in ("read", "check", "report"):
        output = root / (command + "-output.json")
        assert invoke(command, output).returncode == 0
        result = json.loads(output.read_text(encoding="utf-8"))
        head = result["head"] if command in {"check", "report"} else result
        assert head["draft_revision"] == 1 and head["staged_revision"] is None
        assert head["controller_desired_revision"] is head["device_policy_revision"] is None
        assert not head["execution_authorized"] and head["verification"] == "not_performed"
        if command == "report":
            assert result["precondition_status"] == "precondition_evidence_missing"
            assert result["rollout_status"] == "would_pause"
            assert "windows_acceptance_missing" in result["blockers"]
    write_private_json(input_file, request(current.read()).model_dump(mode="json"))
    assert invoke("append", config, with_input=True).returncode == 1
    assert config.read_bytes() == original_config and current.read().revision == 1
    assert all("postgresql://" not in text and "postgresql+psycopg://" not in text for text in output_text)


@pytest.mark.parametrize("table,column", [
    ("stream", "binding"), ("stream", "adapter_fingerprint"), ("stream", "head_fingerprint"),
    ("stream", "head_digest"), ("entries", "request_digest"), ("entries", "bundle_fingerprint"),
    ("entries", "previous_digest"), ("area", "marker"),
])
def test_oversized_corrupt_metadata_is_rejected_before_payload_fetch(target, adapter, table, column, monkeypatch):
    from psycopg import sql
    import tools.policy_revision_lab.controller_store as module
    from scripts import managed_postgres as owned
    current = store(target, adapter)
    current.append(request(current.read()))
    old_marker = None
    if table == "area":
        cfg = read_private_json(target[0])
        fixture = owned._read_config()
        with owned._admin_connection(fixture, dbname=cfg["database_name"]) as connection:
            old_marker = connection.execute("SELECT marker FROM lab_identity.area").fetchone()[0]
            connection.execute("UPDATE lab_identity.area SET marker=%s", ("x" * (1024 * 1024),))
    else:
        with raw(target[0]) as connection:
            checks = connection.execute("SELECT c.conname FROM pg_constraint c JOIN pg_class r ON r.oid=c.conrelid "
                "JOIN pg_namespace n ON n.oid=r.relnamespace JOIN pg_attribute a ON a.attrelid=r.oid "
                "AND a.attnum=ANY(c.conkey) WHERE n.nspname='lab' AND r.relname=%s AND a.attname=%s AND c.contype='c'",
                (table, column)).fetchall()
            for (name,) in checks:
                connection.execute(sql.SQL("ALTER TABLE lab.{} DROP CONSTRAINT {}").format(sql.Identifier(table), sql.Identifier(name)))
            connection.execute(sql.SQL("UPDATE lab.{} SET {}=%s").format(sql.Identifier(table), sql.Identifier(column)),
                               ("x" * (1024 * 1024),))
    original = module._json

    def bounded_decode(raw_value, model):
        if model is LabBinding and raw_value is not None:
            assert len(raw_value.encode("utf-8")) <= 2048
        return original(raw_value, model)

    monkeypatch.setattr(module, "_json", bounded_decode)
    try:
        with pytest.raises(LabError):
            current.read()
    finally:
        if old_marker is not None:
            with owned._admin_connection(fixture, dbname=cfg["database_name"]) as connection:
                connection.execute("UPDATE lab_identity.area SET marker=%s", (old_marker,))
