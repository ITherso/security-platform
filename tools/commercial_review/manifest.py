"""Closed byte inventories and new-directory publication for demo review files.

Packet-manifest validation compares only the explicitly supplied packet bytes.
It never opens an entry name or authenticates a producer or human decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_handoff.schema import InputError
from commercial_intake.assessment_reader import JsonFile

from . import DEMO_LABEL, MAX_REVIEW_BYTES
from .review_contracts import DELIVERY_BLOCKERS, validate_packet


MAX_PAYLOAD_BYTES = 4 * 1024 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_PACKET_BYTES = MAX_REVIEW_BYTES
MAX_OBSERVATIONS = 256
_SHA256 = re.compile(r"[a-f0-9]{64}")
_PREPARE_INPUTS = ("handoff_input", "source_mapping", "intake_manifest")
_RECONCILE_INPUTS = ("review_packet", "packet_manifest", "handoff_input", "overlay")
_PREPARE_PAYLOADS = (
    "review-packet.json", "decision-overlay.template.json", "review-worksheet.md",
)
_RECONCILE_PAYLOADS = ("handoff-input.json", "review-reconciliation.md")
_PHASES = {
    "review-packet-manifest.json": (
        "termivar-analyst-review-packet-manifest/v1", _PREPARE_PAYLOADS,
        _PREPARE_INPUTS, "explicit_review_packet_entry_only",
    ),
    "reconciliation-manifest.json": (
        "termivar-analyst-reconciliation-manifest/v1", _RECONCILE_PAYLOADS,
        _RECONCILE_INPUTS, "generated_payload_byte_inventory_only",
    ),
}
_BLOCKERS = DELIVERY_BLOCKERS
_INTEGRITY_LIMIT = (
    "Hashes identify selected input and generated payload bytes only. They do not "
    "authenticate a source, producer, reviewer, decision, authorized scope or release. "
    "Reconciliation compares only the explicitly supplied packet entry; worksheet "
    "and overlay-template entries are not opened or verified. An overlay is read "
    "only when separately and explicitly supplied."
)
_MANIFEST_FIELDS = frozenset((
    "schema_version", "inputs", "source_assessment_sha256", "source_observation_count",
    "output_files", "files", "manifest_self_excluded", "demo_only", "demo_label",
    "human_review_verified", "producer_verified", "release_authorized",
    "full_bundle_verified", "validation_scope", "delivery_blockers", "integrity_limit",
))


@dataclass(frozen=True, slots=True)
class PacketManifestCheck:
    packet_entry_matches: bool = field(default=True, init=False)
    worksheet_payload_read: bool = field(default=False, init=False)
    overlay_template_payload_read: bool = field(default=False, init=False)
    full_bundle_verified: bool = field(default=False, init=False)
    producer_verified: bool = field(default=False, init=False)
    human_review_verified: bool = field(default=False, init=False)
    release_authorized: bool = field(default=False, init=False)


def _object(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise InputError("invalid_review_manifest_fields")
    return value


def _sha256(value) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise InputError("invalid_review_manifest_digest")
    return value


def _size(value, maximum: int = MAX_PAYLOAD_BYTES) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise InputError("invalid_review_manifest_byte_length")
    return value


def _identity(value, maximum: int) -> dict:
    row = _object(value, ("sha256", "byte_length"))
    return {"sha256": _sha256(row["sha256"]), "byte_length": _size(row["byte_length"], maximum)}


def _metadata(value, roles: tuple[str, ...]) -> dict:
    row = _object(value, ("inputs", "source_assessment_sha256", "source_observation_count"))
    raw_inputs = _object(row["inputs"], roles)
    count = row["source_observation_count"]
    if type(count) is not int or not 0 <= count <= MAX_OBSERVATIONS:
        raise InputError("invalid_review_manifest_count")
    return {
        "inputs": {
            role: _identity(raw_inputs[role], MAX_MANIFEST_BYTES if role == "packet_manifest" else MAX_PACKET_BYTES)
            for role in roles
        },
        "source_assessment_sha256": _sha256(row["source_assessment_sha256"]),
        "source_observation_count": count,
    }


def _phase(manifest_name: str):
    if type(manifest_name) is not str or manifest_name not in _PHASES:
        raise InputError("invalid_review_manifest_name")
    return _PHASES[manifest_name]


def _payloads(payloads: dict[str, bytes], names: tuple[str, ...]) -> None:
    if (type(payloads) is not dict or set(payloads) != set(names)
            or any(type(value) is not bytes or not 0 < len(value) <= MAX_PAYLOAD_BYTES
                   for value in payloads.values())):
        raise InputError("invalid_review_output_inventory")


def _manifest_bytes(manifest_name: str, payloads: dict[str, bytes], metadata: dict) -> bytes:
    schema, names, roles, scope = _phase(manifest_name)
    _payloads(payloads, names)
    checked = _metadata(metadata, roles)
    # Explicit fields only: no paths, source free text, reviewer or decision notes.
    data = {
        "schema_version": schema,
        "inputs": checked["inputs"],
        "source_assessment_sha256": checked["source_assessment_sha256"],
        "source_observation_count": checked["source_observation_count"],
        "output_files": list(names + (manifest_name,)),
        "files": [{"name": name, "bytes": len(payloads[name]),
                   "sha256": hashlib.sha256(payloads[name]).hexdigest()} for name in names],
        "manifest_self_excluded": True,
        "demo_only": True,
        "demo_label": DEMO_LABEL,
        "human_review_verified": False,
        "producer_verified": False,
        "release_authorized": False,
        "full_bundle_verified": False,
        "validation_scope": scope,
        "delivery_blockers": list(_BLOCKERS),
        "integrity_limit": _INTEGRITY_LIMIT,
    }
    raw = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if not 0 < len(raw) <= MAX_MANIFEST_BYTES:
        raise InputError("review_manifest_size_limit")
    return raw


def validate_packet_manifest(
    loaded_manifest: JsonFile, actual_packet: JsonFile,
) -> PacketManifestCheck:
    """Check closed manifest metadata and the one explicit packet-byte relation.

    The loader supplies actual byte identities. Other payload rows are checked
    only for the closed inventory shape; their files are never followed/read.
    Declared Phase17/source identities are compared to the packet's metadata,
    not to independently opened source files or a trusted external reference.
    """
    if type(loaded_manifest) is not JsonFile or type(actual_packet) is not JsonFile:
        raise InputError("invalid_loaded_review_manifest")
    _sha256(loaded_manifest.sha256)
    _size(loaded_manifest.byte_length, MAX_MANIFEST_BYTES)
    packet_digest = _sha256(actual_packet.sha256)
    packet_length = _size(actual_packet.byte_length, MAX_PACKET_BYTES)
    packet = validate_packet(actual_packet.data)
    manifest = _object(loaded_manifest.data, _MANIFEST_FIELDS)
    schema, names, roles, scope = _phase("review-packet-manifest.json")
    if type(manifest["schema_version"]) is not str or manifest["schema_version"] != schema:
        raise InputError("unsupported_review_manifest_schema")
    checked = _metadata({
        "inputs": manifest["inputs"],
        "source_assessment_sha256": manifest["source_assessment_sha256"],
        "source_observation_count": manifest["source_observation_count"],
    }, roles)
    for key, expected in (
        ("manifest_self_excluded", True), ("demo_only", True),
        ("human_review_verified", False), ("producer_verified", False),
        ("release_authorized", False), ("full_bundle_verified", False),
    ):
        if type(manifest[key]) is not bool or manifest[key] is not expected:
            raise InputError("invalid_review_manifest_guard")
    if (type(manifest["demo_label"]) is not str or manifest["demo_label"] != DEMO_LABEL
            or manifest["output_files"] != list(names + ("review-packet-manifest.json",))
            or manifest["validation_scope"] != scope
            or manifest["delivery_blockers"] != list(_BLOCKERS)
            or manifest["integrity_limit"] != _INTEGRITY_LIMIT):
        raise InputError("invalid_review_manifest_limits")
    rows = manifest["files"]
    if type(rows) is not list or len(rows) != len(names):
        raise InputError("invalid_review_manifest_inventory")
    entries = {}
    for raw_entry in rows:
        entry = _object(raw_entry, ("name", "bytes", "sha256"))
        name = entry["name"]
        if type(name) is not str or name not in names or name in entries:
            raise InputError("invalid_review_manifest_inventory")
        entries[name] = {"bytes": _size(entry["bytes"]), "sha256": _sha256(entry["sha256"])}
    selected = entries["review-packet.json"]
    if selected["sha256"] != packet_digest or selected["bytes"] != packet_length:
        raise InputError("review_packet_manifest_mismatch")
    if (checked["source_assessment_sha256"] != packet.source_assessment.sha256
            or checked["source_observation_count"] != packet.source_assessment.item_count
            or checked["source_observation_count"] != len(packet.observations)):
        raise InputError("review_manifest_source_mismatch")
    for role in roles:
        identity = getattr(packet.phase17_inputs, role)
        if checked["inputs"][role] != {"sha256": identity.sha256, "byte_length": identity.byte_length}:
            raise InputError("review_manifest_input_mismatch")
    return PacketManifestCheck()


def publish_bundle(
    output: Path, payloads: dict[str, bytes], manifest_name: str,
    manifest_metadata: dict,
) -> dict[str, dict[str, int | str]]:
    """Publish a fixed prepare/reconcile inventory into a new directory.

    Manifest bytes exclude their own identity; the returned external inventory
    includes it. Existing directories are never adopted. Unsupported hardlink
    filesystems fail; interrupted runs may leave own partial output/staging.
    Hostile races, ACLs, crash durability and secure cleanup are not established.
    """
    _, names, _, _ = _phase(manifest_name)
    metadata = _manifest_bytes(manifest_name, payloads, manifest_metadata)
    all_names = names + (manifest_name,)
    all_payloads = {name: payloads[name] for name in names}
    all_payloads[manifest_name] = metadata
    identities = {
        name: {"bytes": len(all_payloads[name]),
               "sha256": hashlib.sha256(all_payloads[name]).hexdigest()}
        for name in all_names
    }
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".review-stage-", dir=output.parent))
    stage_info = check_existing_path(stage, directory=True)
    try:
        for name in all_names:
            _same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                stream.write(all_payloads[name])
                stream.flush()
                os.fsync(stream.fileno())
        _same_directory(output.parent, parent_info)
        output.mkdir(exist_ok=False)
        output_info = check_existing_path(output, directory=True)
        for name in all_names:
            _same_directory(output.parent, parent_info)
            _same_directory(output, output_info)
            _same_directory(stage, stage_info)
            os.link(stage / name, output / name, follow_symlinks=False)
    finally:
        # Delete only this run's fixed staging names; never recursive cleanup.
        try:
            _same_directory(stage, stage_info)
            for name in all_names:
                candidate = stage / name
                if os.path.lexists(candidate):
                    check_existing_path(candidate, directory=False)
                    candidate.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass  # Residual files are not promised to be securely deleted.
    return identities
