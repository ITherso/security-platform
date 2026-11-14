"""Deterministic task correspondence, without signature or authority claims."""
from __future__ import annotations

from copy import deepcopy
import hashlib

from followup_contracts import (
    InputError, TASK_FIELDS, closed, digest_id, fixed, identifier, json_bytes,
    sha256,
)


def validate_task_record(task_record: object) -> dict:
    """Validate the exact original eight-field pending task, preserving its ID."""
    task = closed(task_record, TASK_FIELDS, "response_slot_original_task_fields")
    task_id = task["task_id"]
    if (type(task_id) is not str or len(task_id) != 5 or task_id[0] != "F"
            or not all("0" <= char <= "9" for char in task_id[1:])
            or not 1 <= int(task_id[1:]) <= 64):
        raise InputError("response_slot_original_task_id_invalid")
    digest_id(task["reference_id"], "rust-ref-", "response_slot_task_reference_id")
    identifier(task["candidate_id"], "response_slot_task_candidate_id")
    digest_id(task["file_id"], "candidate-file-", "response_slot_task_file_id")
    fixed(task["recorded_source_file_presence"], "missing", "response_slot_recorded_missing_only")
    fixed(task["followup_kind"], "request_fresh_source_observation", "response_slot_followup_kind")
    fixed(task["task_status"], "prepared_unassigned", "response_slot_unassigned_task_only")
    fixed(task["fulfillment_status"], "not_observed", "response_slot_unobserved_task_only")
    return deepcopy(task)


def derive_task_binding(source_queue_sha256: str, task_record: dict) -> str:
    """Hash exactly the queue identity and four original task identity fields."""
    sha256(source_queue_sha256, "response_slot_source_queue_sha256")
    task = validate_task_record(task_record)
    preimage = {
        "source_phase40_queue_sha256": source_queue_sha256,
        "task_id": task["task_id"],
        "reference_id": task["reference_id"],
        "candidate_id": task["candidate_id"],
        "file_id": task["file_id"],
    }
    return hashlib.sha256(json_bytes(preimage, maximum=4096)).hexdigest()


__all__ = ("validate_task_record", "derive_task_binding")
