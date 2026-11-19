"""Inspector agreement and disclosure checks with synthetic local records.

The CLI runs here replace only ``load_inputs`` with a loader that reads the
capsule and request from disk through the owner InputBudget and supplies a
synthetic local reference snapshot, so the import CLI, the published files
and the independent inspector run unchanged on IDENTITY_MISMATCH and
multi-task outputs. The file loaders for local records are tested at the
end with the owner inspection functions replaced by synthetic stand-ins,
because building real Phase42/Phase43 outputs needs the whole earlier
chain. Every value is synthetic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from exchange_contracts import MAX_CAPSULE_BYTES, MAX_TOTAL_INPUT_BYTES, InputError, json_bytes, parse_json
from reconciliation_contracts import MAX_REQUEST_BYTES, validate_request
from reconciliation_inputs import LoadedInputs, add_input_arguments
from synthetic_fixtures import (
    TOOL, canonical_capsule, full_local, local, phase42_record, phase43_record, request, sha, synthetic_envelope,
    synthetic_task,
)
import import_task_capsule
import inspect_task_reconciliation
from reconciliation_engine import reconcile_capsule

BOTH = "PHASE42_TASK_RECORDS_AND_PHASE43_DISCLOSURE_RECORDS"
P42_ONLY = "PHASE42_TASK_RECORDS_ONLY"
P43_ONLY = "PHASE43_DISCLOSURE_RECORDS_ONLY"
OUT = ("task-inbox-record.json", "capsule-reconciliation-report.json", "capsule-reconciliation-summary.md",
       "manifest.json")
T7 = synthetic_task("F0007")
T8 = synthetic_task("F0008", "SYNTH0002", "b")


def tasks(count: int) -> list:
    return [synthetic_task("F%04d" % (index + 1), "SYNTH%04d" % (index + 1), "t%d" % index) for index in range(count)]


def snapshot_for(mode: str, imported: bytes, disclosed: bytes | None = None, p42_tasks: list | None = None):
    p42 = phase42_record(p42_tasks) if mode != P43_ONLY else None
    p43 = phase43_record(disclosed or imported) if mode != P42_ONLY else None
    req = request(mode, p42 and p42["register_sha256"], p43 and p43["index_sha256"])
    return local(mode, p42, p43), req


def rows(report: dict, **match) -> list:
    return [r for r in report["local_reconciliation"]["comparisons"]
            if all(r[key] == value for key, value in match.items())]


def rules(report: dict) -> set:
    return {item["rule"] for item in report["findings"]}


class Harness:
    def __init__(self, root: Path, monkeypatch):
        self.root, self.monkeypatch = root, monkeypatch

    def publish(self, capsule: bytes, snapshot, req: dict) -> int:
        (self.root / "capsule.zip").write_bytes(capsule)
        (self.root / "request.json").write_bytes(json_bytes(req))

        def load_inputs(args) -> LoadedInputs:
            from phase42_adapter import InputBudget

            budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
            request_raw = budget.read_text(args.request, MAX_REQUEST_BYTES)
            loaded = validate_request(parse_json(request_raw, maximum=MAX_REQUEST_BYTES))
            return LoadedInputs(budget.read_binary(args.capsule, MAX_CAPSULE_BYTES), request_raw, loaded,
                                snapshot, budget)

        self.monkeypatch.setattr(import_task_capsule, "load_inputs", load_inputs)
        self.monkeypatch.setattr(inspect_task_reconciliation, "load_inputs", load_inputs)
        return import_task_capsule.main(["--capsule", "capsule.zip", "--request", "request.json", "--output-dir", "out"])

    def argv(self) -> list:
        return ["--capsule", "capsule.zip", "--request", "request.json", "--inbox", "out/" + OUT[0],
                "--report", "out/" + OUT[1], "--summary", "out/" + OUT[2], "--manifest", "out/" + OUT[3],
                "--output", "out/inspection-summary.json"]

    def inspect(self) -> int:
        return inspect_task_reconciliation.main(self.argv())

    def inspect_error(self) -> str | None:
        parser = argparse.ArgumentParser()
        add_input_arguments(parser)
        for name in ("inbox", "report", "summary", "manifest", "output"):
            parser.add_argument("--" + name, required=True)
        try:
            inspect_task_reconciliation.inspect_task_reconciliation(parser.parse_args(self.argv()))
        except InputError as error:
            return str(error)
        return None

    def load(self, name: str) -> dict:
        return json.loads((self.root / "out" / name).read_text(encoding="utf-8"))

    def store_with_summary(self, report: dict) -> None:
        """Store a tampered report with a matching re-rendered summary, so the summary check cannot fire first."""
        from reconciliation_renderer import render_reconciliation_summary

        (self.root / "out" / OUT[2]).write_bytes(render_reconciliation_summary(report, self.load(OUT[0])))
        self.store(OUT[1], report)

    def store(self, name: str, model: dict) -> None:
        (self.root / "out" / name).write_bytes(json_bytes(model))
        manifest = self.load(OUT[3])
        for item in manifest["files"]:
            raw = (self.root / "out" / item["name"]).read_bytes()
            item["bytes"], item["sha256"] = len(raw), hashlib.sha256(raw).hexdigest()
        (self.root / "out" / OUT[3]).write_bytes(json_bytes(manifest))


@pytest.fixture
def harness(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return Harness(tmp_path, monkeypatch)


def disagreement(code: str) -> str:
    return "task_reconciliation_inspection_disagreement_" + code


# --- IDENTITY_MISMATCH outputs must be inspectable (the Phase44 audit O1 regression) ---

@pytest.mark.parametrize("mode", [P43_ONLY, BOTH])
def test_inspector_agrees_on_mismatch_against_multi_task_disclosure_record(harness, mode):
    disclosed = canonical_capsule(synthetic_envelope([T7, T8]))
    imported = canonical_capsule(synthetic_envelope([T7]))
    snapshot, req = snapshot_for(mode, imported, disclosed, [T7, T8])
    assert harness.publish(imported, snapshot, req) == 3
    report = harness.load(OUT[1])
    assert report["eligibility"]["status"] == "IDENTITY_MISMATCH"
    row = rows(report, field="task_id_list")[0]
    assert (row["result"], row["capsule_value"], row["local_value"], row["local_value_disclosure"]) == (
        "MISMATCH", "F0007", "F0007,F0008", "ECHOED")
    assert harness.inspect() == 0
    inspection = harness.load("inspection-summary.json")
    assert inspection["eligibility_agreement"] == "AGREES"
    assert inspection["independently_derived_eligibility_status"] == "IDENTITY_MISMATCH"


def test_inspector_rejects_echoed_value_that_is_not_the_local_record_value(harness):
    disclosed = canonical_capsule(synthetic_envelope([T7, T8]))
    imported = canonical_capsule(synthetic_envelope([T7]))
    assert harness.publish(imported, *snapshot_for(BOTH, imported, disclosed, [T7, T8])) == 3
    report = harness.load(OUT[1])
    rows(report, field="task_id_list")[0]["local_value"] = "F0007,F0009"
    harness.store(OUT[1], report)
    assert harness.inspect_error() == disagreement("echoed_value_differs_from_local_record")
    assert harness.inspect() == 2
    assert not (harness.root / "out" / "inspection-summary.json").exists()


def test_inspector_rejects_undisclosed_phase42_value_echoed(harness):
    imported = canonical_capsule(synthetic_envelope([dict(T7, candidate_id="SYNTH0099")]))
    assert harness.publish(imported, *snapshot_for(P42_ONLY, imported, p42_tasks=[T7])) == 3
    report = harness.load(OUT[1])
    row = rows(report, field="candidate_id", reference_source="PHASE42_LOCAL_TASK_RECORD")[0]
    assert row["local_value"] is None and row["local_value_disclosure"] == "WITHHELD_NOT_PREVIOUSLY_DISCLOSED"
    assert harness.inspect() == 0
    row.update(local_value="SYNTH0001", local_value_disclosure="ECHOED")
    harness.store(OUT[1], report)
    assert harness.inspect_error() == disagreement("undisclosed_local_value_echoed")


def test_inspector_recomputes_match_rows_from_the_local_record(harness):
    capsule = canonical_capsule()
    assert harness.publish(capsule, *full_local(capsule)) == 0
    report = harness.load(OUT[1])
    row = rows(report, field="candidate_id", reference_source="PHASE42_LOCAL_TASK_RECORD")[0]
    row.update(capsule_value="SYNTH0999", local_value="SYNTH0999")
    harness.store(OUT[1], report)
    assert harness.inspect_error() == disagreement("echoed_value_differs_from_local_record")


def test_phase42_value_is_disclosed_only_when_phase43_states_the_same_value(harness):
    p43_task = dict(T7, candidate_id="SYNTH0002")          # Phase43 disclosed a different candidate for F0007
    imported = canonical_capsule(synthetic_envelope([dict(T7, candidate_id="SYNTH0003")]))
    disclosed = canonical_capsule(synthetic_envelope([p43_task]))
    assert harness.publish(imported, *snapshot_for(BOTH, imported, disclosed, [T7])) == 3
    report = harness.load(OUT[1])
    p42_row = rows(report, field="candidate_id", reference_source="PHASE42_LOCAL_TASK_RECORD")[0]
    p43_row = rows(report, field="candidate_id", reference_source="PHASE43_LOCAL_DISCLOSURE_RECORD")[0]
    assert (p42_row["result"], p42_row["local_value"], p42_row["local_value_disclosure"]) == (
        "MISMATCH", None, "WITHHELD_NOT_PREVIOUSLY_DISCLOSED")
    assert (p43_row["result"], p43_row["local_value"], p43_row["local_value_disclosure"]) == (
        "MISMATCH", "SYNTH0002", "ECHOED")
    assert harness.inspect() == 0
    p42_row.update(local_value="SYNTH0001", local_value_disclosure="ECHOED")
    harness.store_with_summary(report)
    assert harness.inspect_error() == disagreement("undisclosed_local_value_echoed")


def test_inspector_rejects_echo_of_undisclosed_binding_owner(harness):
    capsule = canonical_capsule(synthetic_envelope([_triple_claim()]))
    assert harness.publish(capsule, *snapshot_for(P42_ONLY, capsule, p42_tasks=[T7, T8])) == 3
    report = harness.load(OUT[1])
    rows(report, field="binding_triple_owner_task")[0].update(local_value="F0007", local_value_disclosure="ECHOED")
    harness.store_with_summary(report)
    assert harness.inspect_error() == disagreement("undisclosed_local_value_echoed")


@pytest.mark.parametrize("value", ["SYNTH0999", 0])
def test_match_row_with_different_or_differently_typed_values_is_rejected(harness, value):
    # The closed report contract already requires a MATCH row to carry the same
    # value of the same type on both sides, so the inspector's own
    # match_local_value_differs check is a second guard that this input never reaches.
    capsule = canonical_capsule()
    assert harness.publish(capsule, *full_local(capsule)) == 0
    report = harness.load(OUT[1])
    field = "candidate_id" if type(value) is str else "candidate_present"
    rows(report, field=field, reference_source="PHASE42_LOCAL_TASK_RECORD")[0]["capsule_value"] = value
    harness.store(OUT[1], report)
    assert harness.inspect_error() == "task_reconciliation_invalid_comparison_match_semantics"
    assert harness.inspect() == 2


@pytest.mark.parametrize("mode", [P42_ONLY, BOTH])
def test_inspector_agrees_on_phase42_source_digest_mismatch(harness, mode):
    envelope = synthetic_envelope()
    envelope["source_phase42_register_sha256"] = sha("other-register")
    imported = canonical_capsule(envelope)
    assert harness.publish(imported, *snapshot_for(mode, imported, canonical_capsule(), [T7])) == 3
    report = harness.load(OUT[1])
    row = rows(report, subject="capsule", field="source_phase42_register_sha256",
               reference_source="PHASE42_LOCAL_TASK_RECORD")[0]
    assert (row["result"], row["local_value"], row["local_value_disclosure"]) == ("MISMATCH", sha("register"), "ECHOED")
    assert report["eligibility"]["status"] == "IDENTITY_MISMATCH"
    assert harness.inspect() == 0


def test_inspector_requires_a_finding_for_every_mismatch_row(harness):
    imported = canonical_capsule(synthetic_envelope([dict(T7, candidate_id="SYNTH0099")]))
    assert harness.publish(imported, *snapshot_for(P42_ONLY, imported, p42_tasks=[T7])) == 3
    report = harness.load(OUT[1])
    dropped = "P44-IDENTITY_MISMATCH:task:F0007.candidate_id:phase42"
    report["findings"] = [item for item in report["findings"] if item["finding_id"] != dropped]
    report["eligibility"]["basis_finding_ids"].remove(dropped)
    harness.store(OUT[1], report)
    assert harness.inspect_error() == disagreement("mismatch_without_finding")


# --- PHASE43-only mode, multi-task capsules and binding ownership ---

def test_phase43_only_mode_matches_disclosure_but_stays_unavailable(harness):
    capsule = canonical_capsule()
    snapshot, req = snapshot_for(P43_ONLY, capsule)
    report, inbox = reconcile_capsule(capsule, req, snapshot)
    assert {r["result"] for r in rows(report, reference_source="PHASE43_LOCAL_DISCLOSURE_RECORD")} == {"MATCH"}
    assert {r["result"] for r in rows(report, reference_source="PHASE42_LOCAL_TASK_RECORD")} == {"UNAVAILABLE"}
    assert report["local_reconciliation"]["task_lookups"][0]["phase42_lookup"] == "NOT_SUPPLIED"
    assert "P44-LOCAL_RECORDS_NOT_SUPPLIED:phase42" in report["eligibility"]["basis_finding_ids"]
    assert report["eligibility"]["status"] == "LOCAL_RECONCILIATION_UNAVAILABLE"
    assert inbox["admitted_tasks"][0]["local_reconciliation"] == "UNAVAILABLE"
    assert harness.publish(capsule, snapshot, req) == 3
    assert harness.inspect() == 0


@pytest.mark.parametrize("count", [2, 8])
def test_multi_task_capsule_full_match(harness, count):
    declared = tasks(count)
    capsule = canonical_capsule(synthetic_envelope(declared))
    snapshot, req = snapshot_for(BOTH, capsule, p42_tasks=declared)
    assert harness.publish(capsule, snapshot, req) == 0
    report, inbox = harness.load(OUT[1]), harness.load(OUT[0])
    assert report["eligibility"]["status"] == "STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW"
    assert {r["result"] for r in report["local_reconciliation"]["comparisons"]} == {"MATCH"}
    assert [item["task_id"] for item in inbox["admitted_tasks"]] == [task["task_id"] for task in declared]
    assert inbox["admitted_task_count"] == count
    assert {(lookup["phase42_lookup"], lookup["phase43_lookup"])
            for lookup in report["local_reconciliation"]["task_lookups"]} == {("FOUND", "FOUND")}
    assert rows(report, field="task_id_list")[0]["local_value"] == ",".join(t["task_id"] for t in declared)
    assert harness.inspect() == 0


def test_nine_tasks_exceed_the_owner_limit():
    capsule_tasks = tasks(9)
    from synthetic_fixtures import canonical_members, rehash_manifest, zip_members

    envelope = synthetic_envelope(capsule_tasks)
    members = rehash_manifest(dict(canonical_members(), **{"task-request.json": json_bytes(envelope)}))
    report, inbox = reconcile_capsule(zip_members(members), request(), local())
    assert "TASK_COUNT_LIMIT" in rules(report)
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION" and inbox["admitted_tasks"] == []


def _triple_claim() -> dict:
    """F0008 claimed with its own binding digest but F0007's reference/candidate/file triple."""
    return dict(T8, reference_id=T7["reference_id"], candidate_id=T7["candidate_id"], file_id=T7["file_id"])


