import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from security_platform.policy_contracts import cli


ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def hbf_root():
    explicit = os.environ.get("SP_HBF_SOURCE")
    candidates = [Path(explicit)] if explicit is not None else [ROOT.parent / "HostBasedFirewall-main", ROOT.parent / "HostBasedFirewall"]
    source = next((path for path in candidates if (path / "src/policy_engine.py").is_file()), None)
    if source is None:
        if explicit is not None:
            pytest.fail("SP_HBF_SOURCE does not identify the explicit HBF source checkout", pytrace=False)
        pytest.skip("Sibling HBF source unavailable; real CLI evaluator acceptance is not checked in this standalone package")
    return source


def example():
    return json.loads((ROOT / "examples/policy-preview.json").read_text(encoding="utf-8"))


def invoke(tmp_path, value, *, adapter=True, hbf_root=None):
    source, target = tmp_path / "request.json", tmp_path / "result.json"
    source.write_text(json.dumps(value), encoding="utf-8")
    args = ["preview", "--input", str(source), "--output", str(target)]
    if adapter:
        assert hbf_root is not None
        args.extend(["--hbf-root", str(hbf_root)])
    return cli.main(args), target, source


@pytest.mark.parametrize("field,value", [("schema_version", True), ("schema_version", "1"),
                                       ("execution_authorized", True), ("apply", True),
                                       ("verified", True), ("command", "anything")])
def test_cli_rejects_untrusted_authority_fields_without_output(tmp_path, capsys, field, value):
    request = example()
    request[field] = value
    code, target, _ = invoke(tmp_path, request, adapter=False)
    captured = capsys.readouterr()
    assert code == 1 and not target.exists()
    assert captured.out == "" and captured.err == "policy_input_invalid\n"
    assert "10.1.2.3" not in captured.err


def test_cli_absent_evaluator_is_explicit_blocked_not_approximation(tmp_path, capsys):
    code, target, _ = invoke(tmp_path, example(), adapter=False)
    assert code == 0
    result = json.loads(target.read_bytes())
    assert result["status"] == "blocked" and "evaluator_unavailable" in result["blocker_codes"]
    assert result["preview_fingerprint"] is None and result["results"] == []
    assert result["execution_authorized"] is False
    assert capsys.readouterr().out == '{"status":"output_written","execution_authorized":false}\n'


def test_cli_preview_uses_real_evaluator_and_only_explicit_output(tmp_path, hbf_root):
    request = example()
    original = copy.deepcopy(request)
    code, target, source = invoke(tmp_path, request, hbf_root=hbf_root)
    assert code == 0 and request == original
    result = json.loads(target.read_bytes())
    assert result["status"] == "ok", result.get("blocker_codes")
    assert result["results"][0]["base"]["decision"]["action"] == "ALLOW"
    assert result["results"][0]["candidate"]["decision"]["action"] == "DENY"
    assert result["execution_authorized"] is False and result["verification"] == "not_performed"
    assert json.loads(source.read_bytes()) == original
    assert {path.name for path in tmp_path.iterdir()} == {"request.json", "result.json"}


def test_cli_missing_profile_is_not_default_public(tmp_path, hbf_root):
    request = example()
    del request["scenarios"][0]["network_profile"]
    code, target, _ = invoke(tmp_path, request, hbf_root=hbf_root)
    assert code == 0
    result = json.loads(target.read_bytes())
    assert result["status"] == "blocked" and "insufficient_context" in result["blocker_codes"]
    assert not result["results"] and result["preview_fingerprint"] is None


