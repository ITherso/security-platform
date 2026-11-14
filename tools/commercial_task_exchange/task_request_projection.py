"""Source-bound minimal tasks, without full reference-packet disclosure."""
from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from exchange_contracts import (
    InputError, LIMITATIONS, PORTABLE_REQUEST_SCHEMA, RECEIPT_SCHEMA,
    REQUEST_SCHEMA, common, exchange_counts, fixed, response_field_definitions,
    validate_portable_request, validate_receipt, validate_request,
)

if TYPE_CHECKING:
    from phase42_adapter import ValidatedPhase42Source


def build_task_request(validated_source: ValidatedPhase42Source,
                       request: dict) -> dict:
    """Copy only selected pending task identities from the actual source group."""
    from phase42_adapter import read_source
    from slot_contracts import submission_contract

    request = validate_request(request)
    intake, classification, _receipt, artifacts = read_source(validated_source)
    fixed(request["source_phase42_register_sha256"], artifacts[0]["sha256"],
          "task_exchange_actual_Phase42_register_identity")
    fixed(request["source_phase42_manifest_sha256"], artifacts[-1]["sha256"],
          "task_exchange_actual_Phase42_manifest_identity")
    fixed(response_field_definitions(), submission_contract(),
          "task_exchange_exact_owner_response_field_definitions")
    fixed(common(PORTABLE_REQUEST_SCHEMA)["trust_flags"], intake["trust_flags"],
          "task_exchange_exact_owner_false_trust_fields")

    selected_ids = request["selected_task_ids"]
    source_ids = {entry["task_id"] for entry in intake["intake_entries"]}
    if any(task_id not in source_ids for task_id in selected_ids):
        raise InputError("task_exchange_task_outside_original_intake")
    selected = set(selected_ids)
    entries = [entry for entry in intake["intake_entries"]
               if entry["task_id"] in selected]
    fixed([entry["task_id"] for entry in entries], sorted(selected_ids),
          "task_exchange_complete_original_task_selection")
    classified_by_id = {item["task_id"]: item
                        for item in classification["task_classifications"]}
    tasks = []
    for entry in entries:
        if entry["task_id"] not in classified_by_id:
            raise InputError("task_exchange_source_classification_missing")
        classified = classified_by_id[entry["task_id"]]
        fixed(entry["slot_status"], "awaiting_external_response", "task_exchange_pending_slot")
        fixed(entry["response_status"], "unsubmitted", "task_exchange_unsubmitted_source")
        fixed(entry["candidate_present"], False, "task_exchange_no_candidate")
        fixed(entry["candidate_classification"], "no_candidate_supplied", "task_exchange_no_candidate_classification")
        fixed(entry["candidate_response"], None, "task_exchange_no_candidate_payload")
        fixed(classified["binding_digest"], entry["binding_digest"], "task_exchange_source_binding_correspondence")
        fixed(classified["intake_status"], "awaiting_submission", "task_exchange_source_awaiting_submission")
        fixed(classified["structural_result"], "not_evaluated_no_candidate", "task_exchange_source_not_evaluated")
        fixed(classified["observation_verified"], False, "task_exchange_source_observation_unverified")
        fixed(classified["task_completed"], False, "task_exchange_source_task_incomplete")
        # The original parent40 binding preimage is not present here. Preserve
        # the source tuple/digest without rederiving it with a current hash.
        tasks.append({
            "task_id": entry["task_id"], "reference_id": entry["reference_id"],
            "candidate_id": entry["candidate_id"], "file_id": entry["file_id"],
            "binding_digest": entry["binding_digest"], "slot_status": entry["slot_status"],
            "response_status": entry["response_status"], "candidate_present": entry["candidate_present"],
            "observation_verified": classified["observation_verified"],
            "task_completed": classified["task_completed"],
        })
    return validate_portable_request({
        **common(PORTABLE_REQUEST_SCHEMA),
        "source_phase42_register_sha256": artifacts[0]["sha256"],
        "source_phase42_manifest_sha256": artifacts[-1]["sha256"],
        "request_reference": request["request_reference"],
        "tasks": tasks, "counts": exchange_counts(tasks), "limitations": list(LIMITATIONS),
    })


def make_source_receipt(validated_source: ValidatedPhase42Source,
                        envelope: dict) -> dict:
    """Bind the minimal projection to its actual five-source identities."""
    from phase42_adapter import read_source

    envelope = validate_portable_request(envelope)
    request = validate_request({
        "schema_version": REQUEST_SCHEMA, "mode": "demo",
        "request_reference": envelope["request_reference"],
        "source_phase42_register_sha256": envelope["source_phase42_register_sha256"],
        "source_phase42_manifest_sha256": envelope["source_phase42_manifest_sha256"],
        "selected_task_ids": [task["task_id"] for task in envelope["tasks"]],
    })
    fixed(envelope, build_task_request(validated_source, request),
          "task_exchange_receipt_actual_source_projection")
    intake, classification, receipt, artifacts = read_source(validated_source)
    return validate_receipt({
        **common(RECEIPT_SCHEMA),
        "source_artifacts": [dict(item) for item in artifacts],
        "source_phase42_register_sha256": artifacts[0]["sha256"],
        "source_phase42_manifest_sha256": artifacts[-1]["sha256"],
        "source_schema_versions": {item["name"]: item["schema_version"] for item in artifacts},
        "source_counts": {
            "register_counts": dict(intake["counts"]),
            "classification_counts": dict(classification["counts"]),
            "phase41_counts": deepcopy(receipt["source_counts"]),
        },
        "content_scope": "five_Phase42_artifact_internal_correspondence_only",
        "limitations": list(LIMITATIONS),
    })


__all__ = ("build_task_request", "make_source_receipt")
