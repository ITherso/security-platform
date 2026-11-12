"""Publish the three candidate-revalidation payloads and manifest last."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_composition.artifact_manifest import identity
from .revalidation_contracts import InputError, MANIFEST_SCHEMA, MAX_MANIFEST_BYTES, common, json_bytes, validate_documents
from .output_renderer import render_summary

PAYLOAD_NAMES = ("revalidation-ledger.json", "evidence-reuse.json", "revalidation-summary.md")


def manifest_data(ledger: dict, reuse: dict, payloads: dict) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("revalidation_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, ledger["source_reference"]),
            "files": [{"name": name, **identity(raw)} for name, raw in payloads.items()],
            "ledger_counts": ledger["counts"], "reuse_counts": reuse["counts"],
            "manifest_self_excluded": True, "source_contents_embedded": False,
            "completion_marker": "Published last. Three explicit payload byte identities only.",
            "integrity_limit": "Recorded comparison and reuse metadata only; no independent filesystem, historical physical identity, reference context, compiler, producer, ownership, build/runtime or release acceptance."}


def publish_revalidation(output: Path, ledger: dict, reuse: dict) -> None:
    validate_documents(ledger, reuse)
    payloads = {"revalidation-ledger.json": json_bytes(ledger), "evidence-reuse.json": json_bytes(reuse),
                "revalidation-summary.md": render_summary(ledger, reuse)}
    documents = {**payloads, "manifest.json": json_bytes(manifest_data(ledger, reuse, payloads), maximum=MAX_MANIFEST_BYTES)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("revalidation_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".candidate-revalidation-stage-", dir=output.parent))
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
