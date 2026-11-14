"""Consume existing unsubmitted templates without evaluating any candidate."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from intake_contracts import (
    INTAKE_SCHEMA, LIMITATIONS, MAX_INTAKE_BYTES, InputError,
    classification_from_intake, common, fixed, intake_counts, json_bytes,
    parse_json, validate_intake, validate_request,
)

if TYPE_CHECKING:
    from phase41_adapter import ValidatedPhase41Source


def _validated_intake(raw_bytes: bytes) -> dict:
    if type(raw_bytes) is not bytes:
        raise InputError("deferred_intake_exact_immutable_bytes_required")
    return validate_intake(parse_json(raw_bytes, maximum=MAX_INTAKE_BYTES))


@dataclass(frozen=True, slots=True)
class ValidatedDeferredIntake:
    """Closed new register bytes, without source or observation approval.

    Direct construction checks internal wire correspondence only; it does not
    prove original task membership, candidate receipt or observation validity.
    """

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_intake(self.raw_bytes)


def read_deferred_intake(snapshot: ValidatedDeferredIntake) -> dict:
    if type(snapshot) is not ValidatedDeferredIntake:
        raise InputError("deferred_intake_exact_validated_snapshot_required")
    return deepcopy(_validated_intake(snapshot.raw_bytes))


def build_deferred_intake(validated_source: ValidatedPhase41Source,
                           request: dict) -> ValidatedDeferredIntake:
    """Build the actual no-candidate register from the validated five files."""
    from phase41_adapter import read_source

    request = validate_request(request)
    slots, template, _receipt, artifacts = read_source(validated_source)
    fixed(request["source_phase41_slots_sha256"], artifacts[0]["sha256"],
          "deferred_intake_actual_Phase41_slots_identity")
    fixed(request["source_phase41_manifest_sha256"], artifacts[-1]["sha256"],
          "deferred_intake_actual_Phase41_manifest_identity")
    selected_ids = request["selected_task_ids"]
    source_ids = {slot["task_id"] for slot in slots["response_slots"]}
    if any(task_id not in source_ids for task_id in selected_ids):
        raise InputError("deferred_intake_task_outside_original_slots")
    selected_set = set(selected_ids)
    source_slots = [slot for slot in slots["response_slots"] if slot["task_id"] in selected_set]
    fixed([slot["task_id"] for slot in source_slots], sorted(selected_ids),
          "deferred_intake_complete_original_task_selection")
    template_entries = {entry["task_id"]: entry for entry in template["template_entries"]}
    intake_entries = []
    for slot in source_slots:
        if slot["task_id"] not in template_entries:
            raise InputError("deferred_intake_original_template_entry_missing")
        entry = template_entries[slot["task_id"]]
        fixed(slot["submission"], None, "deferred_intake_original_submission_null")
        fixed(slot["slot_status"], "awaiting_external_response", "deferred_intake_original_slot_status")
        fixed(slot["task_status"], "prepared_unassigned", "deferred_intake_original_task_status")
        fixed(slot["fulfillment_status"], "not_observed", "deferred_intake_original_fulfillment")
        fixed(entry["binding_digest"], slot["binding_digest"], "deferred_intake_original_template_binding")
        fixed(entry["response_status"], "unsubmitted", "deferred_intake_original_response_status")
        fixed(entry["response"], None, "deferred_intake_original_response_null")
        # No decoder is invoked, including with None. The source already
        # records no submission. Its original parent-bound digest is copied;
        # the current Phase41 slots hash is not that digest's parent preimage.
        intake_entries.append({
            "task_id": slot["task_id"], "reference_id": slot["reference_id"],
            "candidate_id": slot["candidate_id"], "file_id": slot["file_id"],
            "binding_digest": slot["binding_digest"], "slot_status": slot["slot_status"],
            "response_status": entry["response_status"], "candidate_present": False,
            "candidate_classification": "no_candidate_supplied", "candidate_response": None,
        })
    reference_ids = {entry["reference_id"] for entry in intake_entries}
    packets = [deepcopy(packet) for packet in slots["reference_packets"]
               if packet["reference_id"] in reference_ids]
    fixed([packet["reference_id"] for packet in packets], sorted(reference_ids),
          "deferred_intake_complete_task_reference_packets")
    intake = validate_intake({
        **common(INTAKE_SCHEMA),
        "source_phase41_slots_sha256": artifacts[0]["sha256"],
        "source_phase41_manifest_sha256": artifacts[-1]["sha256"],
        "request": request, "reference_packets": packets, "intake_entries": intake_entries,
        "counts": intake_counts(intake_entries), "limitations": list(LIMITATIONS),
    })
    return ValidatedDeferredIntake(json_bytes(intake, maximum=MAX_INTAKE_BYTES))


def build_intake_classification(validated_intake: ValidatedDeferredIntake) -> dict:
    """Classify only the register's existing absence of a candidate response."""
    return classification_from_intake(read_deferred_intake(validated_intake))


__all__ = ("ValidatedDeferredIntake", "read_deferred_intake", "build_deferred_intake",
           "build_intake_classification")
