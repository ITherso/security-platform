"""Closed immutable metadata contracts and bounded serialization for review.

The packet binds explicitly selected Phase17 files. It neither reads the native
assessment nor authenticates a producer, human, decision or delivery authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re

from commercial_handoff.input_loader import _depth_check, _tree_budget
from commercial_handoff.schema import HandoffInput, InputError, validate as validate_handoff
from commercial_intake.assessment_reader import (
    JsonFile, SUPPORTED_CAPABILITIES, read_json_file,
)

from . import DEMO_LABEL, MAX_REVIEW_BYTES, OVERLAY_CONTRACT, PACKET_CONTRACT


ReviewError = InputError
SOURCE_VERIFICATION = "phase17_file_binding_only"
REVIEW_REQUIREMENTS = (
    "human_review_required", "scope_basis_required",
    "evidence_access_and_limitations_required", "client_inclusion_decision_required",
    "safe_wording_review_required",
)
DELIVERY_BLOCKERS = (
    "demo_only_not_for_delivery", "human_review_not_verified", "producer_not_verified",
    "authorization_not_verified", "data_handling_pending_decision", "release_not_authorized",
)


@dataclass(frozen=True, slots=True)
class FileIdentity:
    sha256: str
    byte_length: int


@dataclass(frozen=True, slots=True)
class Phase17Inputs:
    handoff_input: FileIdentity
    source_mapping: FileIdentity
    intake_manifest: FileIdentity


@dataclass(frozen=True, slots=True)
class SourceAssessment:
    sha256: str
    byte_length: int
    schema: str
    source_schema: str
    run_schema: str
    profile_schema: str
    profile: str
    status: str
    subject_count: int
    item_count: int


@dataclass(frozen=True, slots=True)
class ManifestLimitation:
    provided: bool
    sha256: str | None
    byte_length: int | None
    status: str
    json_entry_matches: bool | None
    summary_matches: bool | None
    html_payload_read: bool
    full_bundle_verified: bool
    producer_verified: bool


@dataclass(frozen=True, slots=True)
class PacketObservation:
    observation_id: str
    observation_key: str
    source_assessment_sha256: str
    source_json_pointer: str
    fingerprint: str
    capability_id: str
    source_disposition: str
    review_status: str
    scope_status: str
    client_inclusion: str


@dataclass(frozen=True, slots=True)
class ReviewPacket:
    schema_version: str
    mode: str
    demo_label: str
    phase17_inputs: Phase17Inputs
    source_assessment: SourceAssessment
    manifest_limitation: ManifestLimitation
    observations: tuple[PacketObservation, ...]
    review_requirements: tuple[str, ...]
    delivery_blockers: tuple[str, ...]
    source_verification: str
    demo_only: bool
    human_review_verified: bool
    producer_verified: bool
    release_authorized: bool
    native_assessment_verified: bool


def object_fields(value: object, keys) -> dict:
    if type(value) is not dict or set(value) != set(keys):
        raise InputError("review_invalid_fields")
    return value


def literal(value: object, expected):
    if type(value) is not type(expected) or value != expected:
        raise InputError("review_invalid_constant")
    return value


def integer(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise InputError("review_invalid_integer")
    return value


def identifier(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value) is None:
        raise InputError("review_invalid_identifier")
    return value


def digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise InputError("review_invalid_digest")
    return value


def fingerprint(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"sha256:[a-f0-9]{64}", value) is None:
        raise InputError("review_invalid_fingerprint")
    return value


def source_pointer(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"/items/(0|[1-9][0-9]{0,3})", value) is None:
        raise InputError("review_invalid_source_pointer")
    return value


def observation_key(source_sha256: str, pointer: str) -> str:
    return "sha256:" + digest(source_sha256) + "#" + source_pointer(pointer)


def enum_value(value: object, allowed) -> str:
    if type(value) is not str or value not in allowed:
        raise InputError("review_invalid_enum")
    return value


def array(value: object, maximum: int, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise InputError("review_invalid_array")
    return value


def text(value: object, maximum: int = 2048, *, nullable: bool = False,
         maximum_lines: int = 16) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise InputError("review_invalid_text")
    try:
        value.encode("utf-8", "strict")
    except UnicodeError:
        raise InputError("review_invalid_unicode") from None
    if any((ord(c) < 32 and c not in "\n\r\t") or 127 <= ord(c) <= 159 for c in value):
        raise InputError("review_invalid_control_character")
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.count("\n") + 1 > maximum_lines:
        raise InputError("review_text_line_limit")
    return value


def _serialized(value: object) -> bytes:
    try:
        return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                           allow_nan=False) + "\n").encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise InputError("review_invalid_json_value") from None


def check_json_budget(value: object, maximum: int = MAX_REVIEW_BYTES) -> None:
    integer(maximum, 1, MAX_REVIEW_BYTES)
    _tree_budget(value)
    raw = _serialized(value)
    if not 0 < len(raw) <= maximum:
        raise InputError("review_json_size_limit")
    _depth_check(raw.decode("utf-8"))


def json_bytes(value: object, maximum: int = MAX_REVIEW_BYTES) -> bytes:
    check_json_budget(value, maximum)
    return _serialized(value)


def load_review_json(raw_path: str, maximum: int = MAX_REVIEW_BYTES) -> JsonFile:
    integer(maximum, 1, MAX_REVIEW_BYTES)
    loaded = read_json_file(raw_path, maximum=maximum)
    # Phase17's generic loader is wider. Apply the unchanged Phase16 aggregate
    # graph budget too: depth12, nodes10000 and key/value UTF-8 text128KiB.
    _tree_budget(loaded.data)
    return loaded


def file_identity(value: object, maximum: int = MAX_REVIEW_BYTES) -> FileIdentity:
    row = object_fields(value, ("sha256", "byte_length"))
    return FileIdentity(digest(row["sha256"]), integer(row["byte_length"], 1, maximum))


def source_assessment(value: object) -> SourceAssessment:
    row = object_fields(value, ("sha256", "byte_length", "schema", "source_schema",
        "run_schema", "profile_schema", "profile", "status", "subject_count", "item_count"))
    return SourceAssessment(
        digest(row["sha256"]), integer(row["byte_length"], 1, 1024 * 1024),
        literal(row["schema"], "venom-rendered-assessment/v1"),
        literal(row["source_schema"], "venom-assessment-run/v1"),
        literal(row["run_schema"], "venom-run/v1"),
        literal(row["profile_schema"], "venom.scan-profile/v1"),
        literal(row["profile"], "web-review"), literal(row["status"], "complete"),
        integer(row["subject_count"], 1, 1024), integer(row["item_count"], 0, 256),
    )


def manifest_limitation(value: object) -> ManifestLimitation:
    row = object_fields(value, ("provided", "sha256", "byte_length", "status",
        "json_entry_matches", "summary_matches", "html_payload_read",
        "full_bundle_verified", "producer_verified"))
    if type(row["provided"]) is not bool:
        raise InputError("review_invalid_manifest_limitation")
    if row["provided"]:
        sha = digest(row["sha256"])
        size = integer(row["byte_length"], 1, 64 * 1024)
        status = literal(row["status"], "partial_json_entry_match")
        json_match = literal(row["json_entry_matches"], True)
        summary_match = literal(row["summary_matches"], True)
    else:
        sha = literal(row["sha256"], None)
        size = literal(row["byte_length"], None)
        status = literal(row["status"], "not_provided")
        json_match = literal(row["json_entry_matches"], None)
        summary_match = literal(row["summary_matches"], None)
    return ManifestLimitation(row["provided"], sha, size, status, json_match, summary_match,
        literal(row["html_payload_read"], False), literal(row["full_bundle_verified"], False),
        literal(row["producer_verified"], False))


def identity_to_dict(value: FileIdentity) -> dict:
    return {"sha256": value.sha256, "byte_length": value.byte_length}


def assessment_to_dict(value: SourceAssessment) -> dict:
    return {"sha256": value.sha256, "byte_length": value.byte_length, "schema": value.schema,
        "source_schema": value.source_schema, "run_schema": value.run_schema,
        "profile_schema": value.profile_schema, "profile": value.profile, "status": value.status,
        "subject_count": value.subject_count, "item_count": value.item_count}


def limitation_to_dict(value: ManifestLimitation) -> dict:
    return {"provided": value.provided, "sha256": value.sha256, "byte_length": value.byte_length,
        "status": value.status, "json_entry_matches": value.json_entry_matches,
        "summary_matches": value.summary_matches, "html_payload_read": value.html_payload_read,
        "full_bundle_verified": value.full_bundle_verified, "producer_verified": value.producer_verified}


def validate_packet(value: object) -> ReviewPacket:
    check_json_budget(value)
    row = object_fields(value, ("schema_version", "mode", "demo_label", "phase17_inputs",
        "source_assessment", "manifest_limitation", "observations", "review_requirements",
        "delivery_blockers", "source_verification", "demo_only", "human_review_verified",
        "producer_verified", "release_authorized", "native_assessment_verified"))
    inputs = object_fields(row["phase17_inputs"], ("handoff_input", "source_mapping", "intake_manifest"))
    phase17 = Phase17Inputs(*(file_identity(inputs[key]) for key in
        ("handoff_input", "source_mapping", "intake_manifest")))
    source = source_assessment(row["source_assessment"])
    observations = []
    for index, item in enumerate(array(row["observations"], 256)):
        item = object_fields(item, ("observation_id", "observation_key", "source_assessment_sha256",
            "source_json_pointer", "fingerprint", "capability_id", "source_disposition",
            "review_status", "scope_status", "client_inclusion"))
        pointer = literal(item["source_json_pointer"], f"/items/{index}")
        source_sha = literal(item["source_assessment_sha256"], source.sha256)
        observations.append(PacketObservation(
            literal(identifier(item["observation_id"]), f"OBS-{index + 1:02d}"),
            literal(item["observation_key"], observation_key(source_sha, pointer)), source_sha,
            pointer, fingerprint(item["fingerprint"]),
            enum_value(item["capability_id"], SUPPORTED_CAPABILITIES),
            enum_value(item["source_disposition"], ("informational", "needs_review", "confirmed")),
            literal(item["review_status"], "unreviewed"), literal(item["scope_status"], "unknown"),
            literal(item["client_inclusion"], "pending_decision"),
        ))
    if len(observations) != source.item_count:
        raise InputError("review_observation_count_mismatch")
    if tuple(array(row["review_requirements"], len(REVIEW_REQUIREMENTS))) != REVIEW_REQUIREMENTS:
        raise InputError("review_requirements_changed")
    if tuple(array(row["delivery_blockers"], len(DELIVERY_BLOCKERS))) != DELIVERY_BLOCKERS:
        raise InputError("review_blockers_changed")
    return ReviewPacket(
        literal(row["schema_version"], PACKET_CONTRACT), literal(row["mode"], "demo"),
        literal(row["demo_label"], DEMO_LABEL), phase17, source,
        manifest_limitation(row["manifest_limitation"]), tuple(observations),
        REVIEW_REQUIREMENTS, DELIVERY_BLOCKERS, literal(row["source_verification"], SOURCE_VERIFICATION),
        literal(row["demo_only"], True), literal(row["human_review_verified"], False),
        literal(row["producer_verified"], False), literal(row["release_authorized"], False),
        literal(row["native_assessment_verified"], False),
    )


def packet_to_dict(packet: ReviewPacket) -> dict:
    if type(packet) is not ReviewPacket:
        raise InputError("review_invalid_packet_model")
    try:
        result = {
            "schema_version": packet.schema_version, "mode": packet.mode, "demo_label": packet.demo_label,
            "phase17_inputs": {key: identity_to_dict(getattr(packet.phase17_inputs, key))
                for key in ("handoff_input", "source_mapping", "intake_manifest")},
            "source_assessment": assessment_to_dict(packet.source_assessment),
            "manifest_limitation": limitation_to_dict(packet.manifest_limitation),
            "observations": [{"observation_id": item.observation_id,
                "observation_key": item.observation_key,
                "source_assessment_sha256": item.source_assessment_sha256,
                "source_json_pointer": item.source_json_pointer, "fingerprint": item.fingerprint,
                "capability_id": item.capability_id, "source_disposition": item.source_disposition,
                "review_status": item.review_status, "scope_status": item.scope_status,
                "client_inclusion": item.client_inclusion} for item in packet.observations],
            "review_requirements": list(packet.review_requirements),
            "delivery_blockers": list(packet.delivery_blockers),
            "source_verification": packet.source_verification, "demo_only": packet.demo_only,
            "human_review_verified": packet.human_review_verified, "producer_verified": packet.producer_verified,
            "release_authorized": packet.release_authorized,
            "native_assessment_verified": packet.native_assessment_verified,
        }
    except (AttributeError, TypeError):
        raise InputError("review_invalid_packet_model") from None
    validate_packet(result)
    return result


def handoff_to_dict(document: HandoffInput) -> dict:
    if type(document) is not HandoffInput:
        raise InputError("review_invalid_handoff_model")
    try:
        result = {
            "schema_version": document.schema_version, "case_id": document.case_id, "mode": document.mode,
            "scope_summary": document.scope_summary, "authorization_status": document.authorization_status,
            "source_artifacts": [{"artifact_id": item.artifact_id, "contract": item.contract,
                "sha256": item.sha256, "byte_length": item.byte_length,
                "completion_status": item.completion_status, "provenance_note": item.provenance_note}
                for item in document.source_artifacts],
            "observations": [{"observation_id": item.observation_id, "source_artifact": item.source_artifact,
                "observation_ref": item.observation_ref, "source_json_pointer": item.source_json_pointer,
                "capability_id": item.capability_id, "source_disposition": item.source_disposition,
                "review_status": item.review_status, "scope_status": item.scope_status,
                "client_inclusion": item.client_inclusion, "safe_summary": item.safe_summary,
                "evidence_limitations": item.evidence_limitations, "decision_ref": item.decision_ref}
                for item in document.observations],
            "review_decisions": [{"decision_id": item.decision_id, "observation_id": item.observation_id,
                "review_status": item.review_status, "client_inclusion": item.client_inclusion,
                "reviewer_ref": item.reviewer_ref, "reviewed_at": item.reviewed_at, "reason": item.reason}
                for item in document.review_decisions],
            "delivery_constraints": list(document.delivery_constraints),
        }
    except (AttributeError, TypeError):
        raise InputError("review_invalid_handoff_model") from None
    check_json_budget(result)
    validate_handoff(result)
    return result


def render_handoff_bytes(document: HandoffInput) -> bytes:
    return json_bytes(handoff_to_dict(document))
