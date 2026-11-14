"""Prepare source-bound follow-up requests from complete disclosed witnesses."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from followup_contracts import (
    LIMITATIONS, MAX_QUEUE_BYTES, QUEUE_SCHEMA, InputError, common,
    derive_followup_tasks, fixed, followup_counts, json_bytes, parse_json,
    validate_queue, validate_request,
)

if TYPE_CHECKING:
    from phase39_adapter import ValidatedPhase39Source


def _validated_queue(raw_bytes: bytes) -> dict:
    if type(raw_bytes) is not bytes:
        raise InputError("evidence_followup_exact_immutable_queue_bytes_required")
    return validate_queue(parse_json(raw_bytes, maximum=MAX_QUEUE_BYTES))


@dataclass(frozen=True, slots=True)
class ValidatedFollowupQueue:
    """Exact closed queue bytes without mutable approval or model markers.

    Direct construction validates new-wire correspondence only. It does not
    reobserve the source, independently establish task necessity, or authorize
    an observation, assignment, collection or fulfillment.
    """

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_queue(self.raw_bytes)


def read_followup_queue(snapshot: ValidatedFollowupQueue) -> dict:
    if type(snapshot) is not ValidatedFollowupQueue:
        raise InputError("evidence_followup_exact_validated_queue_required")
    return deepcopy(_validated_queue(snapshot.raw_bytes))


def build_followup_queue(validated_source: ValidatedPhase39Source,
                          request: dict) -> ValidatedFollowupQueue:
    """Prepare only tasks supported by the selected actual source witnesses."""
    from phase39_adapter import read_source

    request = validate_request(request)
    _query, witnesses, _receipt, source_artifacts = read_source(validated_source)
    # The witness occupies role 1. Role 0 is a different actual file: QUERY.
    fixed(request["source_phase39_witnesses_sha256"], source_artifacts[1]["sha256"],
          "evidence_followup_actual_Phase39_witnesses_identity")
    fixed(request["source_phase39_manifest_sha256"], source_artifacts[-1]["sha256"],
          "evidence_followup_actual_Phase39_manifest_identity")
    requested_ids = request["requested_reference_ids"]
    source_ids = {packet["reference_id"] for packet in witnesses["results"]}
    if any(reference_id not in source_ids for reference_id in requested_ids):
        raise InputError("evidence_followup_reference_outside_source_witnesses")
    requested_set = set(requested_ids)
    reference_packets = [deepcopy(packet) for packet in witnesses["results"]
                         if packet["reference_id"] in requested_set]
    fixed([packet["reference_id"] for packet in reference_packets], sorted(requested_ids),
          "evidence_followup_complete_selected_reference_packets")
    # This narrow owner helper rejects every unsupported missing projection;
    # there is no partial request or arbitrary candidate selection.
    tasks = derive_followup_tasks(reference_packets)
    queue = validate_queue({
        **common(QUEUE_SCHEMA),
        "source_phase39_witnesses_sha256": source_artifacts[1]["sha256"],
        "source_phase39_manifest_sha256": source_artifacts[-1]["sha256"],
        "request": request,
        "reference_packets": reference_packets,
        "followup_tasks": tasks,
        "counts": followup_counts(reference_packets, tasks),
        "limitations": list(LIMITATIONS),
    })
    return ValidatedFollowupQueue(json_bytes(queue, maximum=MAX_QUEUE_BYTES))


__all__ = ("ValidatedFollowupQueue", "read_followup_queue", "build_followup_queue")
