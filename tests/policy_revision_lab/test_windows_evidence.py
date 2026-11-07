import builtins
import ctypes
import json
import os
from pathlib import Path
import socket
import subprocess
import time

from pydantic import ValidationError
import pytest

from tools.policy_revision_lab.windows_evidence import (
    WindowsCase, WindowsEvidenceReport, WindowsEvidenceValidation, validate_windows_evidence,
)


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures/policy_revision_lab"


def fixture(name="windows-not-run.json"):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_real_plan_has_only_not_run_and_no_invented_host_facts():
    value = fixture()
    report = WindowsEvidenceReport.model_validate(value)
    result = validate_windows_evidence(report)
    assert result.status == "format_consistent" and result.reported_status_counts.NOT_RUN == 12
    assert result.reported_status_counts.PASS == 0 and not result.real_acceptance_established
    for case in report.cases:
        assert case.status == "NOT_RUN" and case.observed is None and case.reviewer is None
        assert case.accounts == () and case.evidence_refs == ()
        assert case.artifact_sha256 is case.windows_build is case.architecture is case.environment is None


@pytest.mark.parametrize("origin", ["synthetic", "real"])
def test_reported_pass_hash_signature_and_self_report_never_establish_acceptance(origin):
    value = fixture("windows-synthetic-format.json")
    value["evidence_origin"] = origin
    result = validate_windows_evidence(value)
    assert result.reported_status_counts.PASS == 1
    assert result.status == "format_consistent" and result.validation_scope == "format_consistency_only"
    assert result.windows_acceptance == result.authorization == "not_evaluated"
    assert result.independent_verification == "not_performed"
    assert result.reviewer_identity == "not_authenticated"
    assert not result.execution_authorized and not result.real_acceptance_established


@pytest.mark.parametrize("field", ["source_commit", "artifact_sha256", "windows_build", "architecture",
    "environment", "observed", "accounts", "evidence_refs"])
def test_reported_result_requires_complete_reported_context(field):
    value = fixture("windows-synthetic-format.json")
    value["cases"][0][field] = [] if field in ("accounts", "evidence_refs") else None
    with pytest.raises(ValidationError):
        validate_windows_evidence(value)


@pytest.mark.parametrize("field,value", [("observed", "invented observation"), ("reviewer", "invented reviewer"),
    ("review_status", "reported_reviewed"), ("evidence_refs", [{"reference": "case/log.txt", "sha256": "a" * 64, "kind": "log"}])])
def test_not_run_refuses_observation_review_and_evidence_claims(field, value):
    report = fixture()
    report["cases"][0][field] = value
    with pytest.raises(ValidationError):
        validate_windows_evidence(report)


@pytest.mark.parametrize("version", [True, False, 1.0, "1", 2])
def test_schema_version_is_exact_integer_one(version):
    value = fixture()
    value["schema_version"] = version
    with pytest.raises(ValidationError):
        validate_windows_evidence(value)


@pytest.mark.parametrize("level,field", [("report", "verified"), ("report", "execution_authorized"),
    ("case", "approved"), ("case", "apply"), ("case", "command"), ("case", "verified")])
def test_unknown_authority_fields_are_rejected(level, field):
    value = fixture()
    (value if level == "report" else value["cases"][0])[field] = True
    with pytest.raises(ValidationError):
        validate_windows_evidence(value)


def test_duplicate_case_ids_and_conflicting_hashes_are_rejected():
    value = fixture()
    value["cases"][1]["case_id"] = value["cases"][0]["case_id"]
    with pytest.raises(ValidationError, match="duplicate_windows_case_id"):
        validate_windows_evidence(value)
    value = fixture("windows-synthetic-format.json")
    duplicate = {**value["cases"][0]["evidence_refs"][1], "sha256": "a" * 64}
    value["cases"][0]["evidence_refs"].append(duplicate)
    with pytest.raises(ValidationError, match="conflicting_reported_evidence_hash"):
        validate_windows_evidence(value)


@pytest.mark.parametrize("reference", ["../outside.log", "case/../outside.log", "/absolute.log", "C:/file.log",
    "https://example.invalid/evidence", "case//log.txt", "case/./log.txt"])
def test_evidence_references_are_lexical_relative_strings(reference):
    value = fixture("windows-synthetic-format.json")
    value["cases"][0]["evidence_refs"][0]["reference"] = reference
    with pytest.raises(ValidationError):
        validate_windows_evidence(value)


def test_copied_or_constructed_models_are_revalidated():
    report = WindowsEvidenceReport.model_validate(fixture())
    for invalid in (report.model_copy(update={"schema_version": True}),
                    report.model_copy(update={"execution_authorized": True}),
                    report.model_copy(update={"cases": (report.cases[0].model_copy(update={"status": "PASS"}),)}),
                    WindowsEvidenceReport.model_construct(schema_version=True, evidence_origin="real", cases=report.cases)):
        with pytest.raises(ValidationError):
            validate_windows_evidence(invalid)


@pytest.mark.parametrize("sid,context", [("S-1-5-18", "standard_user"), ("S-1-5-21-1000", "SYSTEM"),
    ("S-1-5-4294967296", "standard_user"), ("S-1-281474976710656-1", "standard_user"),
    ("S-1-5-01", "standard_user")])
def test_sid_number_bounds_and_well_known_system_context_are_consistent(sid, context):
    value = fixture("windows-synthetic-format.json")
    value["cases"][0]["accounts"][0].update(sid=sid, context=context)
    with pytest.raises(ValidationError):
        validate_windows_evidence(value)


def test_deep_immutability_and_input_independence():
    value = fixture()
    report = WindowsEvidenceReport.model_validate(value)
    value["cases"][0]["preconditions"].append("changed")
    assert len(report.cases[0].preconditions) == 1
    with pytest.raises(ValidationError):
        report.cases[0].status = "PASS"
    assert isinstance(report.cases, tuple) and isinstance(report.cases[0].preconditions, tuple)


@pytest.mark.parametrize("field", ["execution_authorized", "real_acceptance_established"])
@pytest.mark.parametrize("value", [True, 0, 1, "false"])
def test_output_guards_are_exact_false(field, value):
    result = validate_windows_evidence(fixture()).model_dump()
    result[field] = value
    with pytest.raises(ValidationError):
        WindowsEvidenceValidation.model_validate(result)


def test_bounded_cases_and_evidence():
    value = fixture()
    value["cases"] = [{**value["cases"][0], "case_id": f"CASE-{i}"} for i in range(65)]
    with pytest.raises(ValidationError):
        validate_windows_evidence(value)
    value = fixture("windows-synthetic-format.json")
    value["cases"][0]["evidence_refs"] *= 12
    with pytest.raises(ValidationError):
        validate_windows_evidence(value)


def test_no_file_hash_signature_os_network_environment_or_clock_checks(monkeypatch):
    value = fixture("windows-synthetic-format.json")
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("Windows format validation attempted ambient access")
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(Path, "open", forbidden)
        patch.setattr(Path, "read_bytes", forbidden)
        patch.setattr(Path, "stat", forbidden)
        patch.setattr(os, "stat", forbidden)
        patch.setattr(os, "getenv", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(socket, "getaddrinfo", forbidden)
        patch.setattr(subprocess, "Popen", forbidden)
        patch.setattr(time, "time", forbidden)
        patch.setattr(time, "monotonic", forbidden)
        patch.setattr(ctypes, "CDLL", forbidden)
        if hasattr(ctypes, "WinDLL"):
            patch.setattr(ctypes, "WinDLL", forbidden)
        result = validate_windows_evidence(value)
    assert attempts == [] and result.windows_acceptance == "not_evaluated"
