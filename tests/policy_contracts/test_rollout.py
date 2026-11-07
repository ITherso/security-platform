from copy import deepcopy
import builtins
import os
import socket
import time

from pydantic import ValidationError
import pytest

from security_platform.policy_contracts.errors import PolicyContractError
from security_platform.policy_contracts.rollout import FIXED_BLOCKERS, ProposedRollout, simulate_rollout
from test_preconditions import (DEVICE, END, NOW, OTHER, PLAN, START, TENANT, assert_guards,
                               expectation, fingerprint, observation, receipt)


def plan(count=2):
    ids = [f"00000000-0000-4000-8000-{number + 2:012x}" for number in range(count)]
    targets = []
    for device in ids:
        expected = expectation(device)
        targets.append({"device_id": device, "preconditions": expected,
            "rollback_reference": {"artifact_fingerprint": expected["base_fingerprint"],
                                   "endpoint_revision": deepcopy(expected["endpoint_revision"])}})
    return {"plan_id": PLAN, "plan_revision": "plan-1", "tenant_id": TENANT,
        "product_id": "hostbasedfirewall", "enforcement_scope": "packet_policy",
        "candidate_fingerprint": fingerprint("bundle", "b"), "adapter_fingerprint": fingerprint("adapter", "c"),
        "targets": targets, "pilot_devices": [ids[0]],
        "batches": [ids[start:start + 32] for start in range(1, count, 32)],
        "valid_from": START, "expires_at": END}


def observations(value):
    return [observation(target["device_id"]) for target in value["targets"]]


def test_initial_proposal_waits_with_fixed_blockers_and_does_not_open_a_batch():
    value = plan()
    before = deepcopy(value)
    result = simulate_rollout(value, observations(value), now=NOW)
    assert result.status == "would_wait" and result.next_batch is None
    assert result.execution_plan == "not_created" and result.rollback == "references_only"
    assert set(FIXED_BLOCKERS) <= set(result.blocker_codes)
    assert value == before
    assert_guards(result)
    assert all(target.status == "would_wait" for target in result.targets)


def test_applied_pilot_report_never_becomes_verified_or_releases_later_batch():
    value = plan()
    result = simulate_rollout(value, observations(value), [receipt(kind="applied_reported")], now=NOW)
    assert result.status == "would_wait" and result.next_batch is None
    assert result.targets[0].receipt_claims == ("applied_reported",)
    assert "verification_not_performed" in result.blocker_codes
    assert_guards(result.targets[0])


@pytest.mark.parametrize("change,code", [("missing", "precondition_evidence_missing"),
    ("aba", "endpoint_revision_conflict"), ("controller", "controller_revision_conflict"),
    ("tenant", "tenant_mismatch"), ("adapter", "adapter_fingerprint_conflict")])
def test_missing_conflicting_or_aba_cas_pauses(change, code):
    value = plan()
    actual = observations(value)
    if change == "missing": actual.pop()
    elif change == "aba": actual[0]["endpoint_revision"]["revision"] = "after-aba"
    elif change == "controller": actual[0]["controller_revision"]["revision"] = "new-controller"
    elif change == "tenant": actual[0]["binding"]["tenant_id"] = OTHER
    else: actual[0]["adapter_fingerprint"] = fingerprint("adapter", "e")
    result = simulate_rollout(value, actual, now=NOW)
    assert result.status == "would_pause" and code in result.blocker_codes


@pytest.mark.parametrize("field", ["controller_revision", "endpoint_revision"])
def test_unknown_durable_revisions_cannot_form_a_ready_proposal(field):
    value = plan(1)
    value["targets"][0]["preconditions"][field] = None
    if field == "endpoint_revision":
        value["targets"][0]["rollback_reference"][field] = None
    result = simulate_rollout(value, observations(value), now=NOW)
    assert result.status == "would_pause" and "precondition_evidence_missing" in result.blocker_codes


@pytest.mark.parametrize("field,value,code", [("plan_revision", "old-plan", "receipt_plan_revision_conflict"),
    ("report_status", "reported_failure", "receipt_reported_failure"),
    ("expires_at", "2030-01-01T00:09:00Z", "receipt_stale")])
def test_failed_stale_or_old_plan_receipts_pause(field, value, code):
    proposed = plan()
    claim = receipt()
    claim[field] = value
    result = simulate_rollout(proposed, observations(proposed), [claim], now=NOW)
    assert result.status == "would_pause" and code in result.blocker_codes


def test_expiry_and_not_started_use_only_explicit_time():
    value = plan()
    assert simulate_rollout(value, observations(value), now=END).status == "would_pause"
    future = simulate_rollout(value, observations(value), now="2029-12-31T23:59:59Z")
    assert future.status == "would_wait" and "rollout_not_started" in future.blocker_codes
    for invalid in (None, "2030-01-01T00:10:00", "2030-99-01T00:10:00Z"):
        with pytest.raises(PolicyContractError, match="evaluation_time_invalid"):
            simulate_rollout(value, observations(value), now=invalid)
    with pytest.raises(TypeError):
        simulate_rollout(value)


@pytest.mark.parametrize("change", ["duplicate", "unassigned", "foreign-pilot", "foreign-tenant",
    "candidate", "adapter", "rollback", "rollback-revision", "empty-targets", "empty-pilot",
    "too-many", "too-long", "reverse-window", "unsupported-scope"])
def test_bad_partition_binding_reference_or_budget_has_no_partial_plan(change):
    value = plan()
    if change == "duplicate": value["batches"] = [[DEVICE]]
    elif change == "unassigned": value["batches"] = []
    elif change == "foreign-pilot": value["pilot_devices"] = [PLAN]
    elif change == "foreign-tenant": value["tenant_id"] = OTHER
    elif change == "candidate": value["candidate_fingerprint"] = fingerprint("bundle", "f")
    elif change == "adapter": value["adapter_fingerprint"] = fingerprint("adapter", "f")
    elif change == "rollback": value["targets"][0]["rollback_reference"]["artifact_fingerprint"] = fingerprint("bundle", "f")
    elif change == "rollback-revision": value["targets"][0]["rollback_reference"]["endpoint_revision"]["revision"] = "foreign"
    elif change == "empty-targets": value["targets"] = []
    elif change == "empty-pilot": value["pilot_devices"] = []
    elif change == "too-many": value = plan(129)
    elif change == "too-long": value["expires_at"] = "2030-01-03T00:00:00Z"
    elif change == "reverse-window": value["expires_at"] = "2029-12-31T00:00:00Z"
    else: value["enforcement_scope"] = "native_windows_rules"
    with pytest.raises(PolicyContractError, match="rollout_input_invalid"):
        simulate_rollout(value, now=NOW)


@pytest.mark.parametrize("field,value", [("execution_authorized", True), ("execution_authorized", 0),
    ("verified", True), ("apply", True), ("command", "arbitrary"), ("dry_run", False),
    ("schema_version", True), ("schema_version", 1.0), ("unresolved_gates", []),
    ("stop_conditions", {"on_failure": False}), ("stop_conditions", {"on_stale_receipt": 1})])
def test_untrusted_input_cannot_authorize_clear_gates_or_disable_stops(field, value):
    proposed = plan()
    proposed[field] = value
    with pytest.raises(PolicyContractError):
        simulate_rollout(proposed, now=NOW)


def test_targets_nested_revisions_and_groups_are_immutable_and_ordered():
    value = ProposedRollout.model_validate(plan())
    assert isinstance(value.targets, tuple) and isinstance(value.batches[0], tuple)
    with pytest.raises(ValidationError): value.plan_revision = "changed"
    with pytest.raises(ValidationError): value.targets[0].preconditions.endpoint_revision.revision = "changed"
    with pytest.raises(AttributeError): value.pilot_devices.append(OTHER)
    with pytest.raises(PolicyContractError):
        simulate_rollout(value.model_copy(update={"execution_authorized": True}), now=NOW)


def test_duplicate_or_foreign_receipt_and_observation_cannot_be_silently_ignored():
    value = plan()
    actual = observations(value)
    assert "rollout_observation_binding_conflict" in simulate_rollout(value, actual + [actual[0]], now=NOW).blocker_codes
    claims = [receipt(), receipt()]
    assert "rollout_receipt_binding_conflict" in simulate_rollout(value, actual, claims, now=NOW).blocker_codes
    claims = [receipt(OTHER)]
    assert "rollout_receipt_binding_conflict" in simulate_rollout(value, actual, claims, now=NOW).blocker_codes


def test_pure_rollout_has_no_file_network_environment_or_clock_access(monkeypatch):
    value, actual = plan(), observations(plan())
    def blocked(*args, **kwargs): raise AssertionError("forbidden side effect")
    monkeypatch.setattr(builtins, "open", blocked)
    monkeypatch.setattr(socket, "socket", blocked)
    monkeypatch.setattr(os, "getenv", blocked)
    monkeypatch.setattr(time, "time", blocked)
    monkeypatch.setattr(time, "monotonic", blocked)
    assert simulate_rollout(value, actual, now=NOW).status == "would_wait"
