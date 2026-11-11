"""Bind four real metadata payloads, publishing the completion manifest last."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_composition.artifact_manifest import identity
from .coverage_contracts import InputError, MANIFEST_SCHEMA, common, json_bytes, validate_documents
from .output_renderer import render_summary

PAYLOAD_NAMES = ("entrypoint-coverage.json", "source-scope-delta.json",
                 "variant-entrypoint-projection.json", "entrypoint-summary.md")


def manifest_data(coverage: dict, delta: dict, variants: dict, payloads: dict) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("entrypoint_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, coverage["source_reference"]),
            "files": [{"name": name, **identity(raw)} for name, raw in payloads.items()],
            "coverage_counts": coverage["counts"], "delta_counts": delta["counts"],
            "variant_count": len(variants["variants"]),
            "manifest_self_excluded": True, "source_contents_embedded": False,
            "completion_marker": "Published last. Four explicit payload byte identities only.",
            "integrity_limit": "Internal metadata consistency only. No source producer, pinned Git attestation, ownership, build, runtime, legal or release acceptance."}


def publish_coverage(output: Path, coverage: dict, delta: dict, variants: dict) -> None:
    validate_documents(coverage, delta, variants)
    payloads = {"entrypoint-coverage.json": json_bytes(coverage),
                "source-scope-delta.json": json_bytes(delta),
                "variant-entrypoint-projection.json": json_bytes(variants),
                "entrypoint-summary.md": render_summary(coverage, delta, variants)}
    documents = {**payloads, "manifest.json": json_bytes(
        manifest_data(coverage, delta, variants, payloads), maximum=128 * 1024)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("entrypoint_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".entrypoint-coverage-stage-", dir=output.parent))
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
        # Remove only temporary files created above; never existing/user inputs.
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
