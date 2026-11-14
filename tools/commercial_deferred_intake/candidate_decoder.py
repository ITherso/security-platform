"""Future in-memory structural decoding; no observation or authority proof."""
from __future__ import annotations

from capsule_contracts import MAX_NEW_STRING
from slot_contracts import (
    InputError, sha256, submission_contract, task_id as validate_task_id,
)
from response_slot_builder import ValidatedResponseSlots, read_response_slots


_RESULTS = (
    "structurally_compatible_unverified", "unknown_task", "binding_mismatch",
    "invalid_field_set", "invalid_field_type", "invalid_field_value",
    "duplicate_task_candidate",
)


def _classification(task_identity: str | None, binding_identity: str | None,
                    structural_result: str) -> dict:
    """Close only the future memory result; the demo wire has stricter states."""
    if structural_result not in _RESULTS:
        raise InputError("deferred_candidate_unknown_structural_result")
    if task_identity is not None:
        validate_task_id(task_identity)
    if binding_identity is not None:
        sha256(binding_identity, "deferred_candidate_result_binding")
    return {
        "task_id": task_identity,
        "binding_digest": binding_identity,
        "intake_status": "candidate_supplied",
        "structural_result": structural_result,
        "observation_verified": False,
        "task_completed": False,
    }


def decode_candidate_response(validated_slots: ValidatedResponseSlots,
                               candidate_object: object) -> dict:
    """Check one future object without retaining it or changing source slots.

    The owner snapshot is wire-only context. This stateless single-object API
    cannot recover duplicate JSON keys or detect earlier submissions/replay.
    A timestamp is only a bounded nonempty string, with no date, freshness or
    locator semantics. This function is not called by either demo product CLI.
    """
    slots = read_response_slots(validated_slots)
    fields = submission_contract()
    if (type(candidate_object) is not dict
            or any(type(key) is not str for key in candidate_object)
            or set(candidate_object) != set(fields)):
        return _classification(None, None, "invalid_field_set")
    candidate = dict(candidate_object)
    if (any(type(candidate[key]) is not str for key in fields
            if key != "evidence_sha256_if_available")
            or (candidate["evidence_sha256_if_available"] is not None
                and type(candidate["evidence_sha256_if_available"]) is not str)):
        return _classification(None, None, "invalid_field_type")
    try:
        for value in candidate.values():
            if type(value) is str:
                if len(value) > MAX_NEW_STRING:
                    return _classification(None, None, "invalid_field_value")
                value.encode("utf-8", "strict")
        for key in ("observation_recorded_at", "observation_method", "source_locator_description"):
            if not candidate[key]:
                return _classification(None, None, "invalid_field_value")
        validate_task_id(candidate["task_id"])
        sha256(candidate["binding_digest"], "deferred_candidate_binding")
        if candidate["reported_presence"] not in ("present", "missing"):
            return _classification(None, None, "invalid_field_value")
        if candidate["evidence_sha256_if_available"] is not None:
            sha256(candidate["evidence_sha256_if_available"], "deferred_candidate_optional_evidence")
    except (InputError, UnicodeError):
        return _classification(None, None, "invalid_field_value")

    matches = [slot for slot in slots["response_slots"]
               if slot["task_id"] == candidate["task_id"]]
    if not matches:
        return _classification(candidate["task_id"], None, "unknown_task")
    if len(matches) != 1:
        # A valid exact owner snapshot rejects this ambiguity before reaching
        # here. This is no across-call duplicate registry or replay guarantee.
        return _classification(candidate["task_id"], None, "duplicate_task_candidate")
    slot = matches[0]
    if candidate["binding_digest"] != slot["binding_digest"]:
        return _classification(slot["task_id"], slot["binding_digest"], "binding_mismatch")
    return _classification(slot["task_id"], slot["binding_digest"],
                           "structurally_compatible_unverified")


__all__ = ("decode_candidate_response",)
