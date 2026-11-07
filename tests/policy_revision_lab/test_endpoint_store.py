import json
from contextlib import closing
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from uuid import uuid4

import pytest

from security_platform.connectors.hostbased_firewall.private_files import (create_private_directory,
    validate_private_path, write_private_json)
from security_platform.policy_contracts.fingerprints import bundle_fingerprint, canonical_bytes
from security_platform.policy_contracts.models import PolicyBundle
from tools.policy_revision_lab.endpoint_store import DATABASE_FILENAME, MARKER_FILENAME, EndpointStore
from tools.policy_revision_lab.models import AppendRequest, LabBinding, LabError, MAX_REVISION, make_commit, normalize_request


def request_for(head, bundle, **updates):
    return AppendRequest.model_validate({"binding": head.binding, "operation_id": str(uuid4()),
        "expected_lineage": head.lineage, "expected_revision": head.revision,
        "base_fingerprint": head.bundle_fingerprint, "bundle": bundle, **updates})


@pytest.fixture
def endpoint(private_parent, lab_binding, hbf_adapter):
    return EndpointStore.init(private_parent / "endpoint", lab_binding, hbf_adapter)


def test_explicit_init_restart_full_payload_and_fixed_non_authority(endpoint, lab_bundle, hbf_adapter):
    empty = endpoint.read()
    assert empty.revision == empty.staged_revision == 0 and empty.bundle is None
    assert empty.draft_revision is None and empty.bundle_fingerprint is None
    request = request_for(empty, lab_bundle)
    result = endpoint.append(request)
    reopened = EndpointStore.open(endpoint.root, endpoint.binding, hbf_adapter)
    head = reopened.read()
    assert head.lineage == empty.lineage and head.revision == head.staged_revision == 1
    assert canonical_bytes(head.bundle.model_dump(mode="json")) == canonical_bytes(lab_bundle.model_dump(mode="json"))
    assert head.last_commit == result and result.operation_id == request.operation_id
    assert reopened.check().checked_entries == 1
    for dto in (head, result, reopened.check()):
        assert dto.authority == "unbound" and dto.operational_binding == "absent"
        assert dto.identity_source == "fixture" and dto.rollback_protection == "not_established"
        assert dto.controller_desired_revision is dto.device_policy_revision is None
        assert dto.execution_authorized is False and dto.verification == "not_performed"
    validate_private_path(endpoint.root, directory=True)
    for path in endpoint.root.iterdir():
        validate_private_path(path)


