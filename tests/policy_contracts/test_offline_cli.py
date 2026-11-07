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


def test_cli_rollout_invalid_time_never_replaces_output(tmp_path, capsys):
    target = tmp_path / "rollout.json"
    target.write_text("previous-result", encoding="utf-8")
    assert cli.main(["validate-rollout", "--input", str(ROOT / "examples/policy-rollout.json"),
        "--evaluation-time", "use-system-clock", "--output", str(target)]) == 1
    assert target.read_text() == "previous-result"
    assert capsys.readouterr().err == "policy_input_invalid\n"
