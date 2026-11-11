"""Bind fixed payload bytes and publish only into a new output directory."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from .composition_contracts import InputError, common, json_bytes, validate_documents
from .composition_renderer import render_summary
from .source_inventory import read_explicit_text

PAYLOAD_NAMES = ("composition-inventory.json", "dependency-license-ledger.json",
                 "release-constraints.json", "composition-summary.md")
MANIFEST_SCHEMA = "termivar-offline-composition-manifest/v1"


def identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def manifest_data(inventory: dict, ledger: dict, constraints: dict,
                  payloads: dict[str, bytes]) -> dict:
    if tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("composition_payload_inventory_mismatch")
    return {**common(MANIFEST_SCHEMA, inventory["candidate_reference"]),
            "files": [{"name": name, **identity(raw)} for name, raw in payloads.items()],
            "source_scope": inventory["source_scope"],
            "counts": {"components": len(inventory["components"]),
                       "source_files": len(inventory["files"]),
                       "dependency_records": len(ledger["dependencies"]),
                       "license_evidence_records": len(ledger["license_evidence"]),
                       "open_blockers": len(constraints["blockers"])},
            "manifest_self_excluded": True,
            "source_contents_embedded": False,
            "completion_marker": "Published last. Four selected payload byte identities only.",
            "integrity_limit": "No original-source, producer, license, build, runtime or distribution authorization is independently verified."}


def publish_composition(output: Path, inventory: dict, ledger: dict, constraints: dict) -> None:
    validate_documents(inventory, ledger, constraints)
    payloads = {"composition-inventory.json": json_bytes(inventory),
                "dependency-license-ledger.json": json_bytes(ledger),
                "release-constraints.json": json_bytes(constraints),
                "composition-summary.md": render_summary(inventory, ledger, constraints)}
    documents = {**payloads, "manifest.json": json_bytes(
        manifest_data(inventory, ledger, constraints, payloads), maximum=64 * 1024)}
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("composition_output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".composition-stage-", dir=output.parent))
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
        except (OSError, InputError):
            pass


def read_payload(path: Path, maximum: int) -> bytes:
    raw, _ = read_explicit_text(path, maximum)
    return raw
