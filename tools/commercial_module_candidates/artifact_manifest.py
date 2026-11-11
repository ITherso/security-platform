"""Publish four bounded candidate payloads with their manifest last."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_composition.artifact_manifest import identity
from .candidate_contracts import (
    InputError, MANIFEST_SCHEMA, MAX_MANIFEST_BYTES, common, json_bytes, validate_documents,
)
from .output_renderer import render_summary

PAYLOAD_NAMES = ("module-candidate-evidence.json", "candidate-triage.json", "candidate-coverage.json", "candidate-summary.md")


def manifest_data(evidence: dict, triage: dict, coverage: dict, payloads: dict) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("module_candidate_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, evidence["source_reference"]),
            "files": [{"name": name, **identity(raw)} for name, raw in payloads.items()],
            "evidence_counts": evidence["counts"], "triage_counts": triage["counts"], "coverage_counts": coverage["counts"],
            "manifest_self_excluded": True, "source_contents_embedded": False,
            "completion_marker": "Published last. Four explicit payload byte identities only.",
            "integrity_limit": "Metadata consistency only; no independent candidate filesystem, Rust lexical truth, compiler resolution, source completeness, producer, pinned Git, build, runtime or release acceptance."}


def publish_candidates(output: Path, evidence: dict, triage: dict, coverage: dict) -> None:
    validate_documents(evidence, triage, coverage)
    payloads = {"module-candidate-evidence.json": json_bytes(evidence), "candidate-triage.json": json_bytes(triage),
                "candidate-coverage.json": json_bytes(coverage), "candidate-summary.md": render_summary(evidence, triage, coverage)}
    documents = {**payloads, "manifest.json": json_bytes(manifest_data(evidence, triage, coverage, payloads), maximum=MAX_MANIFEST_BYTES)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("module_candidate_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".module-candidates-stage-", dir=output.parent))
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
