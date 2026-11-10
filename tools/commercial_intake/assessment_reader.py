"""Bounded, read-only native assessment subset for the demo handoff bridge.

The native owning contracts are Termivar reporting.rs and comparison/import.rs
at 6a2639348c2366d0bf71b9a34e5484d40aa393a3. This bridge intentionally supports
only the base complete web-review document, four passive capabilities and two
closed category labels. Validation does not authenticate source or findings.
Repeated fingerprint labels remain separate source positions; native importer
fingerprint-uniqueness acceptance is not established by this metadata reader.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
import re
import stat

from commercial_handoff.input_loader import (
    _depth_check,
    _integer,
    _pairs,
    _reject_number,
    check_existing_path,
    explicit_relative_path,
)
from commercial_handoff.schema import InputError


MAX_ASSESSMENT_BYTES = 1024 * 1024
MAX_ASSESSMENT_ITEMS = 256
MAX_JSON_NODES = 50000
MAX_JSON_TEXT_BYTES = 512 * 1024
MAX_JSON_STRING_CHARACTERS = 8192
MAX_DISPLAY_BYTES = 1024
MAX_IDENTIFIER_BYTES = 128
MAX_EVIDENCE_REFERENCES = 256
MAX_SUBJECTS = 1024
UINT32_MAX = (1 << 32) - 1

ROOT_FIELDS = frozenset((
    "schema", "source_schema", "run_schema", "profile_schema", "profile", "status",
    "subject_count", "item_count", "items",
))
ITEM_FIELDS = frozenset((
    "schema", "capability_id", "subject_reference", "title", "disposition",
    "claim_basis", "severity", "confidence_ppm", "fingerprint", "evidence_count",
    "redacted_summary", "category", "cwe", "remediation", "evidence_references",
    "control_evidence_references", "candidate_evidence_references", "case_reference",
    "outcome_reference", "verification_stage",
))
KNOWN_OPTIONAL_AUDITS = frozenset((
    "authorization_review", "openapi_review", "rest_review", "secret_exposure_review",
    "tls_observation", "tls_negotiation_review", "websocket_review", "jwt_policy_review",
    "xml_external_entity_review", "template_evaluation_review", "control_reference_mapping",
    "recon_snapshot_import", "recon_certspotter", "supplied_session", "wordpress_review",
    "wordpress_discovery", "wordpress_asset_fingerprints",
))
SUPPORTED_CAPABILITIES = frozenset((
    "web.passive.referrer-policy.missing@1",
    "web.passive.x-content-type-options.missing@1",
    "web.passive.permissions-policy.missing@1",
    "web.passive.csp.missing@1",
))
SUPPORTED_CATEGORIES = frozenset(("browser-defense", "content-policy"))
DISPOSITIONS = frozenset(("informational", "needs_review", "confirmed"))
CLAIM_BASES = frozenset(("observation", "differential", "verifier_transition"))
SEVERITIES = frozenset(("info", "low", "medium", "high", "critical"))
VERIFICATION_STAGES = frozenset(("passive", "active"))


@dataclass(frozen=True, slots=True)
class JsonFile:
    """Selected JSON and its exact byte identity; no referenced files are read."""

    data: object
    sha256: str
    byte_length: int


@dataclass(frozen=True, slots=True)
class NativeItem:
    index: int
    fingerprint: str
    capability_id: str
    disposition: str
    claim_basis: str
    category: str
    subject_reference: str
    evidence_count: int
    evidence_references: tuple[str, ...]
    control_evidence_references: tuple[str, ...]
    candidate_evidence_references: tuple[str, ...]
    case_reference: str | None
    outcome_reference: str | None
    verification_stage: str | None


@dataclass(frozen=True, slots=True)
class AssessmentSource:
    sha256: str
    byte_length: int
    schema: str
    source_schema: str
    run_schema: str
    profile_schema: str
    profile: str
    status: str
    subject_count: int
    items: tuple[NativeItem, ...]

    @property
    def item_count(self) -> int:
        return len(self.items)


def _tree_budget(value: object) -> None:
    stack = [value]
    nodes = text_bytes = 0
    while stack:
        item = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise InputError("json_node_limit")
        if type(item) is str:
            try:
                encoded = item.encode("utf-8", "strict")
            except UnicodeError:
                raise InputError("invalid_unicode") from None
            if len(item) > MAX_JSON_STRING_CHARACTERS:
                raise InputError("json_string_limit")
            text_bytes += len(encoded)
            if text_bytes > MAX_JSON_TEXT_BYTES:
                raise InputError("json_text_budget")
        elif type(item) is dict:
            stack.extend(item.keys())
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)


def read_json_file(raw_path: str, maximum: int = MAX_ASSESSMENT_BYTES) -> JsonFile:
    """Read exactly one explicit regular JSON file using preserved path guards.

    The caller selects a trusted byte ceiling, at most the bridge's 1 MiB limit.
    Generic parsed data is local to consumers; read_assessment never returns it.
    Filesystem races and OS permissions are not established by these checks.
    """
    if type(maximum) is not int or not 1 <= maximum <= MAX_ASSESSMENT_BYTES:
        raise InputError("invalid_json_read_limit")
    path = explicit_relative_path(raw_path)
    info = check_existing_path(path, directory=False)
    if path.suffix.lower() != ".json" or not 0 < info.st_size <= maximum:
        raise InputError("invalid_input_file_size_or_type")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)):
            raise InputError("input_identity_changed")
        if (getattr(opened, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise InputError("linked_path_not_allowed")
        raw = stream.read(maximum + 1)
    if not 0 < len(raw) <= maximum:
        raise InputError("input_size_limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputError("invalid_utf8") from None
    if text.startswith("\ufeff"):
        raise InputError("utf8_bom_not_supported")
    # This preserved helper applies the Phase16 depth-12 string-aware guard.
    _depth_check(text)
    try:
        data = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer,
                          parse_float=_reject_number, parse_constant=_reject_number)
    except (json.JSONDecodeError, RecursionError):
        raise InputError("invalid_json") from None
    _tree_budget(data)
    return JsonFile(data, hashlib.sha256(raw).hexdigest(), len(raw))


def _object(value: object, fields: frozenset[str]) -> dict:
    if type(value) is not dict or set(value) != fields:
        raise InputError("invalid_source_fields")
    return value


def _text(value: object, maximum: int, *, nullable: bool = False) -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or not value:
        raise InputError("invalid_source_text")
    try:
        length = len(value.encode("utf-8", "strict"))
    except UnicodeError:
        raise InputError("invalid_unicode") from None
    if length > maximum:
        raise InputError("invalid_source_text")
    return value


def _number(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise InputError("invalid_source_number")
    return value


def _token(value: object, allowed: frozenset[str], *, nullable: bool = False,
           code: str = "invalid_source_enum") -> str | None:
    if nullable and value is None:
        return None
    if type(value) is not str or value not in allowed:
        raise InputError(code)
    return value


def _reference(value: object, kind: str, *, nullable: bool = False) -> str | None:
    text = _text(value, MAX_IDENTIFIER_BYTES, nullable=nullable)
    if text is None:
        return None
    match = re.fullmatch(re.escape(kind) + r"-([0-9]{4}|[1-9][0-9]{4,9})", text)
    if match is None or int(match.group(1)) > UINT32_MAX:
        raise InputError("invalid_source_reference")
    return text


def _references(value: object) -> tuple[str, ...]:
    if type(value) is not list or len(value) > MAX_EVIDENCE_REFERENCES:
        raise InputError("invalid_source_evidence")
    # Nullable is false: each validated reference is a string.
    return tuple(_reference(entry, "evidence") for entry in value)


def _item(value: object, index: int, subject_count: int) -> NativeItem:
    row = _object(value, ITEM_FIELDS)
    if type(row["schema"]) is not str or row["schema"] != "venom-assessment-item/v1":
        raise InputError("unsupported_source_schema")
    fingerprint = row["fingerprint"]
    if type(fingerprint) is not str or re.fullmatch(r"sha256:[a-f0-9]{64}", fingerprint) is None:
        raise InputError("invalid_source_fingerprint")
    # A reported fingerprint is not the mapping identity by itself. Preserve
    # each source array position; do not merge repeated fingerprint labels.
    # This metadata reader does not claim the native importer's uniqueness proof.

    capability = _text(row["capability_id"], MAX_IDENTIFIER_BYTES)
    if capability not in SUPPORTED_CAPABILITIES:
        raise InputError("unsupported_source_capability")
    category = _text(row["category"], MAX_DISPLAY_BYTES)
    if category not in SUPPORTED_CATEGORIES:
        raise InputError("unsupported_source_category")
    subject = _reference(row["subject_reference"], "subject")
    if int(subject.split("-", 1)[1]) >= subject_count:
        raise InputError("invalid_source_reference")

    # Validate these native values, then discard them. No free display text,
    # remediation text, CWE, severity or confidence enters the reduced DTO.
    _text(row["title"], MAX_DISPLAY_BYTES)
    _text(row["redacted_summary"], MAX_DISPLAY_BYTES)
    _text(row["cwe"], MAX_IDENTIFIER_BYTES, nullable=True)
    _token(row["severity"], SEVERITIES, nullable=True)
    _number(row["confidence_ppm"], 0, 1000000)
    remediation = _object(row["remediation"], frozenset(("id", "summary")))
    _text(remediation["id"], MAX_IDENTIFIER_BYTES)
    _text(remediation["summary"], MAX_DISPLAY_BYTES)

    direct = _references(row["evidence_references"])
    control = _references(row["control_evidence_references"])
    candidate = _references(row["candidate_evidence_references"])
    combined = direct + control + candidate
    evidence_count = _number(row["evidence_count"], 0, MAX_EVIDENCE_REFERENCES)
    if len(set(combined)) != len(combined) or evidence_count != len(combined):
        raise InputError("invalid_source_evidence")
    case = _reference(row["case_reference"], "case", nullable=True)
    outcome = _reference(row["outcome_reference"], "outcome", nullable=True)
    stage = _token(row["verification_stage"], VERIFICATION_STAGES, nullable=True)
    disposition = _token(row["disposition"], DISPOSITIONS,
                         code="unsupported_source_disposition")
    basis = _token(row["claim_basis"], CLAIM_BASES)
    no_verifier = case is None and outcome is None and stage is None
    if basis == "observation":
        valid = (disposition == "informational" and len(direct) > 0
                 and not control and not candidate and no_verifier)
    elif basis == "differential":
        valid = (disposition == "needs_review" and no_verifier
                 and ((len(direct) == 1 and not control and not candidate)
                      or (not direct and len(control) > 0 and len(candidate) > 0)))
    else:
        valid = (disposition == "confirmed" and len(direct) > 0
                 and not control and not candidate and case is not None
                 and outcome is not None and stage is not None)
    if not valid:
        raise InputError("invalid_source_linkage")
    return NativeItem(index, fingerprint, capability, disposition, basis, category,
                      subject, evidence_count, direct, control, candidate, case,
                      outcome, stage)


def read_assessment(raw_path: str) -> AssessmentSource:
    """Validate the explicit narrow v1 profile and return closed metadata only."""
    selected = read_json_file(raw_path)
    if type(selected.data) is not dict:
        raise InputError("invalid_source_fields")
    if KNOWN_OPTIONAL_AUDITS.intersection(selected.data):
        raise InputError("unsupported_source_extension")
    root = _object(selected.data, ROOT_FIELDS)
    for field, expected in (
        ("schema", "venom-rendered-assessment/v1"),
        ("source_schema", "venom-assessment-run/v1"),
        ("run_schema", "venom-run/v1"),
        ("profile_schema", "venom.scan-profile/v1"),
    ):
        if type(root[field]) is not str or root[field] != expected:
            raise InputError("unsupported_source_schema")
    if type(root["profile"]) is not str or root["profile"] != "web-review":
        raise InputError("unsupported_source_profile")
    if type(root["status"]) is not str or root["status"] != "complete":
        raise InputError("unsupported_source_status")
    subject_count = _number(root["subject_count"], 1, MAX_SUBJECTS)
    item_count = root["item_count"]
    if type(item_count) is not int or item_count < 0:
        raise InputError("invalid_source_number")
    if item_count > MAX_ASSESSMENT_ITEMS:
        raise InputError("source_observation_limit")
    rows = root["items"]
    if type(rows) is not list:
        raise InputError("invalid_source_fields")
    if len(rows) > MAX_ASSESSMENT_ITEMS:
        raise InputError("source_observation_limit")
    if len(rows) != item_count:
        raise InputError("source_item_count_mismatch")
    items = tuple(_item(row, index, subject_count)
                  for index, row in enumerate(rows))
    return AssessmentSource(
        selected.sha256, selected.byte_length, root["schema"], root["source_schema"],
        root["run_schema"], root["profile_schema"], root["profile"], root["status"],
        subject_count, items,
    )
