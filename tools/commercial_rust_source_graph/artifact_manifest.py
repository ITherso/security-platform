"""Bind four actual metadata payloads and publish a completion manifest last."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_composition.artifact_manifest import identity
from .source_graph_contracts import InputError, MANIFEST_SCHEMA, common, json_bytes, validate_documents
from .output_renderer import render_summary

PAYLOAD_NAMES = ("source-reference-ledger.json", "source-evidence-graph.json",
                 "module-coverage-projection.json", "source-graph-summary.md")


def manifest_data(ledger: dict, graph: dict, coverage: dict, payloads: dict) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("rust_source_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, ledger["source_reference"]),
            "files": [{"name": name, **identity(raw)} for name, raw in payloads.items()],
            "ledger_counts": ledger["counts"], "graph_counts": graph["counts"], "coverage_counts": coverage["counts"],
            "manifest_self_excluded": True, "source_contents_embedded": False,
            "completion_marker": "Published last. Four explicit payload byte identities only.",
            "integrity_limit": "Metadata consistency only; no independent lexical truth, Rust AST/module closure, producer, pinned Git, build, runtime or release acceptance."}


def publish_graph(output: Path, ledger: dict, graph: dict, coverage: dict) -> None:
    validate_documents(ledger, graph, coverage)
    payloads = {"source-reference-ledger.json": json_bytes(ledger), "source-evidence-graph.json": json_bytes(graph),
                "module-coverage-projection.json": json_bytes(coverage), "source-graph-summary.md": render_summary(ledger, graph, coverage)}
    documents = {**payloads, "manifest.json": json_bytes(manifest_data(ledger, graph, coverage, payloads), maximum=128 * 1024)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("rust_source_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".rust-source-graph-stage-", dir=output.parent))
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
