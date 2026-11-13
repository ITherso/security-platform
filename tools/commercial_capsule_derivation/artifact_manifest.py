"""Fixed derivation output identities and existing exclusive publication."""
from __future__ import annotations

import hashlib
import os

from capsule_manifest import _publish, check_path, explicit_path
from derivation_contracts import (
    InputError, MANIFEST_SCHEMA, MAX_ZIP_BYTES, MAX_LEDGER_BYTES, MAX_SUMMARY_BYTES,
    MAX_MANIFEST_BYTES, common, json_bytes, validate_ledger,
)

PAYLOAD_NAMES = ("derived-reference-capsule.zip", "derivation-ledger.json", "derivation-summary.md")
OUTPUT_NAMES = (*PAYLOAD_NAMES, "manifest.json")
_LIMITS = {PAYLOAD_NAMES[0]: MAX_ZIP_BYTES, PAYLOAD_NAMES[1]: MAX_LEDGER_BYTES,
           PAYLOAD_NAMES[2]: MAX_SUMMARY_BYTES, "manifest.json": MAX_MANIFEST_BYTES}


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(ledger: dict, payloads: dict) -> dict:
    ledger = validate_ledger(ledger)
    if type(payloads) is not dict or tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("derivation_payload_inventory_invalid")
    files = []
    for name, raw in payloads.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("derivation_payload_size_invalid")
        files.append({"name": name, **byte_identity(raw)})
    if files[0]["sha256"] != ledger["derived_capsule"]["sha256"] or files[0]["bytes"] != ledger["derived_capsule"]["bytes"]:
        raise InputError("derivation_manifest_capsule_binding_invalid")
    return {**common(MANIFEST_SCHEMA, ledger["derivation_reference"]),
            "files": files, "source_capsule": ledger["source_capsule"],
            "derived_capsule": ledger["derived_capsule"],
            "source_counts": ledger["source_counts"], "derived_counts": ledger["derived_counts"],
            "subset_relation": ledger["subset_relation"], "manifest_self_excluded": True,
            "integrity_scope": "two_capsule_subset_and_internal_byte_correspondence_only"}


def publish_derivation(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        raise InputError("derivation_output_inventory_invalid")
    for name, raw in documents.items():
        if type(raw) is not bytes or not 0 < len(raw) <= _LIMITS[name]:
            raise InputError("derivation_output_size_invalid")
    output = explicit_path(raw_output_dir)
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("derivation_output_must_be_new")
    # Existing Phase33 publisher stages all bytes, exclusively links the three
    # payloads, and publishes the completion manifest last. No old file removal.
    _publish(output.parent, parent, documents, output)


def publish_inspection(raw_output: str, report: dict) -> None:
    output = explicit_path(raw_output)
    if output.suffix.lower() != ".json":
        raise InputError("derivation_inspection_json_required")
    parent = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("derivation_inspection_output_must_be_new")
    _publish(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_LEDGER_BYTES)})
