"""Byte-identical regeneration of the recorded offline Termivar demo chain (phases 16-44).

Phases 16-19 need only repository files and always run. The full chain needs SP_TERMIVAR_ROOT (Termivar
checkout at the pinned commit) and SP_PHASE30_DELIVERY_ZIP (the Phase30 delivery ZIP). A match only shows
deterministic regeneration of recorded demo bytes; it is not a review or approval of any finding.
On Windows without long-path support keep the pytest base temporary directory short (MAX_PATH).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "run_offline_chain.py"
EXPECTED = REPO / "examples" / "offline-chain" / "expected-sha256.json"
REPO_ONLY = ("16", "17", "18", "19")
ALL_PHASES = tuple(str(number) for number in range(16, 45))
TERMIVAR_ENV, ZIP_ENV = "SP_TERMIVAR_ROOT", "SP_PHASE30_DELIVERY_ZIP"


def load_runner():
    previous, sys.dont_write_bytecode = sys.dont_write_bytecode, True
    try:
        spec = importlib.util.spec_from_file_location("run_offline_chain_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def expected() -> dict:
    return json.loads(EXPECTED.read_text(encoding="utf-8"))


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(SCRIPT), *args], cwd=REPO, stdin=subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", timeout=1800, check=False)


def rows(stdout: str) -> dict:
    table = {}
    for line in stdout.splitlines():
        parts = line.split()
        if parts and parts[0] in ALL_PHASES:
            table[parts[0]] = parts
    return table


def assert_files_match(workspace: Path, phases) -> int:
    count = 0
    for phase in phases:
        for name, digest in expected()["phases"][phase].items():
            assert hashlib.sha256(workspace.joinpath(*name.split("/")).read_bytes()).hexdigest() == digest, name
            count += 1
    return count


def test_expected_pins():
    """The expected file covers every phase and pins the committed desk draft."""
    runner = load_runner()
    data = runner.load_expected()
    assert list(data["phases"]) == list(ALL_PHASES)
    assert sum(len(files) for files in data["phases"].values()) == 168
    assert data["inputs"]["termivar_commit"] == "6a2639348c2366d0bf71b9a34e5484d40aa393a3"
    draft = (REPO / "examples" / "offline-chain" / "termivar-decision-draft.json").read_bytes()
    assert hashlib.sha256(draft).hexdigest() == data["inputs"]["phase19_decision_draft_sha256"]
    assert json.loads(draft)["decisions"] == []
    assert [phase for phase, *_rest in runner.PHASES] == list(ALL_PHASES)


def test_repo_only_chain(tmp_path):
    """Phases 16-19 regenerate byte-identically from repository files; the rest are NOT_RUN."""
    workspace = tmp_path / "w"
    result = run("--workspace", str(workspace))
    assert result.returncode == 0, result.stdout + result.stderr
    table = rows(result.stdout)
    assert list(table) == list(ALL_PHASES)
    for phase in REPO_ONLY:
        assert table[phase][1] == "MATCHED"
        assert set(table[phase][2].split(",")) == {"0"}
    for phase in ALL_PHASES[4:]:
        assert table[phase][1:3] == ["NOT_RUN", "-"]
        assert table[phase][-1] == "termivar_root_not_supplied"
    assert "result=PARTIAL_MATCHED phases_matched=4 phases_failed=0 phases_not_run=25 files_matched=29/168" in result.stdout
    assert assert_files_match(workspace, REPO_ONLY) == 29
    assert (workspace / "security-platform" / "tools" / "commercial_handoff" / "assemble.py").is_file()
    assert not (workspace / "security-platform").is_symlink()
    assert not (workspace / "security-platform" / ".git").exists()


@pytest.mark.skipif(not (os.environ.get(TERMIVAR_ENV) and os.environ.get(ZIP_ENV)),
                    reason="full offline chain needs SP_TERMIVAR_ROOT (Termivar checkout at commit "
                           "6a2639348c2366d0bf71b9a34e5484d40aa393a3) and SP_PHASE30_DELIVERY_ZIP "
                           "(Termivar-Offline-Module-Candidates-phase30-2026-11-12.zip)")
def test_full_chain(tmp_path):
    """Phases 16-44 regenerate byte-identically with the pinned external inputs."""
    workspace = tmp_path / "w"
    result = run("--workspace", str(workspace), "--termivar-root", os.environ[TERMIVAR_ENV],
                 "--phase30-delivery-zip", os.environ[ZIP_ENV])
    assert result.returncode == 0, result.stdout + result.stderr
    table = rows(result.stdout)
    assert [table[phase][1] for phase in ALL_PHASES] == ["MATCHED"] * len(ALL_PHASES)
    assert "result=ALL_MATCHED phases_matched=29 phases_failed=0 phases_not_run=0 files_matched=168/168" in result.stdout
    assert assert_files_match(workspace, ALL_PHASES) == 168


def test_hash_mismatch(tmp_path, monkeypatch, capsys):
    """A differing hash fails the phase, stops the chain and exits 1."""
    runner = load_runner()
    data = runner.load_expected()
    name = "outputs/phase16-demo/manifest.json"
    data["phases"]["16"][name] = "0" * 64
    monkeypatch.setattr(runner, "load_expected", lambda: data)
    assert runner.main(["--workspace", str(tmp_path / "w")]) == 1
    output = capsys.readouterr().out
    table = rows(output)
    assert table["16"][1:4] == ["MISMATCH", "0", "3/4"]
    assert table["17"][1] == "NOT_RUN" and table["17"][-1] == "upstream_failed"
    assert "result=FAILED phases_matched=0 phases_failed=1" in output
    log = (tmp_path / "w" / "run-logs" / "phase16.log").read_text(encoding="utf-8")
    assert "sha256_differs " + name in log


def test_command_failure(tmp_path, monkeypatch, capsys):
    """A failing tool command is reported with its exit code and without paths."""
    runner = load_runner()
    broken = ("16", None, ("phase16-demo",),
              ("security-platform/tools/commercial_handoff/assemble.py --input missing-input.json"
               " --output-dir outputs/phase16-demo",))
    monkeypatch.setattr(runner, "PHASES", (broken, *runner.PHASES[1:]))
    assert runner.main(["--workspace", str(tmp_path / "w")]) == 1
    output = capsys.readouterr().out
    table = rows(output)
    assert table["16"][1] == "COMMAND_FAILED" and table["16"][2] != "0"
    assert table["17"][-1] == "upstream_failed"
    assert str(tmp_path) not in output and "missing-input.json" not in output


def test_refuses_non_empty_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "keep.txt").write_bytes(b"x")
    result = run("--workspace", str(workspace))
    assert result.returncode == 2
    assert result.stderr == "offline_chain: workspace_not_empty; nothing was run\n"
    assert [entry.name for entry in workspace.iterdir()] == ["keep.txt"]
    assert (workspace / "keep.txt").read_bytes() == b"x"


def test_refuses_workspace_inside_repository(capsys):
    target = REPO / (".offline-chain-refusal-" + uuid.uuid4().hex)
    assert load_runner().main(["--workspace", str(target)]) == 2
    assert capsys.readouterr().err == "offline_chain: workspace_inside_repository; nothing was run\n"
    assert not target.exists()


def test_refuses_wrong_external_inputs_before_writing(tmp_path, capsys):
    runner = load_runner()
    workspace = tmp_path / "workspace"
    not_a_checkout = tmp_path / "termivar"
    not_a_checkout.mkdir()
    assert runner.main(["--workspace", str(workspace), "--termivar-root", str(not_a_checkout)]) == 2
    assert capsys.readouterr().err == "offline_chain: termivar_root_commit_mismatch; nothing was run\n"
    fake_zip = tmp_path / "delivery.zip"
    fake_zip.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
    assert runner.main(["--workspace", str(workspace), "--phase30-delivery-zip", str(fake_zip)]) == 2
    assert capsys.readouterr().err == "offline_chain: phase30_delivery_zip_identity_mismatch; nothing was run\n"
    assert not workspace.exists()


def test_invalid_arguments_use_fixed_message():
    result = run("--workspace")
    assert result.returncode == 2
    assert result.stderr == "offline_chain: invalid_arguments\n"
