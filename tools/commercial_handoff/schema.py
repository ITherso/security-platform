"""Closed, demo-only handoff input contract; no Termivar runtime imports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re

CONTRACT = "termivar-handoff-draft/v1"
MAX_INPUT_BYTES = 256 * 1024
MAX_DEPTH = 12
MAX_NODES = 10000
MAX_TEXT_BYTES = 128 * 1024
REVIEW_STATUSES = frozenset(("unreviewed", "needs_manual_review", "informational_only",
    "inconclusive", "excluded_with_reason", "reviewed_for_delivery"))
INCLUSIONS = frozenset(("pending_decision", "include_with_limits", "exclude_with_reason"))
SCOPES = frozenset(("in_scope", "out_of_scope", "unknown"))
DISPOSITIONS = frozenset(("informational", "needs_review", "confirmed"))
SOURCE_CONTRACTS = frozenset(("venom-rendered-assessment/v1", "termivar-report-bundle/v1",
    "termivar-report-comparison/v1", "web-assessment/v2"))
AUTHORIZATIONS = frozenset(("not_provided", "not_verified", "pending_decision"))
COMPLETIONS = frozenset(("complete", "incomplete", "failed", "not_provided"))


class InputError(ValueError):
    """Fixed, non-sensitive error codes only; never include supplied values."""


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    artifact_id: str
    contract: str
    sha256: str
    byte_length: int
    completion_status: str
    provenance_note: str


@dataclass(frozen=True, slots=True)
class Observation:
    observation_id: str
    source_artifact: str | None
    observation_ref: str | None
    source_json_pointer: str | None
    capability_id: str
    source_disposition: str
    review_status: str
    scope_status: str
    client_inclusion: str
    safe_summary: str | None
    evidence_limitations: str
    decision_ref: str | None


@dataclass(frozen=True, slots=True)
class ReviewDecision:
    decision_id: str
    observation_id: str
    review_status: str
    client_inclusion: str
    reviewer_ref: str | None
    reviewed_at: str | None
    reason: str


@dataclass(frozen=True, slots=True)
class HandoffInput:
    schema_version: str
    case_id: str
    mode: str
    scope_summary: str
    authorization_status: str
    source_artifacts: tuple[SourceArtifact, ...]
    observations: tuple[Observation, ...]
    review_decisions: tuple[ReviewDecision, ...]
    delivery_constraints: tuple[str, ...]


def _object(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise InputError("invalid_fields")
    return value


def _text(value, maximum=2048, *, nullable=False):
    if nullable and value is None:
        return None
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise InputError("invalid_text")
    try:
        value.encode("utf-8", "strict")
    except UnicodeError:
        raise InputError("invalid_unicode") from None
    if any((ord(c) < 32 and c not in "\n\r\t") or 127 <= ord(c) <= 159 for c in value):
        raise InputError("invalid_control_character")
    return value


def _identifier(value, *, nullable=False):
    if nullable and value is None:
        return None
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", value):
        raise InputError("invalid_identifier")
    return value


def _enum(value, allowed):
    if type(value) is not str or value not in allowed:
        raise InputError("invalid_enum")
    return value


def _array(value, maximum, minimum=0):
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise InputError("invalid_array")
    return value


def _fingerprint(value, *, prefix=False, nullable=False):
    if nullable and value is None:
        return None
    pattern = r"sha256:[a-f0-9]{64}" if prefix else r"[a-f0-9]{64}"
    if type(value) is not str or not re.fullmatch(pattern, value):
        raise InputError("invalid_fingerprint")
    return value


def _unique(values):
    if len(set(values)) != len(values):
        raise InputError("duplicate_identifier")


def validate(value) -> HandoffInput:
    root = _object(value, ("schema_version", "case_id", "mode", "scope_summary",
        "authorization_status", "source_artifacts", "observations", "review_decisions",
        "delivery_constraints"))
    if root["schema_version"] != CONTRACT or type(root["schema_version"]) is not str:
        raise InputError("unsupported_schema")
    if root["mode"] != "demo" or type(root["mode"]) is not str:
        raise InputError("demo_mode_required")
    artifacts = []
    for row in _array(root["source_artifacts"], 32):
        r = _object(row, ("artifact_id", "contract", "sha256", "byte_length",
            "completion_status", "provenance_note"))
        size = r["byte_length"]
        if type(size) is not int or not 1 <= size <= 16 * 1024 * 1024:
            raise InputError("invalid_byte_length")
        artifacts.append(SourceArtifact(_identifier(r["artifact_id"]),
            _enum(r["contract"], SOURCE_CONTRACTS), _fingerprint(r["sha256"]), size,
            _enum(r["completion_status"], COMPLETIONS), _text(r["provenance_note"])))
    observations = []
    for row in _array(root["observations"], 256):
        r = _object(row, ("observation_id", "source_artifact", "observation_ref",
            "source_json_pointer", "capability_id", "source_disposition", "review_status",
            "scope_status", "client_inclusion", "safe_summary", "evidence_limitations",
            "decision_ref"))
        pointer = r["source_json_pointer"]
        if pointer is not None and (type(pointer) is not str or not re.fullmatch(r"/items/(0|[1-9][0-9]{0,3})", pointer)):
            raise InputError("invalid_source_pointer")
        capability = _text(r["capability_id"], 128)
        if not re.fullmatch(r"[A-Za-z0-9._@-]+", capability):
            raise InputError("invalid_capability_id")
        observations.append(Observation(_identifier(r["observation_id"]),
            _identifier(r["source_artifact"], nullable=True),
            _fingerprint(r["observation_ref"], prefix=True, nullable=True), pointer, capability,
            _enum(r["source_disposition"], DISPOSITIONS), _enum(r["review_status"], REVIEW_STATUSES),
            _enum(r["scope_status"], SCOPES), _enum(r["client_inclusion"], INCLUSIONS),
            _text(r["safe_summary"], nullable=True), _text(r["evidence_limitations"]),
            _identifier(r["decision_ref"], nullable=True)))
    decisions = []
    for row in _array(root["review_decisions"], 256):
        r = _object(row, ("decision_id", "observation_id", "review_status", "client_inclusion",
            "reviewer_ref", "reviewed_at", "reason"))
        reviewed_at = _text(r["reviewed_at"], 20, nullable=True)
        if reviewed_at is not None:
            try:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", reviewed_at):
                    raise ValueError()
                datetime.strptime(reviewed_at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                raise InputError("invalid_review_time") from None
        decisions.append(ReviewDecision(_identifier(r["decision_id"]),
            _identifier(r["observation_id"]), _enum(r["review_status"], REVIEW_STATUSES),
            _enum(r["client_inclusion"], INCLUSIONS), _text(r["reviewer_ref"], 128, nullable=True),
            reviewed_at, _text(r["reason"])))
    _unique([r.artifact_id for r in artifacts])
    _unique([r.observation_id for r in observations])
    _unique([r.decision_id for r in decisions])
    return HandoffInput(CONTRACT, _identifier(root["case_id"]), "demo",
        _text(root["scope_summary"], 1024), _enum(root["authorization_status"], AUTHORIZATIONS),
        tuple(artifacts), tuple(observations), tuple(decisions),
        tuple(_text(x, 1024) for x in _array(root["delivery_constraints"], 32, 1)))