def test_binding_triple_owned_by_other_task_is_withheld_without_disclosure():
    capsule = canonical_capsule(synthetic_envelope([_triple_claim()]))
    snapshot, req = snapshot_for(P42_ONLY, capsule, p42_tasks=[T7, T8])
    report, _ = reconcile_capsule(capsule, req, snapshot)
    triple = rows(report, field="binding_triple_owner_task")[0]
    assert (triple["result"], triple["capsule_value"], triple["local_value"]) == ("MISMATCH", "F0008", None)
    assert triple["local_value_disclosure"] == "WITHHELD_NOT_PREVIOUSLY_DISCLOSED"
    assert rows(report, field="binding_digest_owner_task")[0]["result"] == "MATCH"
    assert "P44-AMBIGUOUS_BINDING_OWNER:task:F0008.binding_triple_owner_task:phase42" in {
        item["finding_id"] for item in report["findings"]}
    assert report["eligibility"]["status"] == "IDENTITY_MISMATCH"


def test_binding_triple_owner_echoed_when_disclosed_and_inspector_agrees(harness):
    capsule = canonical_capsule(synthetic_envelope([_triple_claim()]))
    disclosed = canonical_capsule(synthetic_envelope([T7, T8]))
    snapshot, req = snapshot_for(BOTH, capsule, disclosed, [T7, T8])
    assert harness.publish(capsule, snapshot, req) == 3
    triple = rows(harness.load(OUT[1]), field="binding_triple_owner_task")[0]
    assert (triple["local_value"], triple["local_value_disclosure"]) == ("F0007", "ECHOED")
    assert harness.inspect() == 0


