"""Actual exchange output identities and exclusive producer-side publication."""
from __future__ import annotations

import hashlib
import os

from capsule_manifest import (
    InputError as OwnerPublicationError, _publish, check_path, explicit_path,
)
from exchange_contracts import (
    InputError, MANIFEST_SCHEMA, MAX_CAPSULE_BYTES, MAX_INDEX_BYTES,
    MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES,
    common, fixed, json_bytes, validate_relationships,
)
from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request

PAYLOAD_NAMES = ("task-exchange-capsule.zip", "task-exchange-index.json",
                 "task-exchange-source-receipt.json", "task-exchange-summary.md")
OUTPUT_NAMES = (*PAYLOAD_NAMES, "manifest.json")
_LIMITS = dict(zip(OUTPUT_NAMES, (MAX_CAPSULE_BYTES, MAX_INDEX_BYTES,
                                MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES)))


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(capsule_bytes: bytes, index: dict, receipt: dict, payloads: dict) -> dict:
    snapshot = inspect_task_exchange_capsule(capsule_bytes)
    envelope, _contract, inner_artifacts = read_portable_task_request(snapshot)
    envelope, index, receipt = validate_relationships(envelope, index, receipt)
    if type(payloads) is not dict or tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("task_exchange_payload_inventory_invalid")
    files = []
    for name, raw in payloads.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("task_exchange_payload_size_invalid")
        files.append({"name": name, **byte_identity(raw)})
    if payloads[PAYLOAD_NAMES[0]] != capsule_bytes:
        raise InputError("task_exchange_actual_capsule_payload_mismatch")
    if payloads[PAYLOAD_NAMES[1]] != json_bytes(index, maximum=MAX_INDEX_BYTES):
        raise InputError("task_exchange_index_payload_must_be_canonical")
    fixed(index["capsule_sha256"], files[0]["sha256"], "task_exchange_actual_capsule_index_identity")
    return {
        **common(MANIFEST_SCHEMA), "files": files,
        "source_phase42_register_sha256": envelope["source_phase42_register_sha256"],
        "source_phase42_manifest_sha256": envelope["source_phase42_manifest_sha256"],
        "source_artifacts": receipt["source_artifacts"],
        "source_schema_versions": receipt["source_schema_versions"],
        "source_counts": receipt["source_counts"],
        "capsule_sha256": index["capsule_sha256"], "capsule_members": inner_artifacts,
        "task_ids": index["task_ids"], "counts": index["counts"],
        "request_reference": envelope["request_reference"], "manifest_self_excluded": True,
        "integrity_scope": "five_new_task_exchange_outputs_and_capsule_internal_correspondence_only",
    }


def publish_task_exchange(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        raise InputError("task_exchange_output_inventory_invalid")
    for name, raw in documents.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("task_exchange_output_size_invalid")
    try:
        output = explicit_path(raw_output_dir)
        parent = check_path(output.parent, directory=True)
        if os.path.lexists(output):
            raise InputError("task_exchange_output_must_be_new")
        _publish(output.parent, parent, documents, output)
    except OwnerPublicationError:
        raise InputError("task_exchange_publication_path_or_state_rejected") from None


def publish_inspection(raw_output: str, report: dict) -> None:
    try:
        output = explicit_path(raw_output)
        if output.suffix.lower() != ".json":
            raise InputError("task_exchange_inspection_JSON_required")
        parent = check_path(output.parent, directory=True)
        if os.path.lexists(output):
            raise InputError("task_exchange_inspection_output_must_be_new")
        _publish(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_MANIFEST_BYTES)})
    except OwnerPublicationError:
        raise InputError("task_exchange_inspection_publication_rejected") from None
