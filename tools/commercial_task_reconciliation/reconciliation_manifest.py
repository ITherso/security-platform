"""Output byte identities, the output manifest and exclusive new-directory publication."""
from __future__ import annotations

import hashlib
import os

from exchange_contracts import InputError, json_bytes
from local_task_records import LocalReference
from reconciliation_contracts import (
    INTEGRITY_SCOPE, MAX_INBOX_BYTES, MAX_INSPECTION_BYTES, MAX_OUTPUT_MANIFEST_BYTES, MAX_REPORT_BYTES,
    MAX_SUMMARY_BYTES, OUTPUT_MANIFEST_SCHEMA, OUTPUT_NAMES, OUTPUT_PAYLOAD_NAMES, common, fail,
    validate_inbox, validate_output_manifest, validate_report,
)
from reconciliation_renderer import render_reconciliation_summary

OUTPUT_LIMITS = dict(zip(OUTPUT_NAMES, (MAX_INBOX_BYTES, MAX_REPORT_BYTES, MAX_SUMMARY_BYTES, MAX_OUTPUT_MANIFEST_BYTES)))


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def input_identities(capsule: bytes, request_raw: bytes, local: LocalReference) -> list:
    record = local.record()
    inputs = [{"role": "untrusted_capsule", **byte_identity(capsule)},
              {"role": "reconciliation_request", **byte_identity(request_raw)}]
    for group in ("phase42", "phase43"):
        if record[group] is not None:
            inputs.extend(dict(item) for item in record[group]["inputs"])
    return inputs


def output_documents(report: dict, inbox: dict, inputs: list) -> dict[str, bytes]:
    """Canonical bytes of the four outputs; the manifest excludes itself."""
    report, inbox = validate_report(report), validate_inbox(inbox)
    payloads = {
        OUTPUT_PAYLOAD_NAMES[0]: json_bytes(inbox, maximum=MAX_INBOX_BYTES),
        OUTPUT_PAYLOAD_NAMES[1]: json_bytes(report, maximum=MAX_REPORT_BYTES),
        OUTPUT_PAYLOAD_NAMES[2]: render_reconciliation_summary(report, inbox),
    }
    manifest = validate_output_manifest({
        **common(OUTPUT_MANIFEST_SCHEMA), "request_reference": report["request_reference"],
        "capsule": dict(report["capsule"]), "eligibility_status": report["eligibility"]["status"],
        "files": [{"name": name, **byte_identity(raw)} for name, raw in payloads.items()],
        "inputs": inputs, "manifest_self_excluded": True, "integrity_scope": INTEGRITY_SCOPE,
    }, report["local_reference"]["mode"])
    documents = {**payloads, OUTPUT_NAMES[3]: json_bytes(manifest, maximum=MAX_OUTPUT_MANIFEST_BYTES)}
    for name, raw in documents.items():
        if not 0 < len(raw) <= OUTPUT_LIMITS[name]:
            fail("output_size")
    return documents


def publish_outputs(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    """Publish into a new directory through the existing owner publisher."""
    from capsule_manifest import InputError as OwnerPublicationError, _publish, check_path, explicit_path

    if type(documents) is not dict or tuple(documents) != OUTPUT_NAMES:
        fail("output_inventory")
    try:
        output = explicit_path(raw_output_dir)
        parent = check_path(output.parent, directory=True)
        if os.path.lexists(output):
            fail("output_directory_must_be_new")
        _publish(output.parent, parent, documents, output)
    except OwnerPublicationError:
        raise InputError("task_reconciliation_publication_path_or_state_rejected") from None


def publish_inspection(raw_output: str, report: dict) -> None:
    from capsule_manifest import InputError as OwnerPublicationError, _publish, check_path, explicit_path

    try:
        output = explicit_path(raw_output)
        if output.suffix.lower() != ".json":
            fail("inspection_json_required")
        parent = check_path(output.parent, directory=True)
        if os.path.lexists(output):
            fail("inspection_output_must_be_new")
        _publish(output.parent, parent, {output.name: json_bytes(report, maximum=MAX_INSPECTION_BYTES)})
    except OwnerPublicationError:
        raise InputError("task_reconciliation_inspection_publication_rejected") from None


__all__ = ("OUTPUT_LIMITS", "byte_identity", "input_identities", "output_documents", "publish_inspection",
           "publish_outputs")
