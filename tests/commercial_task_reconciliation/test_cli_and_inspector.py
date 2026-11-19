"""File-based CLI runs and independent-inspector disagreement detection."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

import pytest

from exchange_contracts import json_bytes
from synthetic_fixtures import WORKSPACE_OUTPUTS, canonical_capsule, canonical_members, request, zip_members
import import_task_capsule
import inspect_task_reconciliation

OUT = ("task-inbox-record.json", "capsule-reconciliation-report.json", "capsule-reconciliation-summary.md",
       "manifest.json")


def write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


def base_args(extra: list | None = None) -> list:
    return ["--capsule", "capsule.zip", "--request", "request.json", *(extra or [])]


def inspect_args(output: str = "out/inspection-summary.json", extra: list | None = None) -> list:
    return [*base_args(extra), "--inbox", "out/" + OUT[0], "--report", "out/" + OUT[1], "--summary", "out/" + OUT[2],
            "--manifest", "out/" + OUT[3], "--output", output]


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(tmp_path / "request.json", json_bytes(request()))
    return tmp_path


def test_cli_publishes_four_outputs_and_inspector_agrees(workdir, capsys):
    write(workdir / "capsule.zip", canonical_capsule())
    assert import_task_capsule.main([*base_args(), "--output-dir", "out"]) == 3   # unavailable -> non-eligible
    assert sorted(p.name for p in (workdir / "out").iterdir()) == sorted(OUT)
    assert "eligibility_status=LOCAL_RECONCILIATION_UNAVAILABLE" in capsys.readouterr().out
    assert inspect_task_reconciliation.main(inspect_args()) == 0
    inspection = json.loads((workdir / "out/inspection-summary.json").read_text(encoding="utf-8"))
    assert inspection["eligibility_agreement"] == "AGREES"
    assert inspection["regenerated_outputs"] == "BYTE_IDENTICAL"
    assert inspection["independently_derived_eligibility_status"] == "LOCAL_RECONCILIATION_UNAVAILABLE"
    assert len(inspection["checks"]) == 10


def test_cli_publishes_rejection_report_for_hostile_capsule(workdir):
    members = canonical_members()
    write(workdir / "capsule.zip", zip_members(dict(members, **{"README.txt": b"tampered"})))
    assert import_task_capsule.main([*base_args(), "--output-dir", "out"]) == 3
    report = json.loads((workdir / "out" / OUT[1]).read_text(encoding="utf-8"))
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    assert inspect_task_reconciliation.main(inspect_args()) == 0


def test_cli_rejects_bad_arguments_and_existing_output(workdir):
    write(workdir / "capsule.zip", canonical_capsule())
    assert import_task_capsule.main([*base_args(["--local-register", "x.json"]), "--output-dir", "out"]) == 2
    assert not (workdir / "out").exists()
    (workdir / "out").mkdir()
    assert import_task_capsule.main([*base_args(), "--output-dir", "out"]) == 2
    assert list((workdir / "out").iterdir()) == []
    with pytest.raises(SystemExit) as error:
        import_task_capsule.main(["--capsule", "capsule.zip"])
    assert error.value.code == 2


def test_cli_refuses_oversized_capsule_file_without_report(workdir):
    write(workdir / "capsule.zip", b"\0" * (128 * 1024 + 1))
    assert import_task_capsule.main([*base_args(), "--output-dir", "out"]) == 2
    assert not (workdir / "out").exists()


def _rewrite_manifest(workdir: Path) -> None:
    manifest_path = workdir / "out" / OUT[3]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest["files"]:
        raw = (workdir / "out" / item["name"]).read_bytes()
        item["bytes"], item["sha256"] = len(raw), hashlib.sha256(raw).hexdigest()
    manifest_path.write_bytes(json_bytes(manifest))


@pytest.mark.parametrize("tamper", ["status", "finding", "inbox_stage", "summary", "capsule_swap", "comparison"])
def test_inspector_detects_disagreement(workdir, tamper):
    write(workdir / "capsule.zip", canonical_capsule())
    assert import_task_capsule.main([*base_args(), "--output-dir", "out"]) == 3
    out = workdir / "out"
    report_path, inbox_path = out / OUT[1], out / OUT[0]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    inbox = json.loads(inbox_path.read_text(encoding="utf-8"))
    if tamper == "status":
        # A coherent-looking upgrade: report, inbox and manifest all claim eligibility.
        report["eligibility"].update(status="STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW",
                                     manual_review="ELIGIBLE_FOR_MANUAL_REVIEW",
                                     basis_finding_ids=["P44-MANUAL_REVIEW_REQUIRED:capsule"])
        inbox.update(eligibility_status="STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW",
                     manual_review="ELIGIBLE_FOR_MANUAL_REVIEW", lifecycle_stage="QUARANTINED_AWAITING_MANUAL_REVIEW")
        manifest = json.loads((out / OUT[3]).read_text(encoding="utf-8"))
        manifest["eligibility_status"] = "STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW"
        (out / OUT[3]).write_bytes(json_bytes(manifest))
    elif tamper == "finding":
        report["findings"] = [f for f in report["findings"] if f["rule"] != "LOCAL_RECORDS_NOT_SUPPLIED"]
        report["eligibility"]["basis_finding_ids"] = []
    elif tamper == "inbox_stage":
        inbox["admitted_tasks"][0]["candidate_id"] = "SYNTH0999"
    elif tamper == "comparison":
        report["local_reconciliation"]["comparisons"] = report["local_reconciliation"]["comparisons"][1:]
    if tamper in ("status", "finding", "inbox_stage", "comparison"):
        report_path.write_bytes(json_bytes(report))
        inbox_path.write_bytes(json_bytes(inbox))
    if tamper == "summary":
        (out / OUT[2]).write_bytes((out / OUT[2]).read_bytes().replace(b"# Offline", b"# Online"))
    if tamper == "capsule_swap":
        from synthetic_fixtures import synthetic_envelope

        write(workdir / "capsule.zip", canonical_capsule(synthetic_envelope(reference="synthetic-other")))
    _rewrite_manifest(workdir)
    assert inspect_task_reconciliation.main(inspect_args()) == 2
    assert not (out / "inspection-summary.json").exists()


REAL_42 = ("deferred-intake-register.json", "intake-classification.json", "intake-source-receipt.json",
           "intake-summary.md", "manifest.json")
REAL_43 = ("task-exchange-capsule.zip", "task-exchange-index.json", "task-exchange-source-receipt.json",
           "task-exchange-summary.md", "manifest.json")


@pytest.mark.skipif(not (WORKSPACE_OUTPUTS / "phase43-task-exchange" / REAL_43[0]).exists(),
                    reason="workspace Phase42/Phase43 outputs are not present")
def test_real_phase43_capsule_copies_reconcile(tmp_path, monkeypatch):
    """Read-only copies of the existing outputs; the originals are never opened for writing."""
    for directory, names in (("phase42-deferred-intake", REAL_42), ("phase43-task-exchange", REAL_43)):
        for name in names:
            target = tmp_path / directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(WORKSPACE_OUTPUTS / directory / name, target)
    capsule = (tmp_path / "phase43-task-exchange" / REAL_43[0]).read_bytes()
    index = (tmp_path / "phase43-task-exchange" / REAL_43[1]).read_bytes()
    register = (tmp_path / "phase42-deferred-intake" / REAL_42[0]).read_bytes()
    mode = "PHASE42_TASK_RECORDS_AND_PHASE43_DISCLOSURE_RECORDS"
    write(tmp_path / "request.json", json_bytes(request(mode, hashlib.sha256(register).hexdigest(),
                                                        hashlib.sha256(index).hexdigest(), "integration-copy")))
    write(tmp_path / "capsule.zip", capsule)
    monkeypatch.chdir(tmp_path)
    local_args = []
    for option, name in zip(("local-register", "local-classification", "local-intake-receipt", "local-intake-summary",
                             "local-intake-manifest"), REAL_42):
        local_args += ["--" + option, "phase42-deferred-intake/" + name]
    for option, name in zip(("disclosed-capsule", "disclosed-index", "disclosed-receipt", "disclosed-summary",
                             "disclosed-manifest"), REAL_43):
        local_args += ["--" + option, "phase43-task-exchange/" + name]
    assert import_task_capsule.main([*base_args(local_args), "--output-dir", "out"]) == 0
    report = json.loads((tmp_path / "out" / OUT[1]).read_text(encoding="utf-8"))
    assert report["eligibility"]["status"] == "STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW"
    assert {r["result"] for r in report["local_reconciliation"]["comparisons"]} == {"MATCH"}
    assert report["capsule_identity"]["represented_tasks"][0]["task_id"] == "F0001"
    assert inspect_task_reconciliation.main(inspect_args(extra=local_args)) == 0