def test_task_without_local_binding_records_binding_not_found():
    capsule = canonical_capsule(synthetic_envelope([synthetic_task("F0011", "SYNTH0011", "k")]))
    snapshot, req = snapshot_for(P42_ONLY, capsule, p42_tasks=[T7])
    report, _ = reconcile_capsule(capsule, req, snapshot)
    found = {item["finding_id"] for item in report["findings"] if item["rule"] == "LOCAL_BINDING_NOT_FOUND"}
    assert found == {"P44-LOCAL_BINDING_NOT_FOUND:task:F0011.binding_digest_owner_task:phase42",
                     "P44-LOCAL_BINDING_NOT_FOUND:task:F0011.binding_triple_owner_task:phase42"}
    assert all(r["local_value"] is None for r in rows(report, subject="task:F0011"))


# --- the cross-check between Phase44 diagnostics and the owner reader ---

@pytest.mark.parametrize("change", ["request_reference", "candidate_id"])
def test_owner_envelope_that_differs_from_declaration_fails_closed(monkeypatch, change):
    import reconciliation_engine

    original = reconciliation_engine.read_portable_task_request

    def altered(snapshot):
        envelope, contract, artifacts = original(snapshot)
        if change == "request_reference":
            envelope["request_reference"] = "synthetic-owner-view"
        else:
            envelope["tasks"][0]["candidate_id"] = "SYNTH0777"
        return envelope, contract, artifacts

    monkeypatch.setattr(reconciliation_engine, "read_portable_task_request", altered)
    report, inbox = reconcile_capsule(canonical_capsule(), request(), local())
    structural = [item["rule"] for item in report["findings"] if item["severity"] == "BLOCKING"]
    assert structural == ["DIAGNOSTIC_OWNER_DISAGREEMENT"]           # no Phase44 finding of its own
    assert report["capsule_identity"]["claimed_vs_represented"] == "MISMATCH"
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert report["local_reconciliation"]["state"] == "NOT_PERFORMED_STRUCTURAL_REJECTION"
    assert inbox["admitted_tasks"] == []


