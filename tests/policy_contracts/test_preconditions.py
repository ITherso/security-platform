from copy import deepcopy
import builtins
import os
import socket
import time

from pydantic import ValidationError
import pytest

from security_platform.policy_contracts.errors import PolicyContractError
from security_platform.policy_contracts.preconditions import (PolicyReceipt, PreconditionCheck,
    PreconditionResult, check_preconditions, validate_receipt)

TENANT = "00000000-0000-4000-8000-000000000001"
DEVICE = "00000000-0000-4000-8000-000000000002"
PLAN = "00000000-0000-4000-8000-000000000003"
OTHER = "00000000-0000-4000-8000-000000000004"
NOW = "2030-01-01T00:10:00Z"
START = "2030-01-01T00:00:00Z"
END = "2030-01-01T01:00:00Z"


def fingerprint(kind, value="a"):
    return "sp-hbf-" + kind + "-v1:sha256:" + value * 64


def expectation(device=DEVICE):
    return {"binding": {"tenant_id": TENANT, "device_id": device, "product_id": "hostbasedfirewall",
                        "enforcement_scope": "packet_policy"},
        "controller_revision": {"revision": "controller-1", "lineage": "controller-lineage"},
        "endpoint_revision": {"revision": "policy-1", "lineage": "device-policy-lineage"},
        "base_fingerprint": fingerprint("bundle"), "candidate_fingerprint": fingerprint("bundle", "b"),
        "adapter_fingerprint": fingerprint("adapter", "c"), "preview_fingerprint": fingerprint("preview", "d")}


def observation(device=DEVICE):
    return deepcopy(expectation(device))


def receipt(device=DEVICE, kind="received_reported"):
    row = expectation(device)
    row["source_revision"] = row.pop("endpoint_revision")
    row.update(plan_id=PLAN, plan_revision="plan-1", claim_type=kind,
               report_status="reported_success", reported_at="2030-01-01T00:05:00Z", expires_at=END)
    if kind == "applied_reported":
        row["resulting_revision"] = {"revision": "policy-2", "lineage": "device-policy-lineage"}
    return row


def receipt_expectation(device=DEVICE):
    return {"plan_id": PLAN, "plan_revision": "plan-1", "preconditions": expectation(device),
            "valid_from": START, "expires_at": END}


def assert_guards(value):
    assert value.authorization == "not_evaluated"
    assert value.execution_authorized is False
    assert value.verification == "not_performed"
    assert value.scope == "packet_policy_preview_only"


def test_matching_cas_is_only_explicit_input_consistency():
    value = {"expected": expectation(), "observed": observation()}
    before = deepcopy(value)
    result = check_preconditions(value)
    assert result.status == "consistent_fixture_only" and result.format_consistent
    assert result.blocker_codes == () and value == before
    assert_guards(result)
    with pytest.raises(ValidationError):
        result.execution_authorized = True


@pytest.mark.parametrize("side", ["expected", "observed"])
@pytest.mark.parametrize("field", ["controller_revision", "endpoint_revision"])
def test_missing_durable_revision_never_synthesizes_evidence(side, field):
    value = {"expected": expectation(), "observed": observation()}
    value[side][field] = None
    result = check_preconditions(value)
    assert result.status == "precondition_evidence_missing"
    assert field in result.missing_evidence and not result.format_consistent


@pytest.mark.parametrize("field", ["controller_revision", "endpoint_revision"])
@pytest.mark.parametrize("part", ["revision", "lineage"])
def test_controller_and_endpoint_revision_lineage_are_independent(field, part):
    actual = observation()
    actual[field][part] = "changed"
    result = check_preconditions({"expected": expectation(), "observed": actual})
    assert field.removesuffix("_revision") + "_" + part + "_conflict" in result.blocker_codes


@pytest.mark.parametrize("field", ["controller_revision", "endpoint_revision"])
def test_aba_content_return_does_not_restore_old_revision(field):
    expected, actual = expectation(), observation()
    # A -> B -> A: all fingerprints are back at A, the durable policy revision is not.
    actual[field]["revision"] = "revision-after-aba"
    result = check_preconditions({"expected": expected, "observed": actual})
    assert result.status == "precondition_conflict"
    assert expected["base_fingerprint"] == actual["base_fingerprint"]


@pytest.mark.parametrize("field,kind", [("base_fingerprint", "bundle"), ("candidate_fingerprint", "bundle"),
    ("adapter_fingerprint", "adapter"), ("preview_fingerprint", "preview")])
def test_old_artifact_or_scenario_preview_cannot_move_to_new_proposal(field, kind):
    actual = observation()
    actual[field] = fingerprint(kind, "e")
    assert field + "_conflict" in check_preconditions({"expected": expectation(), "observed": actual}).blocker_codes
    actual[field] = None
    assert check_preconditions({"expected": expectation(), "observed": actual}).status == "precondition_evidence_missing"


