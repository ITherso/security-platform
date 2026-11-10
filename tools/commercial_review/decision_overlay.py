"""Closed declarative analyst overlay; digests bind content, not human identity."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import re

from commercial_handoff.schema import DISPOSITIONS, INCLUSIONS, REVIEW_STATUSES, SCOPES

from . import DEMO_LABEL, OVERLAY_CONTRACT
from .review_contracts import (
    ReviewError, array, check_json_budget, digest, enum_value, identifier,
    literal, object_fields, text,
)


_ROOT_FIELDS = frozenset(("schema_version", "review_packet_digest",
    "source_assessment_digest", "decisions", "review_context"))
_CONTEXT_FIELDS = frozenset(("mode", "demo_label", "demo_only", "human_review_verified",
    "producer_verified", "release_authorized"))
DECISION_CONTEXT_FIELDS = frozenset((
    "decision_id", "observation_id", "observation_key", "source_assessment_sha256",
    "source_json_pointer", "fingerprint", "capability_id", "source_disposition",
    "scope_status", "review_status", "client_inclusion", "safe_summary", "reason",
    "missing_evidence", "follow_up", "reviewer_ref", "reviewed_at",
))
_DECISION_FIELDS = DECISION_CONTEXT_FIELDS | {"decision_context_digest"}
_ELIGIBLE = frozenset(("informational_only", "reviewed_for_delivery"))


@dataclass(frozen=True, slots=True)
class ReviewContext:
    mode: str
    demo_label: str
    demo_only: bool
    human_review_verified: bool
    producer_verified: bool
    release_authorized: bool


@dataclass(frozen=True, slots=True)
class AnalystDecision:
    decision_id: str
    observation_id: str
    observation_key: str
    source_assessment_sha256: str
    source_json_pointer: str
    fingerprint: str
    capability_id: str
    source_disposition: str
    scope_status: str
    review_status: str
    client_inclusion: str
    safe_summary: str | None
    reason: str | None
    missing_evidence: str | None
    follow_up: str | None
    reviewer_ref: str | None
    reviewed_at: str | None
    decision_context_digest: str


@dataclass(frozen=True, slots=True)
class DecisionOverlay:
    schema_version: str
    review_packet_digest: str
    source_assessment_digest: str
    decisions: tuple[AnalystDecision, ...]
    review_context: ReviewContext


def _decision_values(value: object) -> dict:
    row = object_fields(value, DECISION_CONTEXT_FIELDS)
    pointer = row["source_json_pointer"]
    if type(pointer) is not str or re.fullmatch(r"/items/(0|[1-9][0-9]{0,3})", pointer) is None:
        raise ReviewError("invalid_decision_source_pointer")
    source_sha = digest(row["source_assessment_sha256"])
    key = row["observation_key"]
    if type(key) is not str or key != f"sha256:{source_sha}#{pointer}":
        raise ReviewError("invalid_decision_observation_key")
    fingerprint = row["fingerprint"]
    if type(fingerprint) is not str or re.fullmatch(r"sha256:[a-f0-9]{64}", fingerprint) is None:
        raise ReviewError("invalid_decision_fingerprint")
    capability = text(row["capability_id"], 128, maximum_lines=1)
    if re.fullmatch(r"[A-Za-z0-9._@-]+", capability) is None:
        raise ReviewError("invalid_decision_capability")
    reviewed_at = text(row["reviewed_at"], 20, nullable=True, maximum_lines=1)
    if reviewed_at is not None:
        try:
            if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", reviewed_at) is None:
                raise ValueError()
            datetime.strptime(reviewed_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            raise ReviewError("invalid_declared_review_time") from None
    result = {
        "decision_id": identifier(row["decision_id"]),
        "observation_id": identifier(row["observation_id"]),
        "observation_key": key,
        "source_assessment_sha256": source_sha,
        "source_json_pointer": pointer,
        "fingerprint": fingerprint,
        "capability_id": capability,
        "source_disposition": enum_value(row["source_disposition"], DISPOSITIONS),
        "scope_status": enum_value(row["scope_status"], SCOPES),
        "review_status": enum_value(row["review_status"], REVIEW_STATUSES),
        "client_inclusion": enum_value(row["client_inclusion"], INCLUSIONS),
        "safe_summary": text(row["safe_summary"], 2048, nullable=True),
        "reason": text(row["reason"], 2048, nullable=True),
        "missing_evidence": text(row["missing_evidence"], 1024, nullable=True),
        "follow_up": text(row["follow_up"], 1024, nullable=True),
        "reviewer_ref": text(row["reviewer_ref"], 128, nullable=True, maximum_lines=1),
        "reviewed_at": reviewed_at,
    }
    if result["client_inclusion"] == "include_with_limits" and (
        result["review_status"] not in _ELIGIBLE
        or result["scope_status"] != "in_scope" or result["safe_summary"] is None
    ):
        raise ReviewError("invalid_requested_inclusion")
    if (result["review_status"] == "excluded_with_reason"
            or result["client_inclusion"] == "exclude_with_reason") and result["reason"] is None:
        raise ReviewError("exclusion_reason_required")
    return result


def decision_context_digest(value: object) -> str:
    """SHA256 of the exact validated row minus decision_context_digest.

    Canonical bytes: UTF-8, ensure_ascii=False, sort_keys=True, compact JSON
    separators (',', ':'), allow_nan=False, no trailing newline. All fields,
    including nulls and exact safe_summary/reason text, participate. There is no
    whitespace trimming, Unicode normalization or narrative inheritance.
    Anyone can recompute this digest; it is not a signature or expert proof.
    """
    values = _decision_values(value)
    check_json_budget(values)
    encoded = json.dumps(values, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8", "strict")
    return hashlib.sha256(encoded).hexdigest()


def _decision(value: object) -> AnalystDecision:
    row = object_fields(value, _DECISION_FIELDS)
    values = _decision_values({key: row[key] for key in DECISION_CONTEXT_FIELDS})
    claimed = digest(row["decision_context_digest"])
    if claimed != decision_context_digest(values):
        raise ReviewError("decision_context_digest_mismatch")
    return AnalystDecision(**values, decision_context_digest=claimed)


def validate_overlay(value: object) -> DecisionOverlay:
    check_json_budget(value)
    root = object_fields(value, _ROOT_FIELDS)
    literal(root["schema_version"], OVERLAY_CONTRACT)
    context = object_fields(root["review_context"], _CONTEXT_FIELDS)
    literal(context["mode"], "demo")
    literal(context["demo_label"], DEMO_LABEL)
    literal(context["demo_only"], True)
    for key in ("human_review_verified", "producer_verified", "release_authorized"):
        literal(context[key], False)
    decisions = tuple(_decision(row) for row in array(root["decisions"], 256))
    if len({row.decision_id for row in decisions}) != len(decisions):
        raise ReviewError("duplicate_decision_id")
    if (len({row.observation_id for row in decisions}) != len(decisions)
            or len({row.observation_key for row in decisions}) != len(decisions)):
        raise ReviewError("duplicate_decision_observation")
    return DecisionOverlay(OVERLAY_CONTRACT, digest(root["review_packet_digest"]),
        digest(root["source_assessment_digest"]), decisions, ReviewContext(
            "demo", DEMO_LABEL, True, False, False, False))


def _decision_to_dict(row: AnalystDecision) -> dict:
    return {name: getattr(row, name) for name in _DECISION_FIELDS}


def overlay_to_dict(overlay: DecisionOverlay) -> dict:
    if (type(overlay) is not DecisionOverlay or type(overlay.review_context) is not ReviewContext
            or type(overlay.decisions) is not tuple
            or any(type(row) is not AnalystDecision for row in overlay.decisions)):
        raise ReviewError("invalid_overlay_model")
    context = overlay.review_context
    return {
        "schema_version": overlay.schema_version,
        "review_packet_digest": overlay.review_packet_digest,
        "source_assessment_digest": overlay.source_assessment_digest,
        "decisions": [_decision_to_dict(row) for row in overlay.decisions],
        "review_context": {
            "mode": context.mode,
            "demo_label": context.demo_label,
            "demo_only": context.demo_only,
            "human_review_verified": context.human_review_verified,
            "producer_verified": context.producer_verified,
            "release_authorized": context.release_authorized,
        },
    }


def make_empty_overlay(packet_digest: str, source_digest: str) -> dict:
    """Return an unfilled, demo-only overlay without person, time or decision."""
    result = {
        "schema_version": OVERLAY_CONTRACT,
        "review_packet_digest": digest(packet_digest),
        "source_assessment_digest": digest(source_digest),
        "decisions": [],
        "review_context": {
            "mode": "demo", "demo_label": DEMO_LABEL, "demo_only": True, "human_review_verified": False,
            "producer_verified": False, "release_authorized": False,
        },
    }
    validate_overlay(result)
    return result