def test_init_never_adopts_existing_root_and_open_never_creates(private_parent, lab_binding, hbf_adapter):
    missing = private_parent / "missing"
    with pytest.raises(LabError):
        EndpointStore.open(missing, lab_binding, hbf_adapter)
    assert not missing.exists()
    existing = create_private_directory(private_parent / "existing")
    with pytest.raises(LabError, match="^lab_root_exists$"):
        EndpointStore.init(existing, lab_binding, hbf_adapter)
    assert list(existing.iterdir()) == []
    (existing / "unknown.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(LabError):
        EndpointStore.init(existing, lab_binding, hbf_adapter)
    assert (existing / "unknown.txt").read_text() == "keep"


def test_aba_exact_retry_after_restart_and_head_advance(endpoint, lab_bundle, hbf_adapter):
    a = request_for(endpoint.read(), lab_bundle)
    first = endpoint.append(a)
    b_bundle = hbf_adapter.normalize(PolicyBundle.model_validate({**lab_bundle.model_dump(mode="json"),
        "policies": {"default_action": "DENY", "policies": []}}))
    second = endpoint.append(request_for(endpoint.read(), b_bundle))
    third = endpoint.append(request_for(endpoint.read(), lab_bundle))
    assert [first.staged_revision, second.staged_revision, third.staged_revision] == [1, 2, 3]
    assert first.bundle_fingerprint == third.bundle_fingerprint != second.bundle_fingerprint
    reopened = EndpointStore.open(endpoint.root, endpoint.binding, hbf_adapter)
    assert reopened.append(a) == first
    assert reopened.read().revision == 3 and reopened.read().last_commit == third
    with pytest.raises(LabError, match="^lab_cas_conflict$"):
        reopened.append(request_for(reopened.read(), lab_bundle, expected_revision=1,
            base_fingerprint=first.bundle_fingerprint))
    with pytest.raises(LabError, match="^lab_operation_conflict$"):
        reopened.append(request_for(reopened.read(), lab_bundle, operation_id=a.operation_id))
    # A new operation commits even when content is unchanged.
    assert reopened.append(request_for(reopened.read(), lab_bundle)).staged_revision == 4


@pytest.mark.parametrize("field", ["tenant_id", "subject_id", "kind", "product_id", "enforcement_scope"])
def test_wrong_immutable_binding_is_side_effect_free(endpoint, lab_bundle, field):
    head = endpoint.read()
    values = {"tenant_id": str(uuid4()), "subject_id": str(uuid4()), "kind": "controller_draft",
              "product_id": "termivar", "enforcement_scope": "native_firewall"}
    # Deliberately bypass construction: public store must revalidate copied models.
    binding = head.binding.model_copy(update={field: values[field]})
    request = request_for(head, lab_bundle).model_copy(update={"binding": binding})
    with pytest.raises(LabError):
        endpoint.append(request)
    assert endpoint.read() == head


@pytest.mark.parametrize("field,value", [("expected_lineage", str(uuid4())),
    ("base_fingerprint", "sp-hbf-bundle-v1:sha256:" + "1" * 64), ("expected_revision", 7)])
def test_wrong_cas_side_effect_free(endpoint, lab_bundle, field, value):
    endpoint.append(request_for(endpoint.read(), lab_bundle))
    head = endpoint.read()
    with pytest.raises(LabError, match="^lab_cas_conflict$"):
        endpoint.append(request_for(head, lab_bundle, **{field: value}))
    assert endpoint.read() == head


@pytest.mark.parametrize("value", [True, -1, 1.0, "1", MAX_REVISION + 1])
def test_revision_types_and_overflow_rejected_without_write(endpoint, lab_bundle, value):
    head = endpoint.read()
    invalid = request_for(head, lab_bundle).model_copy(update={"expected_revision": value})
    with pytest.raises(LabError):
        endpoint.append(invalid)
    assert endpoint.read() == head


def test_commit_overflow_guard_and_input_immutability(endpoint, lab_bundle):
    original = request_for(endpoint.read(), lab_bundle)
    with pytest.raises(LabError):
        make_commit(original, original.expected_lineage, MAX_REVISION + 1, "2026-11-07T10:00:00.000000Z")
    assert original.expected_revision == 0 and original.bundle == lab_bundle


@pytest.mark.parametrize("mutation", [
    "UPDATE lab_meta SET head_revision=3", "UPDATE lab_meta SET head_fingerprint='bad'",
    "DELETE FROM lab_entries WHERE revision=1", "UPDATE lab_entries SET bundle_json=x'7b7d' WHERE revision=1",
    "UPDATE lab_entries SET request_digest='bad' WHERE revision=1",
    "UPDATE lab_entries SET result_json=x'7b7d' WHERE revision=1",
    "UPDATE lab_entries SET entry_digest='bad' WHERE revision=1",
    "UPDATE lab_meta SET lineage='00000000-0000-0000-0000-000000000001'",
    "UPDATE lab_meta SET store_id='00000000-0000-0000-0000-000000000001'",
    "DROP TABLE lab_entries",
])
def test_all_history_corruption_fails_closed(endpoint, lab_bundle, hbf_adapter, mutation):
    first = request_for(endpoint.read(), lab_bundle)
    endpoint.append(first)
    endpoint.append(request_for(endpoint.read(), lab_bundle))
    with closing(sqlite3.connect(endpoint.root / DATABASE_FILENAME)) as connection:
        connection.execute(mutation)
        connection.commit()
    before = (endpoint.root / DATABASE_FILENAME).read_bytes()
    for action in (lambda: endpoint.read(), lambda: endpoint.append(first),
                   lambda: EndpointStore.open(endpoint.root, endpoint.binding, hbf_adapter)):
        with pytest.raises(LabError):
            action()
    assert (endpoint.root / DATABASE_FILENAME).read_bytes() == before


def test_missing_marker_or_db_never_repaired(endpoint, hbf_adapter):
    marker = endpoint.root / MARKER_FILENAME
    saved = marker.read_bytes()
    marker.unlink()
    with pytest.raises(LabError):
        EndpointStore.open(endpoint.root, endpoint.binding, hbf_adapter)
    assert not marker.exists()
    write_private_json(marker, json.loads(saved))
    (endpoint.root / DATABASE_FILENAME).unlink()
    with pytest.raises(LabError):
        EndpointStore.open(endpoint.root, endpoint.binding, hbf_adapter)
    assert not (endpoint.root / DATABASE_FILENAME).exists()


def test_consistent_old_clone_has_no_external_rollback_detection(endpoint, lab_bundle, hbf_adapter, private_parent):
    first = endpoint.append(request_for(endpoint.read(), lab_bundle))
    clone = create_private_directory(private_parent / "clone")
    # Clone is explicitly made by this fixture, with each file's native privacy.
    write_private_json(clone / MARKER_FILENAME, json.loads((endpoint.root / MARKER_FILENAME).read_bytes()))
    shutil.copyfile(endpoint.root / DATABASE_FILENAME, clone / DATABASE_FILENAME)
    if os.name == "nt":
        from security_platform.connectors.hostbased_firewall.private_files import _install_private_windows_acl
        _install_private_windows_acl(clone / DATABASE_FILENAME)
    else:
        (clone / DATABASE_FILENAME).chmod(0o600)
    endpoint.append(request_for(endpoint.read(), lab_bundle))
    old = EndpointStore.open(clone, endpoint.binding, hbf_adapter).read()
    assert old.revision == 1 and old.last_commit == first
    assert old.rollback_protection == "not_established" and endpoint.read().revision == 2


def test_ordered_zones_normalization_and_legacy_hash_ambiguity_rejection(endpoint, lab_bundle, hbf_adapter):
    ordered = PolicyBundle.model_validate({**lab_bundle.model_dump(mode="json"), "ordered_zones": [
        {"name": "B", "cidrs": ["192.168.0.0/16"]}, {"name": "A", "cidrs": ["10.0.0.0/8"]}]})
    endpoint.append(request_for(endpoint.read(), ordered))
    assert [zone.name for zone in endpoint.read().bundle.ordered_zones] == ["B", "A"]
    ambiguous = PolicyBundle.model_validate({**ordered.model_dump(mode="json"), "ordered_zones": [
        {"name": "A", "cidrs": ["10.1.2.3/8"]}, {"name": "B", "cidrs": ["10.0.0.0/8"]}]})
    reverse = PolicyBundle.model_validate({**ambiguous.model_dump(mode="json"),
        "ordered_zones": list(reversed(ambiguous.model_dump(mode="json")["ordered_zones"]))})
    assert hbf_adapter.legacy_version(ambiguous) == hbf_adapter.legacy_version(reverse)
    before = endpoint.read()
    for bundle in (ambiguous, reverse, lab_bundle.model_copy(update={"schema_version": True})):
        with pytest.raises(LabError):
            endpoint.append(request_for(before, lab_bundle).model_copy(update={"bundle": bundle}))
    assert endpoint.read() == before


CHILD = r'''
import json,os,sys,time
from pathlib import Path
from security_platform.policy_contracts.hbf_bridge import load_hbf_adapter
from tools.policy_revision_lab.endpoint_store import EndpointStore
from tools.policy_revision_lab.models import LabBinding,LabError
root,binding,request,source,barrier,action=sys.argv[1:]
store=EndpointStore.open(root,LabBinding.model_validate_json(binding),load_hbf_adapter(source))
Path(barrier+'.ready.'+str(os.getpid())).write_text('ready')
deadline=time.monotonic()+15
while not Path(barrier).exists():
    if time.monotonic()>deadline: raise SystemExit(9)
    time.sleep(.01)
if action in ('before','after'):
    original=store._connection
    from contextlib import contextmanager
    @contextmanager
    def wrapped(**kwargs):
        with original(**kwargs) as con:
            class Proxy:
                def __getattr__(self,name): return getattr(con,name)
                def commit(self):
                    if action=='before': os._exit(71)
                    con.commit()
                    os._exit(72)
            yield Proxy()
    store._connection=wrapped
try:
    value=store.append(json.loads(request))
    print(json.dumps({'ok':value.model_dump(mode='json')}),flush=True)
except LabError as exc:
    print(json.dumps({'error':exc.code}),flush=True)
'''


def spawn(endpoint, request, hbf_source, barrier, action="normal"):
    env = dict(os.environ)
    project = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = os.pathsep.join((str(project / "src"), str(project)))
    return subprocess.Popen([sys.executable, "-c", CHILD, str(endpoint.root), endpoint.binding.model_dump_json(),
        request.model_dump_json(), str(hbf_source), str(barrier), action], cwd=project, env=env,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def release(children, barrier):
    deadline = time.monotonic() + 15
    while len(list(barrier.parent.glob(barrier.name + ".ready.*"))) < len(children):
        assert time.monotonic() < deadline, "child startup barrier timed out"
        assert all(child.poll() is None for child in children), [child.communicate() for child in children]
        time.sleep(.01)
    barrier.write_text("go")


@pytest.mark.parametrize("race", ["different_ids", "exact_retry", "conflicting_retry"])
def test_two_independent_processes_atomic_cas_and_exact_idempotency(endpoint, lab_bundle, hbf_source, hbf_adapter, private_parent, race):
    head = endpoint.read()
    request = request_for(head, lab_bundle)
    other = request if race == "exact_retry" else request_for(head, lab_bundle)
    if race == "conflicting_retry":
        changed = hbf_adapter.normalize(PolicyBundle.model_validate({**lab_bundle.model_dump(mode="json"),
            "policies": {"default_action": "DENY", "policies": []}}))
        other = request_for(head, changed, operation_id=request.operation_id)
    barrier = private_parent / "go"
    children = [spawn(endpoint, value, hbf_source, barrier) for value in (request, other)]
    try:
        release(children, barrier)
        responses = []
        for child in children:
            output, error = child.communicate(timeout=20)
            assert child.returncode == 0, error
            responses.append(json.loads(output))
        successful = [response["ok"] for response in responses if "ok" in response]
        assert len(successful) == (2 if race == "exact_retry" else 1)
        if race == "exact_retry":
            assert successful[0] == successful[1]
        else:
            expected = "lab_operation_conflict" if race == "conflicting_retry" else "lab_cas_conflict"
            assert [response["error"] for response in responses if "error" in response] == [expected]
        assert endpoint.read().revision == endpoint.check().checked_entries == 1
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=5)


@pytest.mark.parametrize("action,code,revision", [("before", 71, 0), ("after", 72, 1)])
def test_process_crash_before_commit_and_committed_response_loss(endpoint, lab_bundle, hbf_source, hbf_adapter, private_parent, action, code, revision):
    request = request_for(endpoint.read(), lab_bundle)
    barrier = private_parent / "crash-go"
    child = spawn(endpoint, request, hbf_source, barrier, action)
    try:
        release([child], barrier)
        output, error = child.communicate(timeout=20)
        assert child.returncode == code, (output, error)
        reopened = EndpointStore.open(endpoint.root, endpoint.binding, hbf_adapter)
        assert reopened.read().revision == revision
        committed = reopened.append(request)
        assert committed.staged_revision == 1 and reopened.read().revision == 1
        assert reopened.append(request) == committed
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=5)


