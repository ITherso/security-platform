"""Fixed cohort payload inventory and preserved exclusive publication."""
from __future__ import annotations

import hashlib
import os

from capsule_manifest import _publish, check_path, explicit_path
from cohort_contracts import (
    InputError, MANIFEST_SCHEMA, MAX_QUERY_BYTES, MAX_WITNESSES_BYTES,
    MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES,
    common, json_bytes, validate_relationships,
)

PAYLOAD_NAMES = ("cohort-query.json", "cohort-witnesses.json",
                 "cohort-source-receipt.json", "cohort-summary.md")
OUTPUT_NAMES = (*PAYLOAD_NAMES, "manifest.json")
_LIMITS = dict(zip(OUTPUT_NAMES, (MAX_QUERY_BYTES, MAX_WITNESSES_BYTES,
                                MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES)))


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(query: dict, witnesses: dict, receipt: dict, payloads: dict) -> dict:
    query, witnesses, receipt = validate_relationships(query, witnesses, receipt)
    if type(payloads) is not dict or tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("cohort_payload_inventory_invalid")
    files = []
    for name, raw in payloads.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("cohort_payload_size_invalid")
        files.append({"name": name, **byte_identity(raw)})
    return {
        **common(MANIFEST_SCHEMA), "files": files,
        "source_phase38_join_sha256": query["source_phase38_join_sha256"],
        "source_phase38_manifest_sha256": query["source_phase38_manifest_sha256"],
        "source_artifacts": receipt["source_artifacts"],
        "query_counts": query["counts"], "request": query["request"],
        "manifest_self_excluded": True,
        "integrity_scope": "five_new_cohort_outputs_internal_correspondence_only",
    }


def publish_cohort_query(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        raise InputError("cohort_output_inventory_invalid")
    for name, raw in documents.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("cohort_output_size_invalid")
    output = explicit_path(raw_output_dir)
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("cohort_output_must_be_new")
    _publish(output.parent, parent, documents, output)


def publish_inspection(raw_output: str, report: dict) -> None:
    output = explicit_path(raw_output)
    if output.suffix.lower() != ".json":
        raise InputError("cohort_inspection_JSON_required")
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("cohort_inspection_output_must_be_new")
    _publish(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_MANIFEST_BYTES)})
