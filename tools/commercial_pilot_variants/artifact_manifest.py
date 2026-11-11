"""Publish four bounded metadata payloads and a final byte-binding manifest."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_composition.artifact_manifest import identity
from .variant_contracts import InputError, MANIFEST_SCHEMA, common, json_bytes, validate_documents
from .output_renderer import render_summary

PAYLOAD_NAMES = ("variant-analysis.json", "dependency-exposure.json",
                 "license-readiness.json", "variant-comparison.md")


def manifest_data(analysis: dict, dependencies: dict, licenses: dict, payloads: dict[str, bytes]) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("pilot_variant_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, analysis["candidate_reference"]),
            "source_reference": analysis["source_reference"],
            "files": [{"name": name, **identity(raw)} for name, raw in payloads.items()],
            "source_counts": analysis["source_counts"],
            "variant_count": len(analysis["variants"]),
            "comparison_count": len(analysis["comparisons"]),
            "manifest_self_excluded": True, "source_contents_embedded": False,
            "completion_marker": "Published last. Four explicit payload byte bindings only.",
            "integrity_limit": "Internal byte/model consistency cannot establish original source, producer, dependency closure, legal clearance, build, runtime or distribution authority."}


def publish_variants(output: Path, analysis: dict, dependencies: dict, licenses: dict) -> None:
    validate_documents(analysis, dependencies, licenses)
    payloads = {"variant-analysis.json": json_bytes(analysis),
                "dependency-exposure.json": json_bytes(dependencies),
                "license-readiness.json": json_bytes(licenses),
                "variant-comparison.md": render_summary(analysis, dependencies, licenses)}
    documents = {**payloads, "manifest.json": json_bytes(
        manifest_data(analysis, dependencies, licenses, payloads), maximum=64 * 1024)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("pilot_variant_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".pilot-variant-stage-", dir=output.parent))
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
