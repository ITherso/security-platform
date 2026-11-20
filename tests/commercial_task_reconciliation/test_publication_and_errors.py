"""Stage-and-rename publication without hard links, rollback, retry and fixed CLI error codes."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from exchange_contracts import InputError, json_bytes
from synthetic_fixtures import canonical_capsule, request
import import_task_capsule
import inspect_task_reconciliation
import reconciliation_manifest

OUT = ("task-inbox-record.json", "capsule-reconciliation-report.json", "capsule-reconciliation-summary.md",
       "manifest.json")
INSPECTION = "inspection-summary.json"
STAGE_PREFIX = ".task-reconciliation-"


def import_args(output_dir: str = "out", extra: list | None = None) -> list:
    return ["--capsule", "capsule.zip", "--request", "request.json", *(extra or []), "--output-dir", output_dir]


def inspect_args(directory: str = "out", output: str | None = None) -> list:
    return ["--capsule", "capsule.zip", "--request", "request.json",
            *(item for name, option in zip(OUT, ("--inbox", "--report", "--summary", "--manifest"))
              for item in (option, directory + "/" + name)),
            "--output", output or directory + "/" + INSPECTION]


def stages(directory: Path) -> list:
    return [path.name for path in directory.iterdir() if path.name.startswith(STAGE_PREFIX)]


def tree(directory: Path) -> dict:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir())}


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "request.json").write_bytes(json_bytes(request()))
    (tmp_path / "capsule.zip").write_bytes(canonical_capsule())
    return tmp_path


def _refuse_link(*_args, **_kwargs):
    raise OSError("hard links are not supported on this volume")


def test_publication_needs_no_hard_links_and_keeps_bytes(workdir, monkeypatch):
    assert import_task_capsule.main(import_args("baseline")) == 3
    assert inspect_task_reconciliation.main(inspect_args("baseline")) == 0
    monkeypatch.setattr(os, "link", _refuse_link)
    assert import_task_capsule.main(import_args("nolink")) == 3
    assert inspect_task_reconciliation.main(inspect_args("nolink")) == 0
    assert sorted(tree(workdir / "nolink")) == sorted((*OUT, INSPECTION))
    assert tree(workdir / "nolink") == tree(workdir / "baseline")
    for name in (*OUT, INSPECTION):
        assert (workdir / "nolink" / name).stat().st_nlink == 1
    assert stages(workdir) == [] and stages(workdir / "nolink") == []


@pytest.mark.parametrize("failing_call", [1, 3, 4])
def test_failure_during_staging_leaves_nothing_and_retry_succeeds(workdir, monkeypatch, capsys, failing_call):
    real_fsync, calls = os.fsync, []

    def flaky_fsync(descriptor):
        calls.append(descriptor)
        if len(calls) == failing_call:
            raise OSError("injected fsync failure")
        return real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", flaky_fsync)
    assert import_task_capsule.main(import_args()) == 1
    assert capsys.readouterr().err == "task_reconciliation: rejected; no reconciliation is claimed\n"
    assert not os.path.lexists(workdir / "out")
    assert stages(workdir) == []
    monkeypatch.setattr(os, "fsync", real_fsync)
    assert import_task_capsule.main(import_args()) == 3
    assert sorted(p.name for p in (workdir / "out").iterdir()) == sorted(OUT)
    assert inspect_task_reconciliation.main(inspect_args()) == 0


def test_failed_rename_leaves_nothing_and_retry_succeeds(workdir, monkeypatch):
    real_rename = os.rename

    def refuse_rename(*_args, **_kwargs):
        raise PermissionError("injected rename failure")

    monkeypatch.setattr(os, "rename", refuse_rename)
    assert import_task_capsule.main(import_args()) == 1
    assert not os.path.lexists(workdir / "out") and stages(workdir) == []
    monkeypatch.setattr(os, "rename", real_rename)
    assert import_task_capsule.main(import_args()) == 3
    published = tree(workdir / "out")
    monkeypatch.setattr(os, "rename", refuse_rename)
    assert inspect_task_reconciliation.main(inspect_args()) == 1
    assert tree(workdir / "out") == published and stages(workdir / "out") == []
    monkeypatch.setattr(os, "rename", real_rename)
    assert inspect_task_reconciliation.main(inspect_args()) == 0
    assert sorted(tree(workdir / "out")) == sorted((*OUT, INSPECTION))


def test_target_created_during_publication_is_reported_and_never_removed(workdir, monkeypatch, capsys):
    real_rename = os.rename

    def racing_rename(source, target):
        Path(target).mkdir()
        (Path(target) / "someone-else.txt").write_bytes(b"not created by this run")
        return real_rename(source, target)

    monkeypatch.setattr(os, "rename", racing_rename)
    assert import_task_capsule.main(import_args()) == 2
    assert capsys.readouterr().err == (
        "task_reconciliation: rejected: task_reconciliation_invalid_output_directory_must_be_new; nothing published\n")
    assert tree(workdir / "out") == {"someone-else.txt": b"not created by this run"}
    assert stages(workdir) == []


def test_cleanup_removes_only_files_this_run_wrote(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    real_fsync, calls = os.fsync, []

    def plant_then_fail(descriptor):
        calls.append(descriptor)
        if len(calls) == 2:
            stage = Path(tmp_path / stages(tmp_path)[0])
            (stage / "planted.txt").write_bytes(b"not written by the publisher")
            raise OSError("injected fsync failure")
        return real_fsync(descriptor)

    monkeypatch.setattr(os, "fsync", plant_then_fail)
    documents = {name: b"{}\n" for name in OUT}
    with pytest.raises(OSError):
        reconciliation_manifest.publish_outputs("out", documents)
    assert not os.path.lexists(tmp_path / "out")
    [stage] = stages(tmp_path)
    assert tree(tmp_path / stage) == {"planted.txt": b"not written by the publisher"}


def test_import_prints_fixed_rejection_codes(workdir, capsys):
    cases = [
        (import_args("nope/out"), "task_reconciliation_output_parent_missing"),
        (import_args("out", ["--local-register", "x.json"]), "task_reconciliation_invalid_partial_local_record_group"),
        (import_args(str(workdir / "absolute")), "task_reconciliation_publication_path_or_state_rejected"),
    ]
    for argv, code in cases:
        assert import_task_capsule.main(argv) == 2
        assert capsys.readouterr().err == "task_reconciliation: rejected: " + code + "; nothing published\n"
    assert not os.path.lexists(workdir / "nope") and not os.path.lexists(workdir / "out")
    (workdir / "out").mkdir()
    assert import_task_capsule.main(import_args()) == 2
    assert capsys.readouterr().err == (
        "task_reconciliation: rejected: task_reconciliation_invalid_output_directory_must_be_new; nothing published\n")
    assert list((workdir / "out").iterdir()) == []


def test_import_never_prints_an_unrepresentable_error_text(workdir, monkeypatch, capsys):
    def leaky(_args):
        raise InputError("C:/Users/someone/secret token=abc")

    monkeypatch.setattr(import_task_capsule, "load_inputs", leaky)
    assert import_task_capsule.main(import_args()) == 2
    err = capsys.readouterr().err
    assert err == "task_reconciliation: rejected: owner_code_unrepresentable; nothing published\n"
    assert "secret" not in err and "Users" not in err


def test_inspector_prints_disagreement_code_and_existing_output(workdir, capsys):
    assert import_task_capsule.main(import_args()) == 3
    capsys.readouterr()
    summary = workdir / "out" / OUT[2]
    original = summary.read_bytes()
    summary.write_bytes(original.replace(b"# Offline", b"# Online"))
    assert inspect_task_reconciliation.main(inspect_args()) == 2
    assert capsys.readouterr().err == (
        "task_reconciliation_inspection: outputs_disagree_with_independent_recomputation: "
        "task_reconciliation_inspection_disagreement_output_manifest_identity; nothing published\n")
    assert not os.path.lexists(workdir / "out" / INSPECTION)
    summary.write_bytes(original)
    assert inspect_task_reconciliation.main(inspect_args(output="nope/" + INSPECTION)) == 2
    assert capsys.readouterr().err == (
        "task_reconciliation_inspection: input_or_contract_rejected: "
        "task_reconciliation_inspection_output_parent_missing; nothing published\n")
    assert inspect_task_reconciliation.main(inspect_args()) == 0
    first = (workdir / "out" / INSPECTION).read_bytes()
    capsys.readouterr()
    assert inspect_task_reconciliation.main(inspect_args()) == 2
    assert capsys.readouterr().err == (
        "task_reconciliation_inspection: inspection_output_already_exists: "
        "task_reconciliation_invalid_inspection_output_must_be_new; nothing published\n")
    assert (workdir / "out" / INSPECTION).read_bytes() == first
    assert stages(workdir / "out") == []
