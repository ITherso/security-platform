"""Fixed, exclusive metadata payload publication; hashes grant no authority."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_composition.artifact_manifest import identity
from .evidence_contracts import InputError, MANIFEST_SCHEMA, common, json_bytes, validate_documents
from .output_renderer import render_summary

PAYLOAD_NAMES = ("license-evidence-ledger.json", "review-queue.json",
                 "binding-conflicts.json", "evidence-summary.md")


def manifest_data(ledger: dict, queue: dict, conflicts: dict, payloads: dict[str, bytes]) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("license_review_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, ledger["composition_reference"]),
            "files": [{"name": name, **identity(raw)} for name, raw in payloads.items()],
            "source_record_count": len(ledger["source_subjects"]),
            "evidence_source_count": len(ledger["evidence_sources"]),
            "binding_request_count": len(ledger["bindings"]),
            "manifest_self_excluded": True, "raw_evidence_embedded": False,
            "completion_marker": "Published last. Four explicit payload byte bindings only.",
            "integrity_limit": "No source producer, dependency applicability, legal review, license grant, build, runtime or release authority is authenticated."}


def publish_evidence(output: Path, ledger: dict, queue: dict, conflicts: dict) -> None:
    validate_documents(ledger, queue, conflicts)
    payloads = {"license-evidence-ledger.json": json_bytes(ledger),
                "review-queue.json": json_bytes(queue),
                "binding-conflicts.json": json_bytes(conflicts),
                "evidence-summary.md": render_summary(ledger, queue, conflicts)}
    documents = {**payloads, "manifest.json": json_bytes(
        manifest_data(ledger, queue, conflicts, payloads), maximum=64 * 1024)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("license_review_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".license-review-stage-", dir=output.parent))
    stage_info = check_existing_path(stage, directory=True)
    try:
        for name, raw in documents.items():
            _same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        _same_directory(output.parent, parent_info)
        output.mkdir(exist_ok=False)
        output_info = check_existing_path(output, directory=True)
        for name in documents:
            _same_directory(output.parent, parent_info)
            _same_directory(output, output_info)
            _same_directory(stage, stage_info)
            os.link(stage / name, output / name, follow_symlinks=False)
    finally:
        try:
            _same_directory(stage, stage_info)
            for name in documents:
                path = stage / name
                if os.path.lexists(path):
                    check_existing_path(path, directory=False)
                    path.unlink()
            stage.rmdir()
        except (OSError, ValueError):
            pass
