"""Local identity and disclosure reconciliation with synthetic local snapshots."""
from __future__ import annotations

import pytest

from exchange_contracts import InputError
from synthetic_fixtures import (
    canonical_capsule, full_local, local, phase42_record, phase43_record, request, sha, synthetic_envelope,
    synthetic_task,
)
from reconciliation_engine import reconcile_capsule

BOTH = "PHASE42_TASK_RECORDS_AND_PHASE43_DISCLOSURE_RECORDS"


def rows(report: dict, **match) -> list:
    return [r for r in report["local_reconciliation"]["comparisons"]
            if all(r[key] == value for key, value in match.items())]


def rules(report: dict) -> set:
    return {item["rule"] for item in report["findings"]}


def test_full_match_is_structurally_valid_requires_manual_review():
    capsule = canonical_capsule()
    snapshot, req = full_local(capsule)
    report, inbox = reconcile_capsule(capsule, req, snapshot)
    assert report["eligibility"]["status"] == "STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW"
    assert report["eligibility"]["manual_review"] == "ELIGIBLE_FOR_MANUAL_REVIEW"
    assert report["eligibility"]["manual_review_requirement"] == "REQUIRED"
    assert {r["result"] for r in report["local_reconciliation"]["comparisons"]} == {"MATCH"}
    assert report["local_reconciliation"]["task_lookups"] == [
        {"subject": "task:F0007", "task_id": "F0007", "phase42_lookup": "FOUND", "phase43_lookup": "FOUND"}]
    assert inbox["lifecycle_stage"] == "QUARANTINED_AWAITING_MANUAL_REVIEW"
    assert inbox["admitted_tasks"][0]["fact_origin"] == "CAPSULE_DECLARED_STRUCTURALLY_VALID_NOT_AUTHENTICATED"
    assert inbox["admitted_tasks"][0]["local_reconciliation"] == "MATCH"
    statuses = {"TRUSTED", "APPROVED", "ASSIGNED", "ACCEPTED", "EXECUTED", "COMPLETED", "PRODUCTION"}
    assert not any(word in report["eligibility"]["status"] for word in statuses)


