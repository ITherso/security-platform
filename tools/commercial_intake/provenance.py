"""Partial JSON-entry binding and bounded publication for the offline intake.

No manifest entry is followed. Matching metadata never verifies an HTML
payload, full bundle, producer identity, assessment authority or human review.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Literal

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory
from commercial_handoff.schema import InputError

from . import ADAPTER_VERSION, INTAKE_CONTRACT
from .assessment_reader import AssessmentSource, read_json_file


MAX_MANIFEST_BYTES = 64 * 1024
MAX_NATIVE_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_OUTPUT_BYTES = 4 * 1024 * 1024
DOCUMENT_NAMES = ("handoff-input.json", "source-mapping.json")
ALL_NAMES = DOCUMENT_NAMES + ("intake-manifest.json",)
_MANIFEST_SCHEMA = "termivar-report-bundle/v1"
_SHA256 = re.compile(r"[a-f0-9]{64}")
_SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)


@dataclass(frozen=True, slots=True)
class ManifestCheck:
    provided: bool
    sha256: str | None
    byte_length: int | None
    status: Literal["not_provided", "partial_json_entry_match"]
    json_entry_matches: bool | None
    summary_matches: bool | None
    html_payload_read: bool = field(default=False, init=False)
    producer_verified: bool = field(default=False, init=False)
    full_bundle_verified: bool = field(default=False, init=False)


def _object(value, keys: tuple[str, ...]):
    if type(value) is not dict or set(value) != set(keys):
        raise InputError("manifest_invalid_fields")
    return value


def _valid_semver(value) -> bool:
    if type(value) is not str or not 1 <= len(value) <= 128:
        return False
    match = _SEMVER.fullmatch(value)
    if match is None or any(int(match.group(index)) > 2**64 - 1 for index in (1, 2, 3)):
        return False
    prerelease = match.group(4)
    return prerelease is None or all(
        not (part.isdecimal() and len(part) > 1 and part.startswith("0"))
        for part in prerelease.split(".")
    )


def read_manifest(raw_path: str | None, assessment: AssessmentSource) -> ManifestCheck:
    """Read only the explicitly named manifest and bind its selected JSON entry.

    Contract checks mirror the base native report-bundle/v1 manifest: exact
    fields, two fixed entries, SemVer metadata and bounded counts/byte lengths.
    The producer version is validated and discarded, never treated as proof.
    """
    if raw_path is None:
        return ManifestCheck(
            provided=False, sha256=None, byte_length=None, status="not_provided",
            json_entry_matches=None, summary_matches=None,
        )

    loaded = read_json_file(raw_path, maximum=MAX_MANIFEST_BYTES)
    manifest = _object(loaded.data, ("schema", "producer", "assessment", "files"))
    if type(manifest["schema"]) is not str or manifest["schema"] != _MANIFEST_SCHEMA:
        raise InputError("manifest_unsupported_schema")
    producer = _object(manifest["producer"], ("product", "version"))
    if (type(producer["product"]) is not str or producer["product"] != "Termivar"
            or not _valid_semver(producer["version"])):
        raise InputError("manifest_invalid_producer")

    summary = _object(manifest["assessment"], ("profile", "status", "subject_count", "item_count"))
    if (type(summary["profile"]) is not str or summary["profile"] != "web-review"
            or type(summary["status"]) is not str or summary["status"] != "complete"
            or type(summary["subject_count"]) is not int
            or not 1 <= summary["subject_count"] <= 1024
            or type(summary["item_count"]) is not int
            or not 0 <= summary["item_count"] <= 4096):
        raise InputError("manifest_invalid_summary")

    files = manifest["files"]
    if type(files) is not list or len(files) != 2:
        raise InputError("manifest_invalid_files")
    expected = {
        "assessment.json": ("json", "application/json"),
        "assessment.html": ("html", "text/html; charset=utf-8"),
    }
    entries = {}
    for raw_entry in files:
        entry = _object(raw_entry, ("name", "format", "media_type", "byte_length", "sha256"))
        name = entry["name"]
        if type(name) is not str or name not in expected or name in entries:
            raise InputError("manifest_invalid_files")
        expected_format, expected_media_type = expected[name]
        if (type(entry["format"]) is not str or entry["format"] != expected_format
                or type(entry["media_type"]) is not str or entry["media_type"] != expected_media_type
                or type(entry["byte_length"]) is not int
                or not 1 <= entry["byte_length"] <= MAX_NATIVE_PAYLOAD_BYTES
                or type(entry["sha256"]) is not str or _SHA256.fullmatch(entry["sha256"]) is None):
            raise InputError("manifest_invalid_files")
        entries[name] = entry

    selected = entries["assessment.json"]
    if (selected["sha256"] != assessment.sha256
            or selected["byte_length"] != assessment.byte_length):
        raise InputError("manifest_json_entry_mismatch")
    if (summary["profile"] != assessment.profile or summary["status"] != assessment.status
            or summary["subject_count"] != assessment.subject_count
            or summary["item_count"] != len(assessment.items)):
        raise InputError("manifest_summary_mismatch")

    return ManifestCheck(
        provided=True, sha256=loaded.sha256, byte_length=loaded.byte_length,
        status="partial_json_entry_match", json_entry_matches=True, summary_matches=True,
    )


def _documents(documents: dict[str, bytes]) -> None:
    if (type(documents) is not dict or set(documents) != set(DOCUMENT_NAMES)
            or any(type(value) is not bytes or not 0 < len(value) <= MAX_OUTPUT_BYTES
                   for value in documents.values())):
        raise InputError("invalid_intake_output_inventory")


def build_intake_manifest(
    assessment: AssessmentSource, manifest_check: ManifestCheck,
    documents: dict[str, bytes],
) -> bytes:
    """Describe successful all-item mapping and the two actual payload bytes.

    The calling adapter validates its complete output before this success-only
    manifest is built. No truncation or unsupported-item success is described.
    Its own byte size/hash belong to the external delivery inventory.
    """
    _documents(documents)
    count = len(assessment.items)
    data = {
        "schema_version": "termivar-assessment-intake-manifest/v1",
        "adapter_contract": INTAKE_CONTRACT,
        "adapter_version": ADAPTER_VERSION,
        "assessment": {
            "schema": assessment.schema,
            "sha256": assessment.sha256,
            "byte_length": assessment.byte_length,
        },
        "optional_manifest": {
            "provided": manifest_check.provided,
            "sha256": manifest_check.sha256,
            "byte_length": manifest_check.byte_length,
            "status": manifest_check.status,
            "json_entry_matches": manifest_check.json_entry_matches,
            "summary_matches": manifest_check.summary_matches,
            "html_payload_read": False,
            "producer_verified": False,
            "full_bundle_verified": False,
        },
        "source_count": count,
        "transferred_count": count,
        "rejected_or_unsupported_summary": [],
        "automatic_merge_performed": False,
        "fingerprint_reuse_detected": len({item.fingerprint for item in assessment.items}) != count,
        "native_import_validation_performed": False,
        "fingerprint_limit": "Repeated reported fingerprints remain separate by source byte SHA256 and JSON pointer; native importer uniqueness acceptance is not established.",
        "output_files": list(ALL_NAMES),
        "files": [
            {"name": name, "bytes": len(documents[name]),
             "sha256": hashlib.sha256(documents[name]).hexdigest()}
            for name in DOCUMENT_NAMES
        ],
        "manifest_self_excluded": True,
        "demo_only": True,
        "human_review_verified": False,
        "producer_verified": False,
        "release_authorized": False,
        "delivery_blockers": [
            "demo_only_not_for_delivery", "human_review_not_verified",
            "producer_not_verified", "authorization_not_verified",
            "data_handling_pending_decision", "release_not_authorized",
        ],
        "source_provenance_limitation": (
            "Only the explicitly selected assessment and optional manifest were read. "
            "Hashes identify their actual bytes, not a producer, authorized scope, "
            "finding accuracy or human approval."
        ),
        "partial_manifest_limitation": (
            "A matching manifest establishes only the selected JSON-entry byte length, "
            "SHA256 and summary relation. No HTML payload was opened, no full bundle "
            "was verified and no native verifier or signature check was run."
        ),
        "completion_marker": (
            "intake-manifest.json is published last. Its presence alone is not "
            "authentication; check the declared payload bytes before treating the set as complete."
        ),
    }
    return (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def publish_intake(output: Path, documents: dict[str, bytes], metadata: bytes) -> None:
    """Publish only fixed names into a new directory; never adopt or overwrite.

    Complete staged files are hard-linked exclusively, with the manifest last.
    Unsupported filesystems fail; failures may leave a new partial output or
    own staging directory. Hostile races, ACLs and crash durability are not an
    independently accepted security boundary or a secure-deletion guarantee.
    """
    _documents(documents)
    if type(metadata) is not bytes or not 0 < len(metadata) <= MAX_OUTPUT_BYTES:
        raise InputError("invalid_intake_manifest_bytes")
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")

    payloads = {name: documents[name] for name in DOCUMENT_NAMES}
    payloads["intake-manifest.json"] = metadata
    stage = Path(tempfile.mkdtemp(prefix=".intake-stage-", dir=output.parent))
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
        # Only this run's fixed staging filenames; never recursive deletion.
        try:
            _same_directory(stage, stage_info)
            for name in ALL_NAMES:
                candidate = stage / name
                if os.path.lexists(candidate):
                    check_existing_path(candidate, directory=False)
                    candidate.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass  # Residual staging is not promised to be securely removed.