def test_unknown_file_private_path_and_hardlink_escape_fail_closed(endpoint, private_parent, lab_bundle):
    unknown = endpoint.root / "foreign.json"
    write_private_json(unknown, {"unrelated": True})
    with pytest.raises(LabError):
        endpoint.read()
    assert unknown.exists()
    unknown.unlink()
    link = private_parent / "external-hardlink"
    os.link(endpoint.root / DATABASE_FILENAME, link)
    try:
        with pytest.raises(LabError):
            endpoint.read()
    finally:
        link.unlink()
    assert endpoint.read().revision == 0


def test_adapter_identity_change_cannot_relabel_existing_history(endpoint, hbf_adapter):
    from dataclasses import replace
    changed = replace(hbf_adapter, identity=hbf_adapter.identity.model_copy(update={"python_version": "different"}))
    with pytest.raises(LabError, match="^lab_adapter_mismatch$"):
        EndpointStore.open(endpoint.root, endpoint.binding, changed)


def test_sqlite_lock_wait_is_bounded_and_does_not_advance_head(endpoint, lab_bundle):
    head = endpoint.read()
    with closing(sqlite3.connect(endpoint.root / DATABASE_FILENAME)) as competing:
        competing.execute("BEGIN IMMEDIATE")
        started = time.monotonic()
        with pytest.raises(LabError, match="^lab_store_busy$"):
            endpoint.append(request_for(head, lab_bundle))
        assert 2.5 <= time.monotonic() - started < 6
        competing.rollback()
    assert endpoint.read() == head


def test_native_private_file_permission_rejects_added_public_reader(endpoint):
    database = endpoint.root / DATABASE_FILENAME
    if os.name == "nt":
        from security_platform.connectors.hostbased_firewall.private_files import _install_private_windows_acl
        result = subprocess.run(["icacls", str(database), "/grant", "*S-1-1-0:(R)"], capture_output=True, timeout=5)
        assert result.returncode == 0
        restore = lambda: _install_private_windows_acl(database)
    else:
        database.chmod(0o644)
        restore = lambda: database.chmod(0o600)
    try:
        with pytest.raises(LabError):
            endpoint.read()
    finally:
        restore()
    assert endpoint.read().revision == 0


def test_symlink_root_redirect_is_rejected(endpoint, private_parent, hbf_adapter):
    redirect = private_parent / "redirect"
    try:
        redirect.symlink_to(endpoint.root, target_is_directory=True)
    except OSError as exc:
        pytest.skip("OS did not permit creating this isolated symlink fixture: " + str(getattr(exc, "winerror", exc.errno)))
    try:
        with pytest.raises(LabError):
            EndpointStore.open(redirect, endpoint.binding, hbf_adapter)
    finally:
        redirect.unlink()
