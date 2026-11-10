"""Fixed offline desk output inventories and no-overwrite publication."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_handoff.schema import InputError


_OPERATIONS = {
    "prepare_desk": ("review-desk.html", "desk-manifest.json", ("review_packet", "packet_manifest", "overlay_template"), 2 * 1024 * 1024),
    "finalize_desk": ("decision-overlay.json", "overlay-manifest.json", ("review_packet", "packet_manifest", "handoff_input", "decision_draft"), 256 * 1024),
}
_LABEL = "DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED"


def _digest(value):
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise InputError("desk_invalid_manifest_digest")
    return value


def _count(value, maximum):
    if type(value) is not int or not 0 <= value <= maximum:
        raise InputError("desk_invalid_manifest_count")
    return value


def publish_desk(output: Path, documents: dict[str, bytes], operation: str, metadata: dict):
    """Publish one payload and its last-written manifest in a new directory.

    Only fixed inventories are supported. Failed runs may leave their new
    partial output or staging; no secure cleanup or hostile-race claim follows.
    """
    if type(operation) is not str or operation not in _OPERATIONS:
        raise InputError("desk_invalid_output_operation")
    name, manifest_name, roles, maximum = _OPERATIONS[operation]
    if (type(documents) is not dict or set(documents) != {name}
            or type(documents[name]) is not bytes or not 0 < len(documents[name]) <= maximum):
        raise InputError("desk_invalid_output_inventory")
    if type(metadata) is not dict or set(metadata) != {"inputs", "source_assessment_digest", "observation_count", "decision_count"}:
        raise InputError("desk_invalid_output_metadata")
    inputs = metadata["inputs"]
    if type(inputs) is not dict or set(inputs) != set(roles):
        raise InputError("desk_invalid_input_inventory")
    checked_inputs = {}
    for role in roles:
        row = inputs[role]
        cap = 64 * 1024 if role == "packet_manifest" else 256 * 1024
        if type(row) is not dict or set(row) != {"sha256", "byte_length"}:
            raise InputError("desk_invalid_input_identity")
        size = _count(row["byte_length"], cap)
        if not size:
            raise InputError("desk_invalid_input_identity")
        checked_inputs[role] = {"sha256": _digest(row["sha256"]), "byte_length": size}
    observations = _count(metadata["observation_count"], 256)
    decisions = _count(metadata["decision_count"], observations)
    if operation == "prepare_desk" and decisions:
        raise InputError("desk_empty_template_required")
    digest = hashlib.sha256(documents[name]).hexdigest()
    data = {
        "schema_version": "termivar-review-desk-output-manifest/v1",
        "operation": operation,
        "inputs": checked_inputs,
        "review_packet_digest": checked_inputs["review_packet"]["sha256"],
        "source_assessment_digest": _digest(metadata["source_assessment_digest"]),
        "observation_count": observations,
        "decision_count": decisions,
        "files": [{"name": name, "bytes": len(documents[name]), "sha256": digest}],
        "output_files": [name, manifest_name],
        "manifest_self_excluded": True,
        "mode": "demo", "demo_only": True, "demo_label": _LABEL,
        "human_review_verified": False, "producer_verified": False,
        "release_authorized": False, "native_assessment_verified": False,
        "full_bundle_verified": False,
        "packet_manifest_validation_scope": "explicit_packet_entry_only",
        "integrity_limit": "Hashes bind explicitly selected files and generated payload bytes only. No producer, reviewer, decision, authorized scope or release is authenticated. Source references and manifest entry names are never opened automatically.",
        "completion_marker": "This manifest is published last. Its presence is not authentication; compare the declared payload bytes before treating this output set as complete.",
    }
    raw = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > 64 * 1024:
        raise InputError("desk_manifest_size_limit")
    payloads = {name: documents[name], manifest_name: raw}
    names = (name, manifest_name)
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".review-desk-stage-", dir=output.parent))
    stage_info = check_existing_path(stage, directory=True)
    try:
        for item in names:
            _same_directory(stage, stage_info)
            with (stage / item).open("xb") as stream:
                stream.write(payloads[item])
                stream.flush()
                os.fsync(stream.fileno())
        _same_directory(output.parent, parent_info)
        output.mkdir(exist_ok=False)
        output_info = check_existing_path(output, directory=True)
        for item in names:
            _same_directory(output.parent, parent_info)
            _same_directory(output, output_info)
            _same_directory(stage, stage_info)
            os.link(stage / item, output / item, follow_symlinks=False)
    finally:
        try:
            _same_directory(stage, stage_info)
            for item in names:
                candidate = stage / item
                if os.path.lexists(candidate):
                    check_existing_path(candidate, directory=False)
                    candidate.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass

