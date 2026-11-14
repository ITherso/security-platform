"""Immutable unsubmitted slots bound to actual Phase40 pending tasks."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from slot_contracts import (
    LIMITATIONS, MAX_SLOTS_BYTES, RECEIPT_SCHEMA, SLOTS_SCHEMA, InputError,
    common, fixed, json_bytes, parse_json, slot_counts, submission_contract,
    validate_receipt, validate_request, validate_slots,
)
from task_binding import derive_task_binding, validate_task_record

if TYPE_CHECKING:
    from phase40_adapter import ValidatedPhase40Source


def _validated_slots(raw_bytes: bytes) -> dict:
    if type(raw_bytes) is not bytes:
        raise InputError("response_slots_exact_immutable_bytes_required")
    return validate_slots(parse_json(raw_bytes, maximum=MAX_SLOTS_BYTES))


@dataclass(frozen=True, slots=True)
class ValidatedResponseSlots:
    """Closed new slot bytes without mutable validation or approval markers.

    Direct construction establishes internal wire correspondence only. It
    does not prove original queue membership, task necessity, authorization,
    external response receipt or any observation.
    """

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_slots(self.raw_bytes)


def read_response_slots(snapshot: ValidatedResponseSlots) -> dict:
    if type(snapshot) is not ValidatedResponseSlots:
        raise InputError("response_slots_exact_validated_snapshot_required")
    return deepcopy(_validated_slots(snapshot.raw_bytes))


def build_response_slots(validated_source: ValidatedPhase40Source,
                          request: dict) -> ValidatedResponseSlots:
    """Create only unsubmitted slots for exact tasks in the validated group."""
    from phase40_adapter import read_source

    request = validate_request(request)
    queue, _handoff, _receipt, source_artifacts = read_source(validated_source)
    queue_sha256 = source_artifacts[0]["sha256"]
    fixed(request["source_phase40_queue_sha256"], queue_sha256,
          "response_slot_actual_Phase40_queue_identity")
    fixed(request["source_phase40_manifest_sha256"], source_artifacts[-1]["sha256"],
          "response_slot_actual_Phase40_manifest_identity")
    selected_ids = request["selected_task_ids"]
    source_ids = {task["task_id"] for task in queue["followup_tasks"]}
    if any(task_id not in source_ids for task_id in selected_ids):
        raise InputError("response_slot_task_outside_original_queue")
    selected_set = set(selected_ids)
    # Preserve each original global F ID and original source order. Deriving
    # tasks again from a packet subset would incorrectly renumber those IDs.
    selected_tasks = [validate_task_record(task) for task in queue["followup_tasks"]
                      if task["task_id"] in selected_set]
    fixed([task["task_id"] for task in selected_tasks], sorted(selected_ids),
          "response_slot_complete_original_task_selection")
    related_references = {task["reference_id"] for task in selected_tasks}
    reference_packets = [deepcopy(packet) for packet in queue["reference_packets"]
                         if packet["reference_id"] in related_references]
    fixed([packet["reference_id"] for packet in reference_packets], sorted(related_references),
          "response_slot_complete_task_reference_packets")
    response_slots = [{
        "task_id": task["task_id"],
        "reference_id": task["reference_id"],
        "candidate_id": task["candidate_id"],
        "file_id": task["file_id"],
        "binding_digest": derive_task_binding(queue_sha256, task),
        "followup_kind": task["followup_kind"],
        "task_status": task["task_status"],
        "fulfillment_status": task["fulfillment_status"],
        "slot_status": "awaiting_external_response",
        "submission": None,
        "submission_contract": submission_contract(),
    } for task in selected_tasks]
    slots = validate_slots({
        **common(SLOTS_SCHEMA),
        "source_phase40_queue_sha256": queue_sha256,
        "source_phase40_manifest_sha256": source_artifacts[-1]["sha256"],
        "request": request,
        "reference_packets": reference_packets,
        "response_slots": response_slots,
        "counts": slot_counts(response_slots),
        "limitations": list(LIMITATIONS),
    })
    return ValidatedResponseSlots(json_bytes(slots, maximum=MAX_SLOTS_BYTES))


def make_source_receipt(validated_source: ValidatedPhase40Source,
                         validated_slots: ValidatedResponseSlots) -> dict:
    """Bind original queue/handoff counts without changing their denominators."""
    from phase40_adapter import read_source

    slots = read_response_slots(validated_slots)
    expected = read_response_slots(build_response_slots(validated_source, slots["request"]))
    fixed(slots, expected, "response_slot_receipt_original_source_correspondence")
    queue, handoff, _receipt, artifacts = read_source(validated_source)
    return validate_receipt({
        **common(RECEIPT_SCHEMA),
        "source_artifacts": [dict(item) for item in artifacts],
        "source_phase40_queue_sha256": artifacts[0]["sha256"],
        "source_phase40_manifest_sha256": artifacts[-1]["sha256"],
        "source_counts": {"queue_counts": dict(queue["counts"]),
                          "handoff_counts": dict(handoff["counts"])},
        "selected_task_count": len(slots["response_slots"]),
        "content_scope": "five_Phase40_artifact_internal_correspondence_only",
        "limitations": list(LIMITATIONS),
    })


__all__ = ("ValidatedResponseSlots", "read_response_slots", "build_response_slots", "make_source_receipt")
