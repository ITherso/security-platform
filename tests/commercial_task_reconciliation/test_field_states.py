"""Absent, null, empty, false and zero stay distinct; declarations are checked."""
from __future__ import annotations

from exchange_contracts import json_bytes
from synthetic_fixtures import (
    canonical_members, local, rehash_manifest, request, synthetic_envelope, synthetic_task, zip_members,
)
from reconciliation_engine import reconcile_capsule


def run_envelope(envelope: dict):
    members = rehash_manifest(dict(canonical_members(), **{"task-request.json": json_bytes(envelope)}))
    return reconcile_capsule(zip_members(members), request(), local())


def field(report: dict, path: str) -> dict:
    for record in report["envelope_fields"] + [f for t in report["tasks"] for f in t["fields"]]:
        if record["path"] == path:
            return record
    raise AssertionError(path)


def rules(report: dict) -> set:
    return {item["rule"] for item in report["findings"]}


TASK = "task-request.json:tasks[0]."


def test_missing_identity_is_absent_not_null():
    task = synthetic_task()
    del task["candidate_id"]
    report, inbox = run_envelope(synthetic_envelope([task]))
    record = field(report, TASK + "candidate_id")
    assert record["presence"] == "ABSENT" and record["state"] == "ABSENT" and record["value_kind"] == "ABSENT"
    assert record["value_disclosure"] == "NOT_APPLICABLE" and record["value"] is None
    assert TASK + "candidate_id" in report["field_presence_summary"]["absent"]
    assert "IDENTITY_ABSENT" in rules(report)
    assert report["capsule_identity"]["declared_tasks"][0]["candidate_id"] is None
    assert report["eligibility"]["status"] == "STRUCTURAL_REJECTION" and inbox["admitted_tasks"] == []


def test_explicit_null_is_distinct_from_absent():
    task = synthetic_task()
    task["candidate_id"] = None
    report, _ = run_envelope(synthetic_envelope([task]))
    record = field(report, TASK + "candidate_id")
    assert record["presence"] == "PRESENT" and record["state"] == "NULL" and record["value_kind"] == "NULL"
    assert record["value_disclosure"] == "ECHOED" and record["value"] is None
    assert TASK + "candidate_id" in report["field_presence_summary"]["null"]
    assert TASK + "candidate_id" not in report["field_presence_summary"]["absent"]
    assert "IDENTITY_NULL" in rules(report)


def test_empty_string_list_object_false_and_zero_are_distinct():
    task = synthetic_task()
    task["candidate_id"] = ""
    task["candidate_present"] = 0
    envelope = synthetic_envelope([task])
    envelope["trust_flags"] = {}
    envelope["limitations"] = []
    report, _ = run_envelope(envelope)
    empty = field(report, TASK + "candidate_id")
    assert empty["state"] == "EMPTY_STRING" and empty["value"] == "" and empty["value_kind"] == "STRING"
    zero = field(report, TASK + "candidate_present")
    assert zero["state"] == "INVALID" and zero["value_kind"] == "INTEGER" and zero["value"] == 0
    false = field(report, TASK + "observation_verified")
    assert false["state"] == "VALID" and false["value_kind"] == "BOOLEAN" and false["value"] is False
    assert field(report, "task-request.json:trust_flags")["state"] == "EMPTY_OBJECT"
    limitations = field(report, "task-request.json:limitations")
    assert limitations["state"] == "EMPTY_ARRAY" and limitations["item_count"] == 0
    summary = report["field_presence_summary"]
    assert TASK + "candidate_id" in summary["empty_string"]
    assert TASK + "candidate_present" in summary["invalid"]
    assert "task-request.json:trust_flags" in summary["empty_object"]
    assert "task-request.json:limitations" in summary["empty_array"]
    assert {"IDENTITY_EMPTY_STRING", "FIELD_INVALID", "FIELD_EMPTY_OBJECT", "FIELD_EMPTY_ARRAY"} <= rules(report)