def test_identity_mismatch_withholds_undisclosed_local_value():
    local_task = synthetic_task()
    capsule_task = dict(local_task, candidate_id="SYNTH0099")
    capsule = canonical_capsule(synthetic_envelope([capsule_task]))
    p42 = phase42_record([local_task])
    snapshot = local("PHASE42_TASK_RECORDS_ONLY", p42, None)
    report, inbox = reconcile_capsule(capsule, request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"]), snapshot)
    assert report["eligibility"]["status"] == "IDENTITY_MISMATCH"
    row = rows(report, field="candidate_id", reference_source="PHASE42_LOCAL_TASK_RECORD")[0]
    assert row["result"] == "MISMATCH" and row["capsule_value"] == "SYNTH0099"
    assert row["local_value"] is None and row["local_value_disclosure"] == "WITHHELD_NOT_PREVIOUSLY_DISCLOSED"
    assert "IDENTITY_MISMATCH" in rules(report)
    assert inbox["lifecycle_stage"] == "QUARANTINED_HELD_IDENTITY_MISMATCH"
    assert inbox["admitted_tasks"][0]["local_reconciliation"] == "MISMATCH"
    assert inbox["manual_review"] == "NOT_ELIGIBLE"


def test_identity_mismatch_echoes_value_already_disclosed_by_phase43():
    local_task = synthetic_task()
    disclosed_capsule = canonical_capsule(synthetic_envelope([local_task]))
    imported = canonical_capsule(synthetic_envelope([dict(local_task, candidate_id="SYNTH0099")]))
    p42, p43 = phase42_record([local_task]), phase43_record(disclosed_capsule)
    report, _ = reconcile_capsule(imported, request(BOTH, p42["register_sha256"], p43["index_sha256"]),
                                  local(BOTH, p42, p43))
    assert report["eligibility"]["status"] == "IDENTITY_MISMATCH"
    for source in ("PHASE42_LOCAL_TASK_RECORD", "PHASE43_LOCAL_DISCLOSURE_RECORD"):
        row = rows(report, field="candidate_id", reference_source=source)[0]
        assert row["result"] == "MISMATCH" and row["local_value"] == "SYNTH0001"
    assert rows(report, field="capsule_sha256")[0]["result"] == "MISMATCH"
    assert rows(report, field="member_sha256:task-request.json")[0]["result"] == "MISMATCH"
    assert rows(report, field="member_sha256:README.txt")[0]["result"] == "MATCH"
    assert "DISCLOSURE_MISMATCH" in rules(report)


def test_ambiguous_binding_owned_by_other_local_task():
    owner_task = synthetic_task("F0007")
    claimed = synthetic_task("F0008", "SYNTH0002", "b")
    claimed["binding_digest"] = owner_task["binding_digest"]
    capsule = canonical_capsule(synthetic_envelope([claimed]))
    p42 = phase42_record([owner_task, synthetic_task("F0008", "SYNTH0002", "b")])
    report, _ = reconcile_capsule(capsule, request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"]),
                                  local("PHASE42_TASK_RECORDS_ONLY", p42, None))
    assert report["eligibility"]["status"] == "IDENTITY_MISMATCH"
    owner_row = rows(report, field="binding_digest_owner_task")[0]
    assert owner_row["result"] == "MISMATCH" and owner_row["capsule_value"] == "F0008"
    assert owner_row["local_value"] is None          # F0007 was never disclosed
    assert "AMBIGUOUS_BINDING_OWNER" in rules(report)


def test_task_not_found_locally_is_unavailable():
    capsule = canonical_capsule(synthetic_envelope([synthetic_task("F0011", "SYNTH0011", "k")]))
    p42 = phase42_record([synthetic_task()])
    report, inbox = reconcile_capsule(capsule, request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"]),
                                      local("PHASE42_TASK_RECORDS_ONLY", p42, None))
    assert report["local_reconciliation"]["task_lookups"][0]["phase42_lookup"] == "NOT_FOUND"
    assert report["eligibility"]["status"] == "LOCAL_RECONCILIATION_UNAVAILABLE"
    assert {"LOCAL_TASK_NOT_FOUND", "LOCAL_RECORDS_NOT_SUPPLIED"} <= rules(report)
    assert all(r["local_value"] is None for r in rows(report, subject="task:F0011"))
    assert inbox["lifecycle_stage"] == "QUARANTINED_HELD_LOCAL_RECONCILIATION_UNAVAILABLE"


def test_no_local_records_is_unavailable_never_match():
    report, _ = reconcile_capsule(canonical_capsule(), request(), local())
    results = {r["result"] for r in report["local_reconciliation"]["comparisons"]}
    assert results == {"UNAVAILABLE"}
    assert report["eligibility"]["status"] == "LOCAL_RECONCILIATION_UNAVAILABLE"


def test_request_and_local_snapshot_must_agree():
    capsule = canonical_capsule()
    snapshot, req = full_local(capsule)
    with pytest.raises(InputError):
        reconcile_capsule(capsule, dict(req, expected_local_phase42_register_sha256=sha("other")), snapshot)
    with pytest.raises(InputError):
        reconcile_capsule(capsule, request(), snapshot)
    with pytest.raises(InputError):
        reconcile_capsule(capsule, dict(request(), expected_local_phase42_register_sha256=sha("x")), local())


def test_inconsistent_local_groups_are_rejected():
    capsule = canonical_capsule()
    p42 = phase42_record()
    p43 = phase43_record(capsule)
    p43["source_phase42_register_sha256"] = sha("different-register")
    with pytest.raises(InputError):
        local(BOTH, p42, p43)
    ambiguous = phase42_record([synthetic_task("F0007"), synthetic_task("F0007", "SYNTH0002", "b")])
    with pytest.raises(InputError):
        local("PHASE42_TASK_RECORDS_ONLY", ambiguous, None)
