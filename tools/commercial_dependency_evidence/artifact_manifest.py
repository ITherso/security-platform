"""Bind four bounded metadata payloads; publication grants no release authority."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_composition.artifact_manifest import identity
from .evidence_contracts import InputError, MANIFEST_SCHEMA, common, json_bytes, validate_documents
from .graph_renderer import render_summary

PAYLOAD_NAMES = ("direct-dependency-evidence.json", "source-evidence-graph.json",
                 "variant-dependency-evidence.json", "dependency-evidence-summary.md")


def manifest_data(evidence: dict, graph: dict, variants: dict, payloads: dict[str, bytes]) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("dependency_evidence_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, evidence["source_reference"]),
            "files": [{"name": name, **identity(raw)} for name, raw in payloads.items()],
            "source_manifest_count": len(evidence["source_manifests"]),
            "declaration_count": len(evidence["declarations"]),
            "phase24_record_count": len(evidence["phase24_records"]),
            "graph_node_count": len(graph["nodes"]), "graph_edge_count": len(graph["edges"]),
            "variant_count": len(variants["variants"]),
            "manifest_self_excluded": True, "source_contents_embedded": False,
            "completion_marker": "Published last. Four explicit payload byte identities only.",
            "integrity_limit": "No independent original-source, producer, Cargo resolution, build closure, binary inclusion, legal review or distribution authority is established."}


def publish_evidence(output: Path, evidence: dict, graph: dict, variants: dict) -> None:
    validate_documents(evidence, graph, variants)
    payloads = {"direct-dependency-evidence.json": json_bytes(evidence),
                "source-evidence-graph.json": json_bytes(graph),
                "variant-dependency-evidence.json": json_bytes(variants),
                "dependency-evidence-summary.md": render_summary(evidence, graph, variants)}
    documents = {**payloads, "manifest.json": json_bytes(
        manifest_data(evidence, graph, variants, payloads), maximum=64 * 1024)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("dependency_evidence_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".dependency-evidence-stage-", dir=output.parent))
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
