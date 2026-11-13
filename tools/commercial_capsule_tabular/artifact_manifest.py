"""Fixed four-payload tabular manifest and existing exclusive publication."""
from __future__ import annotations

import hashlib
import os

from capsule_manifest import _publish, check_path, explicit_path
from tabular_contracts import (
    InputError, MANIFEST_SCHEMA, MAX_DATASET_BYTES, MAX_CSV_BYTES,
    MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES, common, json_bytes, validate_dataset,
)

PAYLOAD_NAMES = ("tabular-dataset.json", "reference-register.csv", "projection-register.csv", "tabular-summary.md")
OUTPUT_NAMES = (*PAYLOAD_NAMES, "manifest.json")
_LIMITS = {PAYLOAD_NAMES[0]: MAX_DATASET_BYTES, PAYLOAD_NAMES[1]: MAX_CSV_BYTES,
           PAYLOAD_NAMES[2]: MAX_CSV_BYTES, PAYLOAD_NAMES[3]: MAX_SUMMARY_BYTES,
           "manifest.json": MAX_MANIFEST_BYTES}


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(dataset: dict, payloads: dict) -> dict:
    dataset = validate_dataset(dataset)
    if type(payloads) is not dict or tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("tabular_payload_inventory_invalid")
    files = []
    for name, raw in payloads.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("tabular_payload_size_invalid")
        files.append({"name": name, **byte_identity(raw)})
    return {**common(MANIFEST_SCHEMA), "files": files,
            "source_capsule": dataset["source_capsule"], "counts": dataset["counts"],
            "reference_data_rows": len(dataset["reference_records"]),
            "projection_data_rows": len(dataset["projection_records"]),
            "csv_encoding": dataset["csv_encoding"], "manifest_self_excluded": True,
            "integrity_scope": "capsule_to_dataset_and_tabular_byte_correspondence_only"}


def publish_tabular(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        raise InputError("tabular_output_inventory_invalid")
    for name, raw in documents.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("tabular_output_size_invalid")
    output = explicit_path(raw_output_dir)
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("tabular_output_must_be_new")
    _publish(output.parent, parent, documents, output)


def publish_inspection(raw_output: str, report: dict) -> None:
    output = explicit_path(raw_output)
    if output.suffix.lower() != ".json":
        raise InputError("tabular_inspection_JSON_required")
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("tabular_inspection_output_must_be_new")
    _publish(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_MANIFEST_BYTES)})