def test_empty_task_list():
    envelope = synthetic_envelope()
    envelope["tasks"] = []
    report, _ = run_envelope(envelope)
    assert field(report, "task-request.json:tasks")["state"] == "EMPTY_ARRAY"
    assert report["task_declaration"]["actual_task_entry_count"] == 0
    assert report["task_declaration"]["declared_task_count"] == 1
    assert report["task_declaration"]["consistency"] == "INCONSISTENT"
    assert "TASK_COUNT_DECLARATION_MISMATCH" in rules(report)


def test_malformed_identifier_is_withheld():
    task = synthetic_task()
    task["reference_id"] = "rust-ref-NOT-A-DIGEST"
    task["file_id"] = 42
    report, _ = run_envelope(synthetic_envelope([task]))
    reference = field(report, TASK + "reference_id")
    assert reference["state"] == "INVALID" and reference["value_disclosure"] == "WITHHELD_INVALID_STRING"
    assert reference["value"] is None and reference["string_length"] == len("rust-ref-NOT-A-DIGEST")
    assert reference["owner_rule_code"] == "task_exchange_invalid_portable_reference_id"
    file_id = field(report, TASK + "file_id")
    assert file_id["state"] == "INVALID" and file_id["value_kind"] == "INTEGER" and file_id["value"] == 42
    assert "IDENTITY_INVALID" in rules(report)


def test_structurally_inconsistent_task_declarations():
    first, second = synthetic_task("F0007"), synthetic_task("F0007", "SYNTH0002", "b")
    envelope = synthetic_envelope([first])
    envelope["tasks"] = [first, second]          # counts still declare one task
    report, _ = run_envelope(envelope)
    assert {"TASK_COUNT_DECLARATION_MISMATCH", "TASK_DUPLICATE_REFERENCE"} <= rules(report)
    assert report["task_declaration"]["consistency"] == "INCONSISTENT"
    shared = synthetic_task("F0008", "SYNTH0002", "b")
    shared["binding_digest"] = first["binding_digest"]
    envelope = synthetic_envelope([first])
    envelope["tasks"] = [first, shared]
    envelope["counts"] = dict(envelope["counts"], selected_task_count=2, unsubmitted_request_count=2)
    report, _ = run_envelope(envelope)
    assert "TASK_DUPLICATE_BINDING" in rules(report)
    unordered = synthetic_envelope([synthetic_task("F0009", "SYNTH0003", "c")])
    unordered["tasks"] = [synthetic_task("F0009", "SYNTH0003", "c"), synthetic_task("F0008", "SYNTH0002", "b")]
    unordered["counts"] = dict(unordered["counts"], selected_task_count=2, unsubmitted_request_count=2)
    report, _ = run_envelope(unordered)
    assert "TASK_ORDER_NONCANONICAL" in rules(report)
    not_object = synthetic_envelope()
    not_object["tasks"] = ["F0007"]
    report, _ = run_envelope(not_object)
    assert "TASK_ENTRY_NOT_OBJECT" in rules(report)
    assert report["tasks"][0]["entry_shape"] == "NOT_OBJECT"


def test_unexpected_fields_are_counted_not_echoed():
    task = dict(synthetic_task(), **{"candidate_response": "synthetic-should-not-appear", "Bad Key!": 1})
    report, _ = run_envelope(synthetic_envelope([task]))
    unexpected = report["tasks"][0]["unexpected_fields"]
    assert unexpected == {"count": 2, "listed_names": ["candidate_response"], "unlisted_count": 1}
    assert "FIELD_UNEXPECTED" in rules(report)
    assert b"synthetic-should-not-appear" not in json_bytes(report, maximum=512 * 1024)


def test_valid_capsule_has_no_field_findings():
    report, _ = run_envelope(synthetic_envelope())
    assert report["phase43_reader"]["compatibility"] == "COMPATIBLE"
    summary = report["field_presence_summary"]
    assert all(not summary[key] for key in summary if key != "present_valid")
    assert len(summary["present_valid"]) == 10 + 10
