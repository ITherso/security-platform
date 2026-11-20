"""Record a declared reviewer reference and time on a finalized desk overlay.

The finalized Phase19 overlay, its desk manifest, the Phase18 packet and packet
manifest and the original Phase17 handoff input are selected explicitly and
checked with the unchanged owner validators. Only reviewer_ref and reviewed_at
change; the owner Phase18 function recomputes each decision context digest.
Attribution records who declared the decisions. It does not authenticate that
person, verify a review, approve inclusion or authorize delivery or release.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import LoadedInput, check_existing_path, load_input, output_location
from commercial_handoff.manifest import _same_directory
from commercial_handoff.review_rules import _reviewer_missing
from commercial_handoff.schema import InputError
from commercial_intake.assessment_reader import JsonFile
from commercial_review import DEMO_LABEL, MAX_REVIEW_BYTES
from commercial_review.decision_binding import bind_decisions
from commercial_review.decision_overlay import (
    DECISION_CONTEXT_FIELDS, decision_context_digest, overlay_to_dict, validate_overlay,
)
from commercial_review.manifest import validate_packet_manifest
from commercial_review.review_contracts import ReviewPacket, check_json_budget, load_review_json, text, validate_packet
from commercial_review_desk.desk_contracts import checked_packet_file
from commercial_review_desk.desk_projection import render_overlay
from commercial_review_desk.manifest import _LABEL as DESK_LABEL, _OPERATIONS as DESK_OPERATIONS
from commercial_review_attribution import MANIFEST_CONTRACT, MANIFEST_NAME, OVERLAY_NAME


MAX_MANIFEST_BYTES = 64 * 1024
_SHA256 = re.compile(r"[a-f0-9]{64}")
_REVIEW_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
# Owner Phase19 finalize inventory; the desk publisher writes these literals.
_DESK_OVERLAY, _DESK_MANIFEST, _DESK_ROLES = DESK_OPERATIONS["finalize_desk"][:3]
_DESK_SCHEMA = "termivar-review-desk-output-manifest/v1"
_DESK_FIELDS = frozenset((
    "schema_version", "operation", "inputs", "review_packet_digest", "source_assessment_digest",
    "observation_count", "decision_count", "files", "output_files", "manifest_self_excluded",
    "mode", "demo_only", "demo_label", "human_review_verified", "producer_verified",
    "release_authorized", "native_assessment_verified", "full_bundle_verified",
    "packet_manifest_validation_scope", "integrity_limit", "completion_marker",
))
_INPUT_ROLES = ("review_packet", "packet_manifest", "handoff_input", "overlay", "overlay_manifest")
_ATTRIBUTED_FIELDS = ("reviewer_ref", "reviewed_at")
_INTEGRITY_LIMIT = (
    "Hashes bind explicitly selected files and generated payload bytes only. reviewer_ref and "
    "reviewed_at are operator declarations copied unchanged into every decision; they do not "
    "authenticate a reviewer, prove that a human review took place, or approve, authorize or "
    "release anything. Source references and manifest entry names are never opened automatically."
)
_COMPLETION_MARKER = (
    "This manifest is published last. Its presence is not authentication; compare the declared "
    "payload bytes before treating this output set as complete."
)


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def checked_reviewer_ref(value: object) -> str:
    """Owner Phase18 reviewer text rule (128 chars, one line), plus printable,
    unpadded and not a Phase16 missing-reviewer sentinel. Never an identity proof."""
    try:
        checked = text(value, 128, maximum_lines=1)
    except InputError:
        raise InputError("attribution_invalid_reviewer_ref") from None
    if not checked.isprintable() or checked != checked.strip():
        raise InputError("attribution_invalid_reviewer_ref")
    if _reviewer_missing(checked):
        raise InputError("attribution_reviewer_ref_placeholder")
    return checked


def checked_review_time(value: object) -> str:
    """Same declared-time rule as the Phase18 overlay; there is no clock default."""
    try:
        checked = text(value, 20, maximum_lines=1)
        if _REVIEW_TIME.fullmatch(checked) is None:
            raise ValueError()
        datetime.strptime(checked, "%Y-%m-%dT%H:%M:%SZ")
    except (InputError, ValueError):
        raise InputError("attribution_invalid_review_time") from None
    return checked


def _identity_row(row: object, maximum: int) -> bool:
    return (type(row) is dict and set(row) == {"sha256", "byte_length"}
            and type(row["sha256"]) is str and _SHA256.fullmatch(row["sha256"]) is not None
            and type(row["byte_length"]) is int and 1 <= row["byte_length"] <= maximum)


def check_overlay_manifest(manifest_file: JsonFile, overlay_file: JsonFile, selected: dict,
                           packet: ReviewPacket, decision_count: int) -> None:
    """Check the closed Phase19 finalize manifest against the selected bytes.

    Only the explicitly selected files are compared. The decision draft named by
    the manifest is shape-checked, never opened. Nothing here is authentication.
    """
    if type(manifest_file) is not JsonFile or type(overlay_file) is not JsonFile:
        raise InputError("attribution_invalid_loaded_input")
    data = manifest_file.data
    if type(data) is not dict or set(data) != _DESK_FIELDS:
        raise InputError("attribution_overlay_manifest_fields")
    inputs = data["inputs"]
    if type(inputs) is not dict or set(inputs) != set(_DESK_ROLES):
        raise InputError("attribution_overlay_manifest_inputs")
    for role in _DESK_ROLES:
        cap = MAX_MANIFEST_BYTES if role == "packet_manifest" else MAX_REVIEW_BYTES
        if not _identity_row(inputs[role], cap):
            raise InputError("attribution_overlay_manifest_inputs")
        if role in selected and inputs[role] != {"sha256": selected[role].sha256,
                                                 "byte_length": selected[role].byte_length}:
            raise InputError("attribution_overlay_manifest_input_mismatch")
    expected = {
        "schema_version": _DESK_SCHEMA, "operation": "finalize_desk",
        "review_packet_digest": selected["review_packet"].sha256,
        "source_assessment_digest": packet.source_assessment.sha256,
        "observation_count": len(packet.observations), "decision_count": decision_count,
        "files": [{"name": _DESK_OVERLAY, "bytes": overlay_file.byte_length, "sha256": overlay_file.sha256}],
        "output_files": [_DESK_OVERLAY, _DESK_MANIFEST], "manifest_self_excluded": True,
        "mode": "demo", "demo_only": True, "demo_label": DESK_LABEL,
        "human_review_verified": False, "producer_verified": False, "release_authorized": False,
        "native_assessment_verified": False, "full_bundle_verified": False,
        "packet_manifest_validation_scope": "explicit_packet_entry_only",
    }
    for key, value in expected.items():
        if _canonical(data[key]) != _canonical(value):
            raise InputError("attribution_overlay_manifest_mismatch")
    for key in ("integrity_limit", "completion_marker"):
        try:
            text(data[key], 1024, maximum_lines=1)
        except InputError:
            raise InputError("attribution_overlay_manifest_mismatch") from None


def attribute_overlay(packet_file: JsonFile, packet: ReviewPacket, packet_manifest_file: JsonFile,
                      original: LoadedInput, overlay_file: JsonFile, overlay_manifest_file: JsonFile,
                      reviewer_ref: str, reviewed_at: str) -> dict:
    """Return the same Phase18 overlay with declared reviewer_ref/reviewed_at.

    Pure: opens no files and never takes a person or time from the environment.
    Prior attribution is never overwritten. Owner validation and binding run on
    both the finalized input and the attributed result; trust flags stay false.
    """
    reviewer_ref = checked_reviewer_ref(reviewer_ref)
    reviewed_at = checked_review_time(reviewed_at)
    packet = checked_packet_file(packet_file, packet)
    validate_packet_manifest(packet_manifest_file, packet_file)
    if (type(original) is not LoadedInput or type(overlay_file) is not JsonFile
            or type(overlay_manifest_file) is not JsonFile):
        raise InputError("attribution_invalid_loaded_input")
    overlay = validate_overlay(overlay_file.data)
    if hashlib.sha256(render_overlay(overlay_file.data)).hexdigest() != overlay_file.sha256:
        raise InputError("attribution_overlay_not_canonical")
    bind_decisions(packet, original, overlay, packet_digest=packet_file.sha256)
    if not overlay.decisions:
        raise InputError("attribution_requires_decisions")
    for row in overlay.decisions:
        if row.decision_id != "DESK-" + row.observation_id:
            raise InputError("attribution_not_desk_overlay")
        if row.reviewer_ref is not None or row.reviewed_at is not None:
            raise InputError("attribution_already_present")
    check_overlay_manifest(overlay_manifest_file, overlay_file, {
        "review_packet": packet_file, "packet_manifest": packet_manifest_file, "handoff_input": original,
    }, packet, len(overlay.decisions))
    result = overlay_to_dict(overlay)
    rows = []
    for row in result["decisions"]:
        values = {name: row[name] for name in DECISION_CONTEXT_FIELDS}
        values["reviewer_ref"] = reviewer_ref
        values["reviewed_at"] = reviewed_at
        # Exact 17-field owner digest; the result is revalidated below.
        values["decision_context_digest"] = decision_context_digest(values)
        rows.append(values)
    result["decisions"] = rows
    checked = validate_overlay(result)
    bind_decisions(packet, original, checked, packet_digest=packet_file.sha256)
    output = overlay_to_dict(checked)
    check_json_budget(output)
    return output


def attribution_manifest(document: bytes, inputs: dict, source_digest: str,
                         observation_count: int, decision_count: int) -> bytes:
    """Closed manifest: identities and counts only, never reviewer text or paths."""
    if type(document) is not bytes or not 0 < len(document) <= MAX_REVIEW_BYTES:
        raise InputError("attribution_invalid_output_inventory")
    if type(inputs) is not dict or set(inputs) != set(_INPUT_ROLES):
        raise InputError("attribution_invalid_input_inventory")
    checked = {}
    for role in _INPUT_ROLES:
        cap = MAX_MANIFEST_BYTES if role in ("packet_manifest", "overlay_manifest") else MAX_REVIEW_BYTES
        if not _identity_row(inputs[role], cap):
            raise InputError("attribution_invalid_input_identity")
        checked[role] = {"sha256": inputs[role]["sha256"], "byte_length": inputs[role]["byte_length"]}
    if type(source_digest) is not str or _SHA256.fullmatch(source_digest) is None:
        raise InputError("attribution_invalid_manifest_digest")
    if (type(observation_count) is not int or type(decision_count) is not int
            or not 1 <= decision_count <= observation_count <= 256):
        raise InputError("attribution_invalid_manifest_count")
    data = {
        "schema_version": MANIFEST_CONTRACT,
        "operation": "attribute_review",
        "inputs": checked,
        "review_packet_digest": checked["review_packet"]["sha256"],
        "source_assessment_digest": source_digest,
        "observation_count": observation_count,
        "decision_count": decision_count,
        "attributed_fields": list(_ATTRIBUTED_FIELDS),
        "files": [{"name": OVERLAY_NAME, "bytes": len(document), "sha256": hashlib.sha256(document).hexdigest()}],
        "output_files": [OVERLAY_NAME, MANIFEST_NAME],
        "manifest_self_excluded": True,
        "mode": "demo", "demo_only": True, "demo_label": DEMO_LABEL,
        "human_review_verified": False, "reviewer_identity_verified": False,
        "producer_verified": False, "release_authorized": False,
        "native_assessment_verified": False, "full_bundle_verified": False,
        "attribution_scope": "declared_reviewer_reference_and_time_only",
        "integrity_limit": _INTEGRITY_LIMIT,
        "completion_marker": _COMPLETION_MARKER,
    }
    raw = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > MAX_MANIFEST_BYTES:
        raise InputError("attribution_manifest_size_limit")
    return raw


def publish_attribution(output: Path, document: bytes, manifest: bytes) -> None:
    """Publish the overlay, then the manifest, into a new directory.

    Same staging, exclusive hard-link and manifest-last convention as the desk
    publisher. Failed runs may leave their own partial output or staging; no
    secure cleanup or hostile-race claim follows.
    """
    if (type(document) is not bytes or type(manifest) is not bytes
            or not 0 < len(document) <= MAX_REVIEW_BYTES or not 0 < len(manifest) <= MAX_MANIFEST_BYTES):
        raise InputError("attribution_invalid_output_inventory")
    payloads = {OVERLAY_NAME: document, MANIFEST_NAME: manifest}
    names = (OVERLAY_NAME, MANIFEST_NAME)
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".review-attribution-stage-", dir=output.parent))
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


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "review_attribution: invalid_arguments\n")


def main(argv=None) -> int:
    parser = Arguments(description="Record a declared reviewer reference and time on a finalized "
                       "demo-only desk overlay; no identity, review or release is verified.", allow_abbrev=False)
    parser.add_argument("--review-packet", required=True)
    parser.add_argument("--packet-manifest", required=True)
    parser.add_argument("--handoff-input", required=True, help="Explicit original Phase17 input required by Phase18 binding.")
    parser.add_argument("--overlay", required=True, help="decision-overlay.json written by finalize_desk.")
    parser.add_argument("--overlay-manifest", required=True, help="overlay-manifest.json written by finalize_desk.")
    parser.add_argument("--reviewer-ref", required=True, help="Declared reference, 1-128 printable characters, one line.")
    parser.add_argument("--reviewed-at", required=True, help="Declared time, YYYY-MM-DDTHH:MM:SSZ.")
    parser.add_argument("--output-dir", required=True, help="New cwd-relative directory; parent must exist.")
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        reviewer_ref = checked_reviewer_ref(args.reviewer_ref)
        reviewed_at = checked_review_time(args.reviewed_at)
        packet_file = load_review_json(args.review_packet)
        packet = validate_packet(packet_file.data)
        manifest_file = load_review_json(args.packet_manifest, maximum=MAX_MANIFEST_BYTES)
        validate_packet_manifest(manifest_file, packet_file)
        original = load_input(args.handoff_input)
        overlay_file = load_review_json(args.overlay)
        overlay_manifest_file = load_review_json(args.overlay_manifest, maximum=MAX_MANIFEST_BYTES)
        overlay = attribute_overlay(packet_file, packet, manifest_file, original, overlay_file,
                                    overlay_manifest_file, reviewer_ref, reviewed_at)
        document = render_overlay(overlay)
        inputs = {role: {"sha256": loaded.sha256, "byte_length": loaded.byte_length}
                  for role, loaded in (("review_packet", packet_file), ("packet_manifest", manifest_file),
                                       ("handoff_input", original), ("overlay", overlay_file),
                                       ("overlay_manifest", overlay_manifest_file))}
        manifest = attribution_manifest(document, inputs, packet.source_assessment.sha256,
                                        len(packet.observations), len(overlay["decisions"]))
        publish_attribution(output, document, manifest)
    except InputError as error:
        print("review_attribution: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("review_attribution: local_attribution_failed; no successful attribution is claimed", file=sys.stderr)
        return 1
    print("Created demo-only decision-overlay.json and attribution-manifest.json")
    print("Declared reviewer reference and time recorded on %d decision(s); not identity or review verification"
          % len(overlay["decisions"]))
    print("human_review_verified=false; reviewer_identity_verified=false; producer_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