@pytest.mark.parametrize("field,value,code", [("tenant_id", OTHER, "tenant_mismatch"),
    ("device_id", OTHER, "device_mismatch"), ("product_id", "termivar", "product_mismatch"),
    ("enforcement_scope", "native_windows_rules", "enforcement_scope_mismatch")])
def test_tenant_device_product_and_enforcement_scope_are_bound(field, value, code):
    actual = observation()
    actual["binding"][field] = value
    result = check_preconditions({"expected": expectation(), "observed": actual})
    assert code in result.blocker_codes and result.status == "precondition_conflict"


@pytest.mark.parametrize("field,value", [("execution_authorized", True), ("execution_authorized", 0),
    ("verification", "verified"), ("authorization", "approved"), ("verified", True),
    ("apply", True), ("schema_version", True), ("schema_version", 1.0), ("schema_version", "1")])
def test_external_dto_cannot_escalate_guard_fields_or_coerce_version(field, value):
    row = {"expected": expectation(), "observed": observation(), field: value}
    with pytest.raises(PolicyContractError, match="precondition_input_invalid"):
        check_preconditions(row)


def test_unsafe_model_copy_is_revalidated_and_unknown_blocker_is_rejected():
    row = PreconditionCheck(expected=expectation(), observed=observation())
    with pytest.raises(PolicyContractError):
        check_preconditions(row.model_copy(update={"execution_authorized": True}))
    with pytest.raises(ValidationError):
        PreconditionResult(status="consistent_fixture_only", format_consistent=True, blocker_codes=("approved",))
    row = expectation()
    row["endpoint_revision"] = {"inventory_sequence": 1, "lineage": "runtime-generation"}
    with pytest.raises(PolicyContractError):
        check_preconditions({"expected": row, "observed": observation()})


@pytest.mark.parametrize("kind", ["received_reported", "applied_reported"])
def test_report_consistency_never_verifies_occurrence_or_authorizes(kind):
    result = validate_receipt(receipt(kind=kind), receipt_expectation(), now=NOW)
    assert result.format_consistent and result.status == "receipt_consistent_fixture_only"
    assert result.claim_type == kind and result.evidence_basis == "reported_claim_only"
    assert_guards(result)


@pytest.mark.parametrize("field,value,code", [("plan_id", OTHER, "receipt_plan_conflict"),
    ("plan_revision", "new-plan", "receipt_plan_revision_conflict"),
    ("preview_fingerprint", fingerprint("preview", "e"), "preview_fingerprint_conflict"),
    ("candidate_fingerprint", fingerprint("bundle", "e"), "candidate_fingerprint_conflict"),
    ("reported_at", "2030-01-01T00:11:00Z", "receipt_from_future"),
    ("expires_at", "2030-01-01T00:09:00Z", "receipt_stale"),
    ("expires_at", "2030-01-01T02:00:00Z", "receipt_outside_plan_window"),
    ("report_status", "reported_failure", "receipt_reported_failure")])
def test_stale_delayed_wrong_plan_and_failed_reports_cannot_bind(field, value, code):
    row = receipt()
    row[field] = value
    result = validate_receipt(row, receipt_expectation(), now=NOW)
    assert not result.format_consistent and code in result.blocker_codes


def test_received_claim_cannot_smuggle_applied_revision_and_applied_needs_revision():
    row = receipt()
    row["resulting_revision"] = {"revision": "later", "lineage": "device-policy-lineage"}
    assert "receipt_claim_inconsistent" in validate_receipt(row, receipt_expectation(), now=NOW).blocker_codes
    row = receipt(kind="applied_reported")
    row["resulting_revision"] = None
    assert validate_receipt(row, receipt_expectation(), now=NOW).status == "receipt_evidence_missing"
    row = receipt()
    row["source_revision"] = None
    assert validate_receipt(row, receipt_expectation(), now=NOW).status == "receipt_evidence_missing"
    for bad in ({"claim_type": "verified"}, {"verified": True}, {"execution_authorized": True}):
        with pytest.raises(PolicyContractError):
            validate_receipt({**receipt(), **bad}, receipt_expectation(), now=NOW)


def test_pure_cas_and_receipts_do_not_touch_clock_environment_files_or_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("forbidden side effect")
    monkeypatch.setattr(builtins, "open", blocked)
    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(os, "getenv", blocked)
    monkeypatch.setattr(time, "time", blocked)
    monkeypatch.setattr(time, "monotonic", blocked)
    assert check_preconditions({"expected": expectation(), "observed": observation()}).format_consistent
    assert validate_receipt(receipt(), receipt_expectation(), now=NOW).format_consistent