def test_actual_cli_subprocess_never_logs_policy_contents(tmp_path):
    source, target = tmp_path / "request.json", tmp_path / "result.json"
    source.write_text(json.dumps(example()), encoding="utf-8")
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    result = subprocess.run([sys.executable, "-B", "-m", "security_platform.policy_contracts.cli", "preview",
        "--input", str(source), "--output", str(target)], cwd=ROOT, env=environment,
        capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout == '{"status":"output_written","execution_authorized":false}\n'
    assert result.stderr == "" and "10.1.2.3" not in result.stdout
    assert json.loads(target.read_bytes())["status"] == "blocked"


@pytest.mark.parametrize("flag", ["--apply", "--push", "--execute", "--dry-run=false"])
def test_cli_has_no_hidden_execution_switch(flag):
    with pytest.raises(SystemExit) as caught:
        cli.main(["preview", "--input", "input.json", "--output", "output.json", flag])
    assert caught.value.code == 2


def test_cli_cas_example_keeps_missing_revision_evidence(tmp_path):
    target = tmp_path / "cas.json"
    assert cli.main(["check-preconditions", "--input", str(ROOT / "examples/policy-preconditions.json"),
                     "--output", str(target)]) == 0
    value = json.loads(target.read_bytes())
    assert value["status"] == "precondition_evidence_missing"
    assert set(value["missing_evidence"]) == {"controller_revision", "endpoint_revision"}
    assert value["execution_authorized"] is False


def test_cli_rollout_example_pauses_without_creating_job(tmp_path):
    target = tmp_path / "rollout.json"
    assert cli.main(["validate-rollout", "--input", str(ROOT / "examples/policy-rollout.json"),
        "--evaluation-time", "2030-01-01T00:30:00Z", "--output", str(target)]) == 0
    value = json.loads(target.read_bytes())
    assert value["status"] == "would_pause"
    assert value["execution_plan"] == "not_created" and value["next_batch"] is None
    assert "precondition_evidence_missing" in value["blocker_codes"]


PREVIOUS = "previous-result"


def keep_existing(tmp_path):
    target = tmp_path / "result.json"
    target.write_text(PREVIOUS, encoding="utf-8")
    return target


def assert_rejected_unchanged(captured, code, target, *secrets):
    assert captured.out == "" and captured.err == code + "\n"
    assert target.read_text(encoding="utf-8") == PREVIOUS
    assert {path.name for path in target.parent.iterdir() if path.name.startswith(".security-policy-")} == set()
    assert all(secret not in captured.err for secret in ("10.1.2.3", "NOPE", *secrets))


def fake_hbf_root(tmp_path, layout):
    root = tmp_path / "fake-hbf"
    source = root if layout == "flat" else root / "src"
    source.mkdir(parents=True)
    for name in ("config_store.py", "document_limits.py", "policy_objects.py", "policy_engine.py"):
        (source / name).write_text("VALUE = 1\n", encoding="utf-8")
    if layout == "oversized":
        (source / "config_store.py").write_bytes(b"#" * (256 * 1024 + 1))
    elif layout == "syntax":
        (source / "policy_objects.py").write_text("def broken(:\n", encoding="utf-8")
    elif layout == "import":
        (source / "config_store.py").write_text("import socket\n", encoding="utf-8")
    elif layout == "incomplete":
        (source / "policy_engine.py").unlink()
    return root


@pytest.mark.parametrize("layout", ["missing", "flat", "oversized", "syntax", "import", "incomplete"])
def test_cli_explicit_unloadable_hbf_root_exits_1_without_output(tmp_path, capsys, layout):
    root = tmp_path / "missing-hbf" if layout == "missing" else fake_hbf_root(tmp_path, layout)
    target = keep_existing(tmp_path)
    code, _, _ = invoke(tmp_path, example(), hbf_root=root)
    assert code == 1
    assert_rejected_unchanged(capsys.readouterr(), "evaluator_unavailable", target, str(root), root.name)
    fresh = tmp_path / "fresh.json"
    assert cli.main(["preview", "--input", str(tmp_path / "request.json"), "--output", str(fresh),
                     "--hbf-root", str(root)]) == 1
    assert not fresh.exists() and capsys.readouterr().err == "evaluator_unavailable\n"


def test_cli_real_hbf_root_at_wrong_level_exits_1_and_keeps_output(tmp_path, capsys, hbf_root):
    target = keep_existing(tmp_path)
    code, _, _ = invoke(tmp_path, example(), hbf_root=hbf_root / "src")
    assert code == 1
    assert_rejected_unchanged(capsys.readouterr(), "evaluator_unavailable", target, str(hbf_root))


def hbf_invalid_bundle(request):
    request["candidate"]["policies"]["policies"][0]["src_zones"] = ["NOPE"]


def duplicate_scenario(request):
    request["scenarios"].append(copy.deepcopy(request["scenarios"][0]))


def ambiguous_zone(request):
    request["candidate"]["ordered_zones"].append({"name": "LAB", "cidrs": ["10.0.0.0/8"]})


@pytest.mark.parametrize("mutate,blocker", [(hbf_invalid_bundle, "invalid_policy_bundle"),
                                            (duplicate_scenario, "invalid_scenario"),
                                            (ambiguous_zone, "ambiguous_equal_prefix_zones")])
def test_cli_input_blocker_keeps_existing_good_preview(tmp_path, capsys, hbf_root, mutate, blocker):
    code, target, _ = invoke(tmp_path, example(), hbf_root=hbf_root)
    assert code == 0
    good = target.read_bytes()
    assert json.loads(good)["status"] == "ok"
    capsys.readouterr()
    request = example()
    mutate(request)
    code, _, _ = invoke(tmp_path, request, hbf_root=hbf_root)
    captured = capsys.readouterr()
    assert code == 1 and captured.out == "" and captured.err == blocker + "\n"
    assert target.read_bytes() == good
    assert "10.1.2.3" not in captured.err and "NOPE" not in captured.err and "LAB" not in captured.err


def test_cli_no_hbf_root_still_writes_blocked_evaluator_unavailable(tmp_path, capsys):
    target = keep_existing(tmp_path)
    code, _, _ = invoke(tmp_path, example(), adapter=False)
    captured = capsys.readouterr()
    assert code == 0 and captured.err == ""
    assert captured.out == '{"status":"output_written","execution_authorized":false}\n'
    result = json.loads(target.read_bytes())
    assert result["status"] == "blocked" and result["blocker_codes"] == ["evaluator_unavailable"]
    assert result["results"] == [] and result["execution_authorized"] is False


@pytest.mark.parametrize("blocker,with_root,expected", [
    ("invalid_policy_bundle", True, 1), ("invalid_scenario", True, 1), ("input_limit_exceeded", True, 1),
    ("ambiguous_equal_prefix_zones", True, 1), ("evaluator_unavailable", True, 1),
    ("evaluator_unavailable", False, 0), ("insufficient_context", True, 0),
    ("invalid_evaluator_result", True, 0), ("evaluator_failed", True, 0)])
def test_cli_blocker_exit_classification(tmp_path, capsys, monkeypatch, blocker, with_root, expected):
    from security_platform.policy_contracts import hbf_bridge, preview
    from security_platform.policy_contracts.models import PreviewOutcome
    monkeypatch.setattr(hbf_bridge, "load_hbf_adapter", lambda root: object())
    monkeypatch.setattr(preview, "preview_policy", lambda *args, **kwargs:
                        PreviewOutcome(status="blocked", blocker_codes=(blocker,)))
    target = keep_existing(tmp_path)
    code, _, _ = invoke(tmp_path, example(), adapter=with_root, hbf_root=tmp_path if with_root else None)
    captured = capsys.readouterr()
    assert code == expected
    if expected:
        assert_rejected_unchanged(captured, blocker, target)
    else:
        assert captured.err == "" and json.loads(target.read_bytes())["blocker_codes"] == [blocker]


def test_cli_preview_help_names_trusted_local_code_not_review(capsys):
    with pytest.raises(SystemExit) as caught:
        cli.main(["--help"])
    assert caught.value.code == 0
    with pytest.raises(SystemExit) as caught:
        cli.main(["preview", "--help"])
    assert caught.value.code == 0
    text = " ".join(capsys.readouterr().out.split())
    assert "reviewed" not in text and "verified" not in text
    assert "trusted local code" in text and "evaluator_unavailable" in text


def test_cli_rollout_invalid_time_never_replaces_output(tmp_path, capsys):
    target = tmp_path / "rollout.json"
    target.write_text("previous-result", encoding="utf-8")
    assert cli.main(["validate-rollout", "--input", str(ROOT / "examples/policy-rollout.json"),
        "--evaluation-time", "use-system-clock", "--output", str(target)]) == 1
    assert target.read_text() == "previous-result"
    assert capsys.readouterr().err == "policy_input_invalid\n"
