"""Fixed co-reference payload identities and preserved exclusive publication."""
from __future__ import annotations

import hashlib
import os

from capsule_manifest import _publish, check_path, explicit_path
from co_reference_contracts import (
    InputError, MANIFEST_SCHEMA, MAX_JOIN_BYTES, MAX_LOOKUP_BYTES,
    MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES,
    common, json_bytes, fixed, validate_request, validate_relationships,
)

PAYLOAD_NAMES = ("co-reference-join.json", "co-reference-lookup.json",
                 "co-reference-source-receipt.json", "co-reference-summary.md")
OUTPUT_NAMES = (*PAYLOAD_NAMES, "manifest.json")
_LIMITS = dict(zip(OUTPUT_NAMES, (MAX_JOIN_BYTES, MAX_LOOKUP_BYTES,
                                MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES)))


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(join: dict, lookup: dict, receipt: dict,
                  payloads: dict, request: dict) -> dict:
    join, lookup, receipt = validate_relationships(join, lookup, receipt)
    request = validate_request(request)
    for key in ("source_index_sha256", "source_manifest_sha256", "requested_file_ids"):
        fixed(request[key], join[key], "co_reference_request_join_binding")
    if type(payloads) is not dict or tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("co_reference_payload_inventory_invalid")
    files = []
    for name, raw in payloads.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("co_reference_payload_size_invalid")
        files.append({"name": name, **byte_identity(raw)})
    return {**common(MANIFEST_SCHEMA), "files": files,
            "source_index_sha256": join["source_index_sha256"],
            "source_manifest_sha256": join["source_manifest_sha256"],
            "source_artifacts": join["source_artifacts"],
            "join_counts": join["counts"], "lookup_counts": lookup["counts"],
            "request": request, "manifest_self_excluded": True,
            "integrity_scope": "five_new_co_reference_outputs_internal_correspondence_only"}


def publish_co_reference(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        raise InputError("co_reference_output_inventory_invalid")
    for name, raw in documents.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("co_reference_output_size_invalid")
    output = explicit_path(raw_output_dir)
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("co_reference_output_must_be_new")
    _publish(output.parent, parent, documents, output)


def publish_inspection(raw_output: str, report: dict) -> None:
    output = explicit_path(raw_output)
    if output.suffix.lower() != ".json":
        raise InputError("co_reference_inspection_JSON_required")
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("co_reference_inspection_output_must_be_new")
    _publish(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_MANIFEST_BYTES)})
