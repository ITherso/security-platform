"""Fixed follow-up payload identities and preserved exclusive publication."""
from __future__ import annotations

import hashlib
import os

from capsule_manifest import _publish, check_path, explicit_path
from followup_contracts import (
    InputError, MANIFEST_SCHEMA, MAX_QUEUE_BYTES, MAX_HANDOFF_BYTES,
    MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES,
    common, fixed, json_bytes, validate_relationships,
)

PAYLOAD_NAMES = ("evidence-followup-queue.json", "analyst-handoff.json",
                 "followup-source-receipt.json", "followup-summary.md")
OUTPUT_NAMES = (*PAYLOAD_NAMES, "manifest.json")
_LIMITS = dict(zip(OUTPUT_NAMES, (MAX_QUEUE_BYTES, MAX_HANDOFF_BYTES,
                                MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES)))


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(queue: dict, handoff: dict, receipt: dict, payloads: dict) -> dict:
    queue, handoff, receipt = validate_relationships(queue, handoff, receipt)
    if type(payloads) is not dict or tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("followup_payload_inventory_invalid")
    files = []
    for name, raw in payloads.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("followup_payload_size_invalid")
        files.append({"name": name, **byte_identity(raw)})
    if payloads[PAYLOAD_NAMES[0]] != json_bytes(queue, maximum=MAX_QUEUE_BYTES):
        raise InputError("followup_queue_payload_must_be_canonical")
    fixed(handoff["queue_sha256"], files[0]["sha256"], "followup_actual_queue_handoff_identity")
    return {
        **common(MANIFEST_SCHEMA), "files": files,
        "source_phase39_witnesses_sha256": queue["source_phase39_witnesses_sha256"],
        "source_phase39_manifest_sha256": queue["source_phase39_manifest_sha256"],
        "source_artifacts": receipt["source_artifacts"],
        "queue_sha256": handoff["queue_sha256"],
        "queue_counts": queue["counts"], "handoff_counts": handoff["counts"],
        "request": queue["request"], "manifest_self_excluded": True,
        "integrity_scope": "five_new_evidence_followup_outputs_internal_correspondence_only",
    }


def publish_evidence_followup(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        raise InputError("followup_output_inventory_invalid")
    for name, raw in documents.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("followup_output_size_invalid")
    output = explicit_path(raw_output_dir)
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("followup_output_must_be_new")
    _publish(output.parent, parent, documents, output)


def publish_inspection(raw_output: str, report: dict) -> None:
    output = explicit_path(raw_output)
    if output.suffix.lower() != ".json":
        raise InputError("followup_inspection_JSON_required")
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("followup_inspection_output_must_be_new")
    _publish(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_MANIFEST_BYTES)})
