"""Publish a fixed local output set without overwriting existing files."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory

from .contracts import (
    ADAPTER_VERSION, DEMO_LABEL, SOURCE_ROLES, TRACEABILITY_CONTRACT,
    FileIdentity, InputError, file_identity_to_dict, json_bytes,
)


DOCUMENT_NAMES = ("traceability-ledger.json", "traceability-summary.md")
MANIFEST_NAME = "manifest.json"


def publish_traceability(output: Path, documents: dict[str, bytes],
                         sources: tuple[FileIdentity, ...]) -> None:
    """Stage only this run's fixed payloads and publish the manifest last.

    No directory-wide atomicity or hostile-race acceptance is claimed. A failed
    run may leave a new partial output. Existing output directories are refused.
    """
    if type(documents) is not dict or set(documents) != set(DOCUMENT_NAMES):
        raise InputError("traceability_invalid_output_inventory")
    for name in DOCUMENT_NAMES:
        cap = 128 * 1024 if name.endswith(".md") else 256 * 1024
        if type(documents[name]) is not bytes or not 0 < len(documents[name]) <= cap:
            raise InputError("traceability_invalid_output_payload")
    if (type(sources) is not tuple or len(sources) != len(SOURCE_ROLES)
            or any(type(source) is not FileIdentity for source in sources)
            or {source.role for source in sources} != set(SOURCE_ROLES)):
        raise InputError("traceability_invalid_source_inventory")
    by_role = {source.role: source for source in sources}
    manifest = {
        "schema_version": "termivar-assessment-traceability-manifest/v1",
        "adapter_version": ADAPTER_VERSION,
        "ledger_contract": TRACEABILITY_CONTRACT,
        "sources": [file_identity_to_dict(by_role[role]) for role in SOURCE_ROLES],
        "files": [{"name": name, "bytes": len(documents[name]),
                   "sha256": hashlib.sha256(documents[name]).hexdigest()}
                  for name in DOCUMENT_NAMES],
        "output_files": [*DOCUMENT_NAMES, MANIFEST_NAME],
        "manifest_self_excluded": True,
        "execution_binding": "not_established",
        "demo_label": DEMO_LABEL,
        "demo_only": True,
        "plan_execution_verified": False,
        "scope_fulfillment_verified": False,
        "authorization_verified": False,
        "human_review_verified": False,
        "producer_verified": False,
        "release_authorized": False,
        "execution_authorized": False,
        "production_ready": False,
        "plan_manifest_validation_scope": "plan_preflight_catalog_entries_only; summary_payload_not_read",
        "assessment_manifest_validation_scope": "selected_json_entry_and_summary_only; html_payload_not_read",
        "phase17_manifest_validation_scope": "explicit_mapping_and_handoff_payload_bytes_only",
        "integrity_limit": "Hashes and pointers bind selected bytes and metadata only. They authenticate neither producer, authorized scope, execution, finding accuracy nor review.",
        "completion_marker": "Published last. Compare payload byte sizes and hashes; a manifest alone proves neither complete publication nor execution linkage.",
    }
    payloads = {**documents, MANIFEST_NAME: json_bytes(manifest, maximum=64 * 1024)}
    names = (*DOCUMENT_NAMES, MANIFEST_NAME)
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".traceability-stage-", dir=output.parent))
    stage_info = check_existing_path(stage, directory=True)
    try:
        for name in names:
            _same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                stream.write(payloads[name])
                stream.flush()
                os.fsync(stream.fileno())
        _same_directory(output.parent, parent_info)
        output.mkdir(exist_ok=False)
        output_info = check_existing_path(output, directory=True)
        for name in names:
            _same_directory(output.parent, parent_info)
            _same_directory(output, output_info)
            _same_directory(stage, stage_info)
            os.link(stage / name, output / name, follow_symlinks=False)
    finally:
        try:
            _same_directory(stage, stage_info)
            for name in names:
                candidate = stage / name
                if os.path.lexists(candidate):
                    check_existing_path(candidate, directory=False)
                    candidate.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass
