"""Actual deferred-intake payload identities and exclusive local publication."""
from __future__ import annotations

import hashlib
import os

from capsule_manifest import _publish, check_path, explicit_path
from intake_contracts import (
    InputError, MANIFEST_SCHEMA, MAX_INTAKE_BYTES, MAX_CLASSIFICATION_BYTES,
    MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES,
    common, fixed, json_bytes, validate_relationships,
)

PAYLOAD_NAMES = ("deferred-intake-register.json", "intake-classification.json",
                 "intake-source-receipt.json", "intake-summary.md")
OUTPUT_NAMES = (*PAYLOAD_NAMES, "manifest.json")
_LIMITS = dict(zip(OUTPUT_NAMES, (MAX_INTAKE_BYTES, MAX_CLASSIFICATION_BYTES,
                                MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES)))


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(intake: dict, classification: dict, receipt: dict, payloads: dict) -> dict:
    intake, classification, receipt = validate_relationships(intake, classification, receipt)
    if type(payloads) is not dict or tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("deferred_intake_payload_inventory_invalid")
    files = []
    for name, raw in payloads.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("deferred_intake_payload_size_invalid")
        files.append({"name": name, **byte_identity(raw)})
    if payloads[PAYLOAD_NAMES[0]] != json_bytes(intake, maximum=MAX_INTAKE_BYTES):
        raise InputError("deferred_intake_payload_must_be_canonical")
    fixed(classification["intake_register_sha256"], files[0]["sha256"],
          "deferred_intake_actual_classification_identity")
    return {
        **common(MANIFEST_SCHEMA), "files": files,
        "source_phase41_slots_sha256": intake["source_phase41_slots_sha256"],
        "source_phase41_manifest_sha256": intake["source_phase41_manifest_sha256"],
        "source_artifacts": receipt["source_artifacts"],
        "source_schema_versions": receipt["source_schema_versions"],
        "source_counts": receipt["source_counts"],
        "intake_register_sha256": classification["intake_register_sha256"],
        "intake_counts": intake["counts"], "classification_counts": classification["counts"],
        "request": intake["request"], "manifest_self_excluded": True,
        "integrity_scope": "five_new_deferred_intake_outputs_internal_correspondence_only",
    }


def publish_deferred_intake(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        raise InputError("deferred_intake_output_inventory_invalid")
    for name, raw in documents.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("deferred_intake_output_size_invalid")
    output = explicit_path(raw_output_dir)
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("deferred_intake_output_must_be_new")
    _publish(output.parent, parent, documents, output)


def publish_inspection(raw_output: str, report: dict) -> None:
    output = explicit_path(raw_output)
    if output.suffix.lower() != ".json":
        raise InputError("deferred_intake_inspection_JSON_required")
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("deferred_intake_inspection_output_must_be_new")
    _publish(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_MANIFEST_BYTES)})
