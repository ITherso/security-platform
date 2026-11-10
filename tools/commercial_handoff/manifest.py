"""Byte identity metadata and bounded publication into a new local directory."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile

from .input_loader import LoadedInput, check_existing_path
from .schema import CONTRACT, InputError

DOCUMENT_NAMES = ("internal-review-summary.md", "client-handoff-draft.md",
                  "client-handoff-draft.html")
ALL_NAMES = DOCUMENT_NAMES + ("manifest.json",)
MAX_OUTPUT_BYTES = 4 * 1024 * 1024


def manifest_bytes(loaded: LoadedInput, documents: dict[str, bytes], blockers: tuple[str, ...]) -> bytes:
    if set(documents) != set(DOCUMENT_NAMES) or any(type(v) is not bytes or not 0 < len(v) <= MAX_OUTPUT_BYTES for v in documents.values()):
        raise InputError("invalid_rendered_output")
    data = {
        "schema_version": "termivar-handoff-output-manifest/v1",
        "tool_contract": CONTRACT,
        "input_sha256": loaded.sha256,
        "input_byte_length": loaded.byte_length,
        "files": [{"name": name, "bytes": len(documents[name]),
                   "sha256": hashlib.sha256(documents[name]).hexdigest()} for name in DOCUMENT_NAMES],
        "demo_only": True,
        "release_authorized": False,
        "human_review_verified": False,
        "delivery_blockers": list(blockers),
        "source_provenance_limitation": "Input metadata is an unverified assertion. Referenced source files were not opened; no native verifier, signature or source authentication was performed.",
        "integrity_limit": "SHA256 identifies these bytes only; it is not customer approval, a signature, a finding verdict or a certificate.",
        "completion_marker": "manifest.json is published last; its presence alone is not authentication. Check the declared file bytes before treating the set as complete.",
        "manifest_self_excluded": True,
    }
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _same_directory(path: Path, expected):
    current = check_existing_path(path, directory=True)
    if (current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino):
        raise InputError("output_directory_identity_changed")


def publish(output: Path, documents: dict[str, bytes], metadata: bytes):
    """Stage all bytes, reserve a new directory, link exclusively, manifest last.

    Existing directories, including empty ones, are never adopted. Hard links
    publish each complete file without replacement; unsupported filesystems fail.
    A failed run can leave a new partial directory, never a success report.
    Hostile filesystem races and all-platform ACL/durability acceptance remain open.
    """
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")
    if set(documents) != set(DOCUMENT_NAMES) or type(metadata) is not bytes or len(metadata) > MAX_OUTPUT_BYTES:
        raise InputError("invalid_output_inventory")
    payloads = {name: documents[name] for name in DOCUMENT_NAMES}
    payloads["manifest.json"] = metadata
    stage = Path(tempfile.mkdtemp(prefix=".handoff-stage-", dir=output.parent))
    stage_info = check_existing_path(stage, directory=True)
    try:
        for name in ALL_NAMES:
            _same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                stream.write(payloads[name])
                stream.flush()
                os.fsync(stream.fileno())
        _same_directory(output.parent, parent_info)
        output.mkdir(exist_ok=False)
        output_info = check_existing_path(output, directory=True)
        for name in ALL_NAMES:
            _same_directory(output.parent, parent_info)
            _same_directory(output, output_info)
            _same_directory(stage, stage_info)
            os.link(stage / name, output / name, follow_symlinks=False)
    finally:
        # Only fixed names in this run's own staging directory; no recursive delete.
        try:
            _same_directory(stage, stage_info)
            for name in ALL_NAMES:
                candidate = stage / name
                if os.path.lexists(candidate):
                    check_existing_path(candidate, directory=False)
                    candidate.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass  # Residual staging is not a secure deletion or cleanup guarantee.
