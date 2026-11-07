import json
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError
import pytest

from tools.policy_revision_lab import cli
from tools.policy_revision_lab.models import LabHead
from security_platform.policy_contracts.preconditions import (PolicyBinding, PreconditionCheck,
    PreconditionExpectation, PreconditionObservation, check_preconditions)


def parameters(command, location, binding_file, hbf_source, output):
    return [command, "--backend", "endpoint", "--location", str(location),
            "--binding-file", str(binding_file), "--hbf-root", str(hbf_source), "--output", str(output)]


def test_endpoint_cli_exact_retry_and_unbound_report(private_parent, hbf_source, lab_binding, lab_bundle, tmp_path, capsys):
    location = private_parent / "cli-store"
    binding_file, output, request_file = tmp_path / "binding.json", tmp_path / "output.json", tmp_path / "append.json"
    binding_file.write_text(lab_binding.model_dump_json(), encoding="utf-8")
    assert cli.main(parameters("init", location, binding_file, hbf_source, output)) == 0
    head = json.loads(output.read_bytes())
    assert head["revision"] == head["staged_revision"] == 0
    request = {"binding": lab_binding.model_dump(mode="json"), "operation_id": str(uuid4()),
        "expected_lineage": head["lineage"], "expected_revision": 0, "base_fingerprint": None,
        "bundle": lab_bundle.model_dump(mode="json")}
    request_file.write_text(json.dumps(request), encoding="utf-8")
    append_args = parameters("append", location, binding_file, hbf_source, output) + ["--input", str(request_file)]
    assert cli.main(append_args) == 0
    first = json.loads(output.read_bytes())
    assert first["staged_revision"] == 1 and first["draft_revision"] is None
    second_request = {**request, "operation_id": str(uuid4()), "expected_revision": 1,
                      "base_fingerprint": first["bundle_fingerprint"]}
    request_file.write_text(json.dumps(second_request), encoding="utf-8")
    assert cli.main(append_args) == 0
    assert json.loads(output.read_bytes())["staged_revision"] == 2
    request_file.write_text(json.dumps(request), encoding="utf-8")
    assert cli.main(append_args) == 0
    assert json.loads(output.read_bytes()) == first  # Historical commit, never renamed current head.
    assert cli.main(parameters("report", location, binding_file, hbf_source, output)) == 0
    report = json.loads(output.read_bytes())
    assert report["head"]["staged_revision"] == 2 and report["rollout_status"] == "would_pause"
    assert report["controller_desired_revision"] is report["device_policy_revision"] is None
    assert report["execution_authorized"] is False and report["verification"] == "not_performed"
    assert "precondition_evidence_missing" in report["blockers"]
    before = output.read_bytes()
    bad = {**second_request, "operation_id": str(uuid4()),
           "binding": {**request["binding"], "tenant_id": str(uuid4())}}
    request_file.write_text(json.dumps(bad), encoding="utf-8")
    assert cli.main(append_args) == 1 and output.read_bytes() == before
    assert "bundle" not in capsys.readouterr().out


def test_lab_report_cannot_populate_operational_revision_fields(hbf_adapter, lab_binding, lab_bundle):
    from tools.policy_revision_lab.models import make_head
    head = make_head(lab_binding, str(uuid4()), 0, hbf_adapter)
    report = cli.lab_report(head)
    for field in ("controller_desired_revision", "device_policy_revision"):
        with pytest.raises(ValidationError):
            cli.LabReport.model_validate({**report.model_dump(mode="python"), field: {"revision": "1", "lineage": "lab"}})
        with pytest.raises(ValidationError):
            cli.lab_report(head.model_copy(update={field: {"revision": "1", "lineage": "lab"}}))
    for change in ({"execution_authorized": True}, {"verification": "verified"}, {"blockers": []}):
        with pytest.raises(ValidationError):
            cli.LabReport.model_validate({**report.model_dump(mode="python"), **change})
    binding = PolicyBinding(tenant_id=lab_binding.tenant_id, device_id=lab_binding.subject_id,
                            product_id="hostbasedfirewall", enforcement_scope="packet_policy")
    bundle_fp = "sp-hbf-bundle-v1:sha256:" + "a" * 64
    expected = PreconditionExpectation(binding=binding, controller_revision=None, endpoint_revision=None,
        base_fingerprint=bundle_fp, candidate_fingerprint=bundle_fp, adapter_fingerprint=head.adapter_fingerprint,
        preview_fingerprint="sp-hbf-preview-v1:sha256:" + "d" * 64)
    observed = PreconditionObservation(binding=binding, controller_revision=report.controller_desired_revision,
        endpoint_revision=report.device_policy_revision, base_fingerprint=bundle_fp, candidate_fingerprint=bundle_fp,
        adapter_fingerprint=head.adapter_fingerprint, preview_fingerprint=expected.preview_fingerprint)
    result = check_preconditions(PreconditionCheck(expected=expected, observed=observed))
    assert result.status == "precondition_evidence_missing" and not result.execution_authorized


def test_cli_refuses_output_inside_hbf_source_before_store_creation(private_parent, hbf_source, lab_binding, tmp_path):
    location = private_parent / "must-not-exist"
    binding_file = tmp_path / "binding.json"
    binding_file.write_text(lab_binding.model_dump_json(), encoding="utf-8")
    assert cli.main(parameters("init", location, binding_file, hbf_source, hbf_source / "unwanted-report.json")) == 1
    assert not location.exists() and not (hbf_source / "unwanted-report.json").exists()


def test_windows_cli_validates_only_format(tmp_path):
    fixture = Path(__file__).resolve().parents[1] / "fixtures/policy_revision_lab/windows-not-run.json"
    output = tmp_path / "windows-format.json"
    assert cli.main(["windows-report", "--input", str(fixture), "--output", str(output)]) == 0
    result = json.loads(output.read_bytes())
    assert result["reported_status_counts"]["NOT_RUN"] == 12
    assert result["windows_acceptance"] == "not_evaluated" and result["real_acceptance_established"] is False


def test_unexpected_driver_error_is_fixed_without_connection_or_payload(tmp_path, monkeypatch, capsys):
    from tools.policy_revision_lab import windows_evidence
    fixture = Path(__file__).resolve().parents[1] / "fixtures/policy_revision_lab/windows-not-run.json"
    output = tmp_path / "result.json"
    output.write_text("previous", encoding="utf-8")
    def fail(value):
        raise RuntimeError("postgresql://private-user:private-password@localhost/private-policy")
    monkeypatch.setattr(windows_evidence, "validate_windows_evidence", fail)
    assert cli.main(["windows-report", "--input", str(fixture), "--output", str(output)]) == 1
    assert capsys.readouterr().err == "lab_operation_failed\n" and output.read_text() == "previous"


@pytest.mark.parametrize("flag", ["--apply", "--push", "--execute", "--remote-url", "--real-device"])
def test_no_hidden_execution_or_remote_device_mode(flag):
    with pytest.raises(SystemExit) as result:
        cli.main(["read", "--backend", "endpoint", "--location", "lab", "--binding-file", "binding.json",
                  "--hbf-root", "HBF", "--output", "output.json", flag])
    assert result.value.code == 2
