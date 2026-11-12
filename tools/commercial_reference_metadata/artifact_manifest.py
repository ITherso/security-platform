"""Three minimized payloads, with their completion manifest published last."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from .consumer_contracts import InputError, MANIFEST_SCHEMA, MAX_MANIFEST_BYTES, common, json_bytes, validate_documents
from .output_renderer import render_summary

PAYLOAD_NAMES = ("reference-metadata-response.json", "metadata-selection-ledger.json", "metadata-summary.md")


def _identity(raw: bytes) -> dict:
    import hashlib
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(response: dict, selection: dict, payloads: dict) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("reference_metadata_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, response["source_reference"]),
            "files": [{"name": name, **_identity(raw)} for name, raw in payloads.items()],
            "response_counts": response["counts"], "selection_counts": selection["counts"],
            "manifest_self_excluded": True, "source_contents_embedded": False,
            "completion_marker": "Published last. Three explicit minimized payload byte identities only.",
            "integrity_limit": "Internal output consistency only; no independent upstream guard, source observation, physical identity, compiler, producer, ownership or release acceptance."}


def publish_metadata(output: Path, response: dict, selection: dict) -> None:
    validate_documents(response, selection)
    payloads = {"reference-metadata-response.json": json_bytes(response), "metadata-selection-ledger.json": json_bytes(selection),
                "metadata-summary.md": render_summary(response, selection)}
    documents = {**payloads, "manifest.json": json_bytes(manifest_data(response, selection, payloads), maximum=MAX_MANIFEST_BYTES)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("reference_metadata_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".reference-metadata-stage-", dir=output.parent))
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
