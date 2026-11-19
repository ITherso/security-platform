"""Deterministic outputs and the disclosure-minimization boundary."""
from __future__ import annotations

from exchange_contracts import json_bytes
from synthetic_fixtures import (
    canonical_capsule, canonical_members, full_local, local, phase42_record, phase43_record, rehash_manifest,
    request, synthetic_envelope, synthetic_task, zip_members,
)
from reconciliation_engine import reconcile_capsule
from reconciliation_manifest import input_identities, output_documents

BOTH = "PHASE42_TASK_RECORDS_AND_PHASE43_DISCLOSURE_RECORDS"


def documents(capsule: bytes, req: dict, snapshot) -> dict:
    report, inbox = reconcile_capsule(capsule, req, snapshot)
    return output_documents(report, inbox, input_identities(capsule, json_bytes(req), snapshot))


def test_same_inputs_give_byte_identical_outputs():
    capsule = canonical_capsule()
    snapshot, req = full_local(capsule)
    first = documents(capsule, req, snapshot)
    second = documents(capsule, dict(reversed(list(req.items()))), snapshot)
    assert first == second
    assert list(first) == ["task-inbox-record.json", "capsule-reconciliation-report.json",
                           "capsule-reconciliation-summary.md", "manifest.json"]


def test_rejected_capsule_outputs_are_deterministic_too():
    members = canonical_members()
    hostile = zip_members(dict(members, **{"task-request.json": b'{"a": 1, "a": 2}'}))
    assert documents(hostile, request(), local()) == documents(hostile, request(), local())


def test_report_contains_no_clock_or_path_material():
    capsule = canonical_capsule()
    snapshot, req = full_local(capsule)
    for raw in documents(capsule, req, snapshot).values():
        text = raw.decode("utf-8")
        assert "\\Users\\" not in text and "/Users/" not in text and "2026-" not in text


def test_hostile_strings_and_unclaimed_local_tasks_are_not_disclosed():
    secret = "synthetic-SECRET-token-0123456789"
    task = dict(synthetic_task(), **{"candidate_response": secret})
    task["candidate_id"] = "bad id with spaces " + secret
    envelope = synthetic_envelope([task])
    envelope["extra_" + "x" * 3] = secret
    members = rehash_manifest(dict(canonical_members(), **{"task-request.json": json_bytes(envelope)}))
    hostile = zip_members(members)
    unclaimed = synthetic_task("F0012", "SYNTH0012", "unclaimed")
    p42 = phase42_record([synthetic_task(), unclaimed])
    snapshot = local("PHASE42_TASK_RECORDS_ONLY", p42, None)
    req = request("PHASE42_TASK_RECORDS_ONLY", p42["register_sha256"])
    body = b"".join(documents(hostile, req, snapshot).values())
    assert secret.encode() not in body
    for key in ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest"):
        assert unclaimed[key].encode() not in body
    # A structurally valid capsule also never echoes unclaimed local tasks.
    valid = canonical_capsule()
    body = b"".join(documents(valid, req, snapshot).values())
    for key in ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest"):
        assert unclaimed[key].encode() not in body


def test_rejected_capsule_never_consults_local_values():
    capsule = canonical_capsule()
    p42, p43 = phase42_record(), phase43_record(capsule)
    members = canonical_members()
    broken = zip_members(dict(members, **{"README.txt": b"changed"}))
    report, _ = reconcile_capsule(broken, request(BOTH, p42["register_sha256"], p43["index_sha256"]),
                                  local(BOTH, p42, p43))
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION"
    comparisons = report["local_reconciliation"]["comparisons"]
    assert comparisons and all(r["local_value"] is None and r["local_value_disclosure"] == "NOT_AVAILABLE"
                               for r in comparisons)
    assert all(lookup["phase42_lookup"] == "NOT_PERFORMED" for lookup in report["local_reconciliation"]["task_lookups"])


def test_forbidden_keys_never_appear_in_outputs():
    capsule = canonical_capsule()
    snapshot, req = full_local(capsule)
    body = b"".join(documents(capsule, req, snapshot).values())
    for key in (b'"candidate_response"', b'"observed_sha256"', b'"reference_packets"', b'"projections"',
                b'"source_locator"'):
        assert key not in body