# --- explicit file loaders, with the owner inspections replaced by stand-ins ---

PHASE43_FILES = ("task-exchange-capsule.zip", "task-exchange-index.json", "task-exchange-source-receipt.json",
                 "task-exchange-summary.md", "manifest.json")


def _identity(name: str, raw: bytes) -> dict:
    return {"name": name, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _phase43_files(root: Path) -> tuple:
    """Write the five files into the current directory; the owner reader takes relative paths only."""
    contents = (canonical_capsule(), b'{"synthetic": "index"}\n', b'{"synthetic": "receipt"}\n',
                b"# synthetic summary\n", b'{"synthetic": "manifest"}\n')
    for name, raw in zip(PHASE43_FILES, contents):
        (root / name).write_bytes(raw)
    return PHASE43_FILES


def _stand_in_phase43(monkeypatch, mutate=None, after_read=None):
    import inspect_task_exchange

    def inspect(*paths):
        artifacts = [_identity(name, Path(path).read_bytes()) for name, path in zip(PHASE43_FILES, paths)]
        envelope = synthetic_envelope()
        report = {"task_exchange_artifacts": artifacts, "capsule_sha256": artifacts[0]["sha256"],
                  "task_ids": [task["task_id"] for task in envelope["tasks"]],
                  "source_phase42_register_sha256": envelope["source_phase42_register_sha256"],
                  "source_phase42_manifest_sha256": envelope["source_phase42_manifest_sha256"],
                  "request_reference": envelope["request_reference"]}
        if mutate:
            mutate(report)
        if after_read:
            after_read(paths)
        return report

    monkeypatch.setattr(inspect_task_exchange, "inspect_task_exchange", inspect)


def _load_phase43(tmp_path, pin: str | None = None):
    from local_task_records import load_local_reference
    from phase42_adapter import InputBudget

    paths = _phase43_files(tmp_path)
    index_sha = hashlib.sha256((tmp_path / PHASE43_FILES[1]).read_bytes()).hexdigest()
    req = request(P43_ONLY, None, pin or index_sha)
    return load_local_reference(req, InputBudget(maximum=MAX_TOTAL_INPUT_BYTES), None, paths)


def test_phase43_loader_builds_the_record_from_explicit_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _stand_in_phase43(monkeypatch)
    record = _load_phase43(tmp_path).record()["phase43"]
    assert record["index_sha256"] == hashlib.sha256((tmp_path / PHASE43_FILES[1]).read_bytes()).hexdigest()
    assert record["task_ids"] == ["F0007"] and record["tasks"] == synthetic_envelope()["tasks"]
    from local_task_records import PHASE43_ROLES

    assert [item["role"] for item in record["inputs"]] == list(PHASE43_ROLES)
    assert [item["sha256"] for item in record["inputs"]] == [
        hashlib.sha256((tmp_path / name).read_bytes()).hexdigest() for name in PHASE43_FILES]


@pytest.mark.parametrize("fault, code", [
    ("file_changed_after_owner_read", "local_phase43_reread_identity"),
    ("index_pin", "local_phase43_index_pin"),
    ("owner_capsule_identity", "local_phase43_capsule_identity"),
    ("owner_task_ids", "local_phase43_task_ids"),
])
def test_phase43_loader_fails_closed(tmp_path, monkeypatch, fault, code):
    def change_file(paths):
        Path(paths[3]).write_bytes(b"# changed between the two reads\n")

    monkeypatch.chdir(tmp_path)
    _stand_in_phase43(
        monkeypatch,
        mutate={"owner_capsule_identity": lambda r: r.update(capsule_sha256=sha("other")),
                "owner_task_ids": lambda r: r.update(task_ids=["F0099"])}.get(fault),
        after_read=change_file if fault == "file_changed_after_owner_read" else None)
    with pytest.raises(InputError) as error:
        _load_phase43(tmp_path, pin=sha("other-index") if fault == "index_pin" else None)
    assert str(error.value) == "task_reconciliation_invalid_" + code


def _stand_in_phase42(monkeypatch, classified=True, order=None):
    import phase42_adapter
    from exchange_contracts import SOURCE_NAMES

    names = list(order or SOURCE_NAMES)
    artifacts = [{"name": name, "bytes": 100 + index, "sha256": sha("p42-file-" + name)}
                 for index, name in enumerate(names)]
    intake = {"intake_entries": [{key: T7[key] for key in ("task_id", "reference_id", "candidate_id", "file_id",
                                                            "binding_digest", "slot_status", "response_status",
                                                            "candidate_present")}]}
    classification = {"task_classifications": [{"task_id": "F0007", "observation_verified": False,
                                                "task_completed": False}] if classified else []}
    monkeypatch.setattr(phase42_adapter, "load_source", lambda *args: "snapshot")
    monkeypatch.setattr(phase42_adapter, "read_source", lambda _snapshot: (intake, classification, {}, artifacts))
    return artifacts


def _load_phase42(pin: str):
    from local_task_records import load_local_reference
    from phase42_adapter import InputBudget

    return load_local_reference(request(P42_ONLY, pin), InputBudget(maximum=MAX_TOTAL_INPUT_BYTES),
                                ("a", "b", "c", "d", "e"), None)


def test_phase42_loader_builds_the_record_and_checks_the_pin(monkeypatch):
    artifacts = _stand_in_phase42(monkeypatch)
    record = _load_phase42(artifacts[0]["sha256"]).record()["phase42"]
    assert record["tasks"] == [T7]
    assert (record["register_sha256"], record["manifest_sha256"]) == (artifacts[0]["sha256"], artifacts[-1]["sha256"])
    with pytest.raises(InputError) as error:
        _load_phase42(sha("other-register"))
    assert str(error.value) == "task_reconciliation_invalid_local_phase42_register_pin"


def test_phase42_loader_fails_closed_on_owner_inconsistency(monkeypatch):
    from exchange_contracts import SOURCE_NAMES

    artifacts = _stand_in_phase42(monkeypatch, classified=False)
    with pytest.raises(InputError) as error:
        _load_phase42(artifacts[0]["sha256"])
    assert str(error.value) == "task_reconciliation_invalid_local_phase42_classification_missing"
    artifacts = _stand_in_phase42(monkeypatch, order=tuple(reversed(SOURCE_NAMES)))
    with pytest.raises(InputError) as error:
        _load_phase42(artifacts[0]["sha256"])
    assert str(error.value) == "task_reconciliation_invalid_local_phase42_artifact_order"


def test_local_path_groups_must_match_the_request_mode():
    from local_task_records import load_local_reference
    from phase42_adapter import InputBudget

    with pytest.raises(InputError) as error:
        load_local_reference(request(P42_ONLY, sha("register")), InputBudget(maximum=MAX_TOTAL_INPUT_BYTES),
                             None, None)
    assert str(error.value) == "task_reconciliation_invalid_local_path_groups_do_not_match_request_mode"


# --- the shipped entry points under isolated mode ---

def test_cli_entry_points_run_under_isolated_python(tmp_path):
    (tmp_path / "capsule.zip").write_bytes(canonical_capsule())
    (tmp_path / "request.json").write_bytes(json_bytes(request()))
    base = [sys.executable, "-I", "-B"]
    imported = subprocess.run([*base, str(TOOL / "import_task_capsule.py"), "--capsule", "capsule.zip",
                               "--request", "request.json", "--output-dir", "out"],
                              cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert imported.returncode == 3, imported.stderr
    assert "eligibility_status=LOCAL_RECONCILIATION_UNAVAILABLE" in imported.stdout
    inspected = subprocess.run([*base, str(TOOL / "inspect_task_reconciliation.py"), "--capsule", "capsule.zip",
                                "--request", "request.json", *[arg for pair in zip(
                                    ("--inbox", "--report", "--summary", "--manifest"),
                                    ("out/" + name for name in OUT)) for arg in pair],
                                "--output", "out/inspection-summary.json"],
                               cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert inspected.returncode == 0, inspected.stderr
    assert "eligibility_agreement=AGREES" in inspected.stdout
