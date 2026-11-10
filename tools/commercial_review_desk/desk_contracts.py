"""Closed decision-draft input and reuse of authoritative Phase18 validation.

Browser drafts contain only an observation key and explicit human fields. Source
metadata and context digests are supplied by the existing Python contracts, not
by browser claims. None of these checks authenticate a reviewer or authorize use.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from commercial_handoff.input_loader import LoadedInput
from commercial_handoff.schema import INCLUSIONS, REVIEW_STATUSES, SCOPES, InputError
from commercial_intake.assessment_reader import JsonFile
from commercial_review import DEMO_LABEL, MAX_REVIEW_BYTES
from commercial_review.decision_binding import bind_decisions
from commercial_review.decision_overlay import (
    decision_context_digest, make_empty_overlay, overlay_to_dict, validate_overlay,
)
from commercial_review.manifest import validate_packet_manifest
from commercial_review.review_contracts import (
    ReviewPacket, array, check_json_budget, digest, enum_value, integer, json_bytes,
    literal, load_review_json, object_fields, packet_to_dict, text, validate_packet,
)

from . import DRAFT_CONTRACT, VIEW_CONTRACT


MAX_INPUT_BYTES = MAX_REVIEW_BYTES
MAX_MANIFEST_BYTES = 64 * 1024


@dataclass(frozen=True, slots=True)
class DeskSources:
    packet_file: JsonFile
    manifest_file: JsonFile
    template_file: JsonFile
    packet: ReviewPacket


@dataclass(frozen=True, slots=True)
class DraftDecision:
    observation_key: str
    review_status: str
    scope_status: str
    client_inclusion: str
    safe_summary: str | None
    reason: str | None
    missing_evidence: str | None
    follow_up: str | None


@dataclass(frozen=True, slots=True)
class DecisionDraft:
    schema_version: str
    review_packet_digest: str
    source_assessment_digest: str
    decisions: tuple[DraftDecision, ...]


def _loaded_identity(value: JsonFile, maximum: int = MAX_INPUT_BYTES) -> None:
    if type(value) is not JsonFile:
        raise InputError("desk_invalid_loaded_json")
    digest(value.sha256)
    integer(value.byte_length, 1, maximum)


def checked_packet_file(packet_file: JsonFile, packet: ReviewPacket) -> ReviewPacket:
    """Revalidate supplied frozen models using the unchanged packet contract."""
    _loaded_identity(packet_file)
    actual = validate_packet(packet_file.data)
    if packet_to_dict(packet) != packet_to_dict(actual):
        raise InputError("desk_packet_model_mismatch")
    return actual


def validate_desk_sources(sources: DeskSources) -> ReviewPacket:
    """Check three selected inputs; never follow manifest entries or paths."""
    if type(sources) is not DeskSources:
        raise InputError("desk_invalid_sources")
    packet = checked_packet_file(sources.packet_file, sources.packet)
    _loaded_identity(sources.manifest_file, MAX_MANIFEST_BYTES)
    validate_packet_manifest(sources.manifest_file, sources.packet_file)
    _loaded_identity(sources.template_file)
    template = validate_overlay(sources.template_file.data)
    if template.decisions:
        raise InputError("desk_overlay_template_must_be_empty")
    if template.review_packet_digest != sources.packet_file.sha256:
        raise InputError("desk_template_packet_digest_mismatch")
    if template.source_assessment_digest != packet.source_assessment.sha256:
        raise InputError("desk_template_source_digest_mismatch")
    return packet


def load_desk_sources(packet_path: str, manifest_path: str, template_path: str) -> DeskSources:
    packet_file = load_review_json(packet_path)
    packet = validate_packet(packet_file.data)
    manifest_file = load_review_json(manifest_path, maximum=MAX_MANIFEST_BYTES)
    template_file = load_review_json(template_path)
    sources = DeskSources(packet_file, manifest_file, template_file, packet)
    validate_desk_sources(sources)
    return sources


def validate_draft(value: object, packet: ReviewPacket | None = None) -> DecisionDraft:
    """Validate draft fields; final semantic/binding checks remain in Phase18.

    A packet is required by finalize_draft and, when provided here, rejects keys
    not present in that packet. No source fingerprint/disposition or identity
    assertion is accepted as a draft field.
    """
    check_json_budget(value)
    root = object_fields(value, ("schema_version", "review_packet_digest",
        "source_assessment_digest", "decisions"))
    literal(root["schema_version"], DRAFT_CONTRACT)
    packet_digest = digest(root["review_packet_digest"])
    source_digest = digest(root["source_assessment_digest"])
    known_keys = None
    if packet is not None:
        packet = validate_packet(packet_to_dict(packet))
        if source_digest != packet.source_assessment.sha256:
            raise InputError("desk_draft_source_digest_mismatch")
        known_keys = {item.observation_key for item in packet.observations}
    decisions = []
    seen_keys = set()
    for item in array(root["decisions"], 256):
        row = object_fields(item, ("observation_key", "review_status", "scope_status",
            "client_inclusion", "safe_summary", "reason", "missing_evidence", "follow_up"))
        key = row["observation_key"]
        if type(key) is not str:
            raise InputError("desk_invalid_observation_key")
        match = re.fullmatch(r"sha256:([a-f0-9]{64})#/items/(0|[1-9][0-9]{0,3})", key)
        if match is None or match.group(1) != source_digest:
            raise InputError("desk_invalid_observation_key")
        if key in seen_keys:
            raise InputError("desk_duplicate_observation")
        seen_keys.add(key)
        if known_keys is not None and key not in known_keys:
            raise InputError("desk_unknown_observation")
        decisions.append(DraftDecision(
            key, enum_value(row["review_status"], REVIEW_STATUSES),
            enum_value(row["scope_status"], SCOPES),
            enum_value(row["client_inclusion"], INCLUSIONS),
            text(row["safe_summary"], 2048, nullable=True),
            text(row["reason"], 2048, nullable=True),
            text(row["missing_evidence"], 1024, nullable=True),
            text(row["follow_up"], 1024, nullable=True),
        ))
    return DecisionDraft(DRAFT_CONTRACT, packet_digest, source_digest, tuple(decisions))


def load_draft(raw_path: str) -> DecisionDraft:
    return validate_draft(load_review_json(raw_path).data)


def finalize_draft(packet_file: JsonFile, packet: ReviewPacket,
                   original: LoadedInput, draft_file: JsonFile) -> dict:
    """Build an existing Phase18 overlay using explicit declarations only.

    All inputs are captured by explicit CLI loaders. This pure function opens no
    files and fabricates no LoadedInput, source metadata, person or timestamp.
    The CLI checks the separately selected packet manifest before this call.
    The technical decision ID records a submitted draft row, never expertise.
    """
    packet = checked_packet_file(packet_file, packet)
    _loaded_identity(draft_file)
    draft = validate_draft(draft_file.data, packet)
    if draft.review_packet_digest != packet_file.sha256:
        raise InputError("desk_draft_packet_digest_mismatch")
    observations = {item.observation_key: item for item in packet.observations}
    overlay = make_empty_overlay(packet_file.sha256, packet.source_assessment.sha256)
    rows = []
    for decision in draft.decisions:
        source = observations[decision.observation_key]
        values = {
            "decision_id": "DESK-" + source.observation_id,
            "observation_id": source.observation_id,
            "observation_key": source.observation_key,
            "source_assessment_sha256": packet.source_assessment.sha256,
            "source_json_pointer": source.source_json_pointer,
            "fingerprint": source.fingerprint,
            "capability_id": source.capability_id,
            "source_disposition": source.source_disposition,
            "scope_status": decision.scope_status,
            "review_status": decision.review_status,
            "client_inclusion": decision.client_inclusion,
            "safe_summary": decision.safe_summary,
            "reason": decision.reason,
            "missing_evidence": decision.missing_evidence,
            "follow_up": decision.follow_up,
            "reviewer_ref": None,
            "reviewed_at": None,
        }
        # Reuse the authoritative exact 17-field canonical digest and semantic
        # rules. JavaScript never computes or claims an overlay context digest.
        values["decision_context_digest"] = decision_context_digest(values)
        rows.append(values)
    overlay["decisions"] = rows
    checked = validate_overlay(overlay)
    bind_decisions(packet, original, checked, packet_digest=packet_file.sha256)
    result = overlay_to_dict(checked)
    check_json_budget(result)
    return result


def render_overlay(value: object) -> bytes:
    return json_bytes(overlay_to_dict(validate_overlay(value)))
