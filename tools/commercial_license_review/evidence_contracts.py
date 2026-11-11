"""Closed Phase25 metadata contracts; evidence never grants legal authority."""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
import re

from commercial_composition.composition_contracts import (
    InputError, CANDIDATE_REFERENCE, EVIDENCE_LEVELS as BASE_EVIDENCE_LEVELS,
    closed, text, integer, identifier, relative_path, sha256, parse_json, json_bytes,
)

SCOPE_SCHEMA = "termivar-license-evidence-scope/v1"
LEDGER_SCHEMA = "termivar-license-evidence-ledger/v1"
QUEUE_SCHEMA = "termivar-license-review-queue/v1"
CONFLICTS_SCHEMA = "termivar-license-binding-conflicts/v1"
MANIFEST_SCHEMA = "termivar-license-evidence-manifest/v1"
INSPECTION_SCHEMA = "termivar-license-evidence-inspection/v1"
SOURCE_BINDING_SCHEMA = "termivar-license-source-binding/v1"
SOURCE_KEY_PREFIX = "termivar-license-binding/v1:"
DEMO_LABEL = "DEMONSTRATION ONLY — LICENSE EVIDENCE REVIEW — NO DISTRIBUTION AUTHORIZED"
FALSE_FLAGS = (
    "license_review_completed", "redistribution_authorized", "release_authorized",
    "production_ready", "build_verified", "runtime_verified", "producer_verified",
    "human_review_verified",
)
MAX_SCOPE_BYTES = 128 * 1024
MAX_RECORDS = 1024
MAX_EVIDENCE_SOURCES = 64
MAX_BINDING_REQUESTS = 256
MAX_EVIDENCE_FILE_BYTES = 256 * 1024
MAX_TOTAL_EVIDENCE_BYTES = 2 * 1024 * 1024
REFERENCE_ROLES = ("inventory", "dependencies", "constraints", "summary", "manifest")
REFERENCE_LIMITS = {"inventory": 1024 * 1024, "dependencies": 1024 * 1024,
                    "constraints": 1024 * 1024, "summary": 512 * 1024,
                    "manifest": 64 * 1024}
EVIDENCE_KINDS = (
    "first_party_license_file", "dependency_license_file", "package_metadata",
    "source_manifest_declaration", "unverified_external_evidence", "missing_evidence",
)
BINDING_STATUSES = (
    "binding_confirmed_within_source", "binding_ambiguous", "binding_conflict",
    "evidence_missing", "evidence_unsupported", "source_not_verified",
)
EVIDENCE_STATUSES = (
    "evidence_present", "evidence_missing", "binding_ambiguous", "binding_conflict",
    "evidence_unsupported", "source_not_verified",
)
REVIEW_STATUSES = ("review_required", "conflicting_evidence", "insufficient_evidence", "decision_pending")
REASON_CODES = (
    "source_selector_mismatch", "explicit_evidence_missing", "evidence_hash_mismatch",
    "external_source_not_verified", "evidence_type_subject_mismatch",
    "source_file_reference_not_matched", "source_file_reference_ambiguous",
    "evidence_format_unsupported", "evidence_kind_format_mismatch", "source_file_binding_confirmed",
    "evidence_not_selected_for_record", "conflicting_license_declarations",
    "dependency_metadata_identity_not_established",
)
NEXT_HUMAN_ACTIONS = (
    "review_source_conflicts_without_approval", "clarify_source_record_binding",
    "provide_scoped_local_evidence", "perform_independent_license_review", "provide_supported_evidence_format",
)
PRODUCT_SCOPES = ("proposed_source_component", "selected_source_metadata", "excluded_backend_context")
CONFLICT_CATEGORIES = (
    "duplicate_content", "different_content", "conflicting_license_declarations",
    "ambiguous_binding", "source_not_verified", "evidence_missing", "evidence_hash_mismatch",
    "unsupported_evidence", "source_selector_mismatch",
)
QUEUE_GROUPS = (
    "conflicting_evidence", "ambiguous_binding", "missing_evidence",
    "evidence_present_review_pending", "unsupported_evidence",
)
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "composition_reference", *FALSE_FLAGS)
SUBJECT_FIELDS = (
    "source_key", "source_license_id", "subject_type", "subject_id", "source_artifact",
    "source_artifact_sha256", "source_json_pointer", "source_record_sha256",
    "license_record_pointer", "license_record_sha256", "ecosystem", "name", "version",
    "source_type", "manifest_id", "manifest_file_ref", "product_scope", "base_declared_license",
    "base_evidence_level", "base_source_file_refs", "base_human_review_required",
)
SOURCE_FIELDS = (
    "evidence_id", "kind", "file_present", "bytes", "sha256", "expected_sha256",
    "integrity_status", "format_status", "observed_license_labels", "baseline_file_refs", "source_verified",
)
BINDING_FIELDS = (
    "request_id", "evidence_id", "source_key", "status", "reason_codes",
    "matched_source_file_ref", "observed_license_labels",
)
RECORD_FIELDS = (
    "source_key", "evidence_refs", "request_refs", "evidence_status", "review_status",
    "observed_license_labels", "reason_codes", "human_review_required", "phase24_license_review_required",
)
LEDGER_COUNT_FIELDS = (
    "source_record_count", "base_unknown_license_count", "evidence_file_count", "binding_request_count",
    "evidence_present_record_count", "missing_evidence_record_count", "ambiguous_record_count",
    "conflicting_record_count", "unsupported_record_count", "unverified_source_record_count",
)


def _fail(label: str) -> None:
    raise InputError("license_evidence_invalid_" + label)


def _enum(value: object, options: object, label: str) -> str:
    if type(value) is not str or value not in options:
        _fail(label)
    return value


def _fixed(value: object, expected: object, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        _fail(label)


def _array(value: object, maximum: int, label: str, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        _fail(label)
    return value


def _unique(values: list, label: str) -> None:
    if len(values) != len(set(values)):
        _fail(label)


def _refs(value: object, maximum: int, label: str) -> list[str]:
    values = _array(value, maximum, label)
    for item in values:
        identifier(item, label)
    _unique(values, label)
    return values


def _file_ref(value: object, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if (type(value) is not str or re.fullmatch(r"F[0-9]{4}", value) is None
            or not 1 <= int(value[1:]) <= 5000):
        _fail(label)
    return value


def _file_refs(value: object, label: str) -> list[str]:
    values = _array(value, 5000, label)
    for item in values:
        _file_ref(item, label)
    _unique(values, label)
    return values


def _license_id(value: object, label: str) -> str:
    if (type(value) is not str or re.fullmatch(r"L[0-9]{4,5}", value) is None
            or not 1 <= int(value[1:]) <= MAX_RECORDS):
        _fail(label)
    return value


def _source_key(value: object, label: str) -> str:
    if (type(value) is not str or not value.startswith(SOURCE_KEY_PREFIX)
            or re.fullmatch(r"[0-9a-f]{64}", value[len(SOURCE_KEY_PREFIX):]) is None):
        _fail(label)
    return value


def _labels(value: object, label: str, maximum: int = 8) -> list[str]:
    labels = _array(value, maximum, label)
    for item in labels:
        text(item, label, 256)
        if (re.fullmatch(r"[A-Za-z0-9 .()+:/_-]+", item) is None
                or "://" in item or item != item.strip()):
            _fail(label)
    _unique(labels, label)
    return labels


def _codes(value: object, label: str) -> list[str]:
    values = _refs(value, 64, label)
    for code in values:
        _enum(code, REASON_CODES, label)
    return values


def canonical_bytes(value: object) -> bytes:
    """Exact compact UTF-8 digest encoding; old bounded JSON guards apply."""
    json_bytes(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8", "strict")


def record_digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_reference(value: object) -> dict:
    ref = closed(value, ("candidate_reference", "source_commits", *REFERENCE_ROLES), "composition_reference")
    _fixed(ref["candidate_reference"], CANDIDATE_REFERENCE, "candidate_reference")
    commits = closed(ref["source_commits"], ("termivar", "platform"), "source_commits")
    for pin in commits.values():
        if type(pin) is not str or re.fullmatch(r"[0-9a-f]{40}", pin) is None:
            _fail("declared_source_commit")
    for role in REFERENCE_ROLES:
        item = closed(ref[role], ("bytes", "sha256"), "reference_identity")
        if integer(item["bytes"], "reference_bytes", REFERENCE_LIMITS[role]) == 0:
            _fail("reference_bytes")
        sha256(item["sha256"], "reference_hash")
    return copy.deepcopy(ref)


def common(schema: str, reference: dict) -> dict:
    _enum(schema, (LEDGER_SCHEMA, QUEUE_SCHEMA, CONFLICTS_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA), "schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "composition_reference": validate_reference(reference), **{name: False for name in FALSE_FLAGS}}


def _common(value: dict, schema: str) -> dict:
    ref = validate_reference(value["composition_reference"])
    for field, expected in common(schema, ref).items():
        _fixed(value[field], expected, "common_" + field)
    return ref


def source_key_for(subject: dict, reference: dict) -> str:
    """Local source-artifact identity; neither package identity nor provenance."""
    payload = {"schema_version": SOURCE_BINDING_SCHEMA,
               "source_artifact_sha256": subject["source_artifact_sha256"],
               "source_json_pointer": subject["source_json_pointer"],
               "source_record_sha256": subject["source_record_sha256"],
               "ledger_sha256": reference["dependencies"]["sha256"],
               "license_record_pointer": subject["license_record_pointer"],
               "license_record_sha256": subject["license_record_sha256"]}
    return SOURCE_KEY_PREFIX + record_digest(payload)


def validate_scope(value: object) -> dict:
    json_bytes(value, maximum=MAX_SCOPE_BYTES)
    root = closed(value, ("schema_version", "mode", "composition_reference", "composition_inputs",
                          "evidence_sources", "binding_requests", "review_constraints"), "scope")
    _fixed(root["schema_version"], SCOPE_SCHEMA, "scope_schema")
    _fixed(root["mode"], "demo", "scope_mode")
    validate_reference(root["composition_reference"])
    paths = closed(root["composition_inputs"], REFERENCE_ROLES, "composition_inputs")
    for path in paths.values():
        relative_path(path, "composition_path")
    _unique(list(paths.values()), "composition_paths")
    sources = _array(root["evidence_sources"], MAX_EVIDENCE_SOURCES, "evidence_sources")
    evidence_ids = []
    for row in sources:
        closed(row, ("evidence_id", "kind", "root_id", "path", "expected_sha256"), "source_selection")
        evidence_ids.append(identifier(row["evidence_id"], "evidence_id"))
        _enum(row["kind"], EVIDENCE_KINDS, "evidence_kind")
        sha256(row["expected_sha256"], "evidence_expected_hash", nullable=True)
        if row["kind"] == "missing_evidence":
            for field in ("root_id", "path", "expected_sha256"):
                _fixed(row[field], None, "missing_evidence_selection")
        else:
            _enum(row["root_id"], ("termivar", "platform"), "evidence_root")
            relative_path(row["path"], "evidence_path")
    _unique(evidence_ids, "evidence_ids")
    requests = _array(root["binding_requests"], MAX_BINDING_REQUESTS, "binding_requests")
    request_ids = []
    for row in requests:
        closed(row, ("request_id", "evidence_id", "source_license_id", "subject_type",
                     "subject_id", "source_record_sha256"), "binding_request")
        request_ids.append(identifier(row["request_id"], "request_id"))
        identifier(row["evidence_id"], "request_evidence_id")
        if row["evidence_id"] not in evidence_ids:
            _fail("request_evidence_reference")
        _license_id(row["source_license_id"], "request_source_license_id")
        _enum(row["subject_type"], ("component", "dependency"), "request_subject_type")
        identifier(row["subject_id"], "request_subject_id")
        sha256(row["source_record_sha256"], "request_record_hash")
    _unique(request_ids, "request_ids")
    limits = closed(root["review_constraints"], ("max_records", "max_evidence_sources", "max_evidence_file_bytes",
                                               "max_total_evidence_bytes"), "review_constraints")
    for field, fixed in (("max_records", MAX_RECORDS), ("max_evidence_sources", MAX_EVIDENCE_SOURCES),
                         ("max_evidence_file_bytes", MAX_EVIDENCE_FILE_BYTES),
                         ("max_total_evidence_bytes", MAX_TOTAL_EVIDENCE_BYTES)):
        _fixed(limits[field], fixed, "review_limit")
    return copy.deepcopy(root)


def validate_subject(value: object, reference: dict, index: int) -> dict:
    row = closed(value, SUBJECT_FIELDS, "source_subject")
    _fixed(row["source_license_id"], f"L{index + 1:04d}", "source_license_order")
    _enum(row["subject_type"], ("component", "dependency"), "subject_type")
    identifier(row["subject_id"], "subject_id")
    artifact = _enum(row["source_artifact"], ("inventory", "dependencies"), "source_artifact")
    _fixed(row["source_artifact_sha256"], reference[artifact]["sha256"], "source_artifact_hash")
    sha256(row["source_record_sha256"], "source_record_hash")
    sha256(row["license_record_sha256"], "license_record_hash")
    prefix = "/components/" if row["subject_type"] == "component" else "/dependencies/"
    pointer = text(row["source_json_pointer"], "source_json_pointer", 64)
    if re.fullmatch(re.escape(prefix) + r"(?:0|[1-9][0-9]{0,3})", pointer) is None:
        _fail("source_pointer")
    primary_index = int(pointer.rsplit("/", 1)[1])
    if primary_index >= (64 if row["subject_type"] == "component" else MAX_RECORDS):
        _fail("source_pointer_limit")
    _fixed(artifact, "inventory" if row["subject_type"] == "component" else "dependencies", "source_artifact")
    _fixed(row["license_record_pointer"], f"/license_evidence/{index}", "license_pointer")
    _enum(row["ecosystem"], ("first_party_source", "rust", "python"), "ecosystem")
    name = text(row["name"], "subject_name", 128)
    name_pattern = r"[A-Za-z0-9_][A-Za-z0-9_-]*" if row["ecosystem"] == "rust" else r"[A-Za-z0-9][A-Za-z0-9._-]*"
    if re.fullmatch(name_pattern, name) is None:
        _fail("subject_name")
    text(row["version"], "subject_version", 128, nullable=True)
    _enum(row["source_type"], ("source_repository", "registry", "git", "workspace", "declared_index", "unknown"), "source_type")
    if row["manifest_id"] is not None:
        identifier(row["manifest_id"], "manifest_id")
    _file_ref(row["manifest_file_ref"], "manifest_file_ref")
    _enum(row["product_scope"], PRODUCT_SCOPES, "product_scope")
    if row["subject_type"] == "component":
        _fixed(row["ecosystem"], "first_party_source", "component_ecosystem")
        _fixed(row["source_type"], "source_repository", "component_source_type")
        _fixed(row["product_scope"], "proposed_source_component", "component_product_scope")
        _fixed(row["name"], row["subject_id"], "component_name")
        _fixed(row["manifest_id"], None, "component_manifest_id")
    elif (row["ecosystem"] == "first_party_source" or row["source_type"] == "source_repository"
          or row["product_scope"] == "proposed_source_component" or row["manifest_id"] is None):
        _fail("dependency_subject_scope")
    if row["base_declared_license"] is not None:
        _labels([row["base_declared_license"]], "base_declared_license")
    _enum(row["base_evidence_level"], BASE_EVIDENCE_LEVELS, "base_evidence_level")
    _file_refs(row["base_source_file_refs"], "base_source_file_refs")
    _fixed(row["base_human_review_required"], True, "base_human_review_required")
    if row["base_evidence_level"] == "not_available" and row["base_declared_license"] is not None:
        _fail("base_unknown_license")
    if row["base_evidence_level"] in BASE_EVIDENCE_LEVELS[:3] and row["base_declared_license"] is None:
        _fail("base_license_declaration")
    _fixed(row["source_key"], source_key_for(row, reference), "source_key")
    return copy.deepcopy(row)


def _validate_source(row: object) -> dict:
    row = closed(row, SOURCE_FIELDS, "evidence_source")
    identifier(row["evidence_id"], "evidence_id")
    _enum(row["kind"], EVIDENCE_KINDS, "evidence_kind")
    if type(row["file_present"]) is not bool:
        _fail("file_present")
    sha256(row["expected_sha256"], "evidence_expected_hash", nullable=True)
    _enum(row["integrity_status"], ("expected_hash_matched", "expected_hash_mismatch", "no_expected_hash", "not_read"), "integrity_status")
    _enum(row["format_status"], ("license_header_observed", "metadata_declaration_observed", "uninterpreted_text", "missing_file"), "format_status")
    _labels(row["observed_license_labels"], "source_license_labels")
    _file_refs(row["baseline_file_refs"], "baseline_file_refs")
    _fixed(row["source_verified"], False, "source_verified")
    if row["kind"] == "missing_evidence":
        _fixed(row["expected_sha256"], None, "missing_kind_expected_hash")
    if not row["file_present"]:
        _fixed(row["bytes"], None, "missing_file_bytes")
        _fixed(row["sha256"], None, "missing_file_hash")
        _fixed(row["integrity_status"], "not_read", "missing_file_integrity")
        _fixed(row["format_status"], "missing_file", "missing_file_format")
        _fixed(row["observed_license_labels"], [], "missing_file_labels")
        _fixed(row["baseline_file_refs"], [], "missing_file_refs")
    else:
        if row["kind"] == "missing_evidence":
            _fail("missing_kind_present")
        if integer(row["bytes"], "evidence_bytes", MAX_EVIDENCE_FILE_BYTES) == 0:
            _fail("evidence_bytes")
        sha256(row["sha256"], "evidence_hash")
        expected_status = ("no_expected_hash" if row["expected_sha256"] is None else
                           "expected_hash_matched" if row["sha256"] == row["expected_sha256"]
                           else "expected_hash_mismatch")
        _fixed(row["integrity_status"], expected_status, "evidence_integrity")
        if row["format_status"] == "missing_file":
            _fail("present_file_format")
        interpreted = row["format_status"] in ("license_header_observed", "metadata_declaration_observed")
        if interpreted != bool(row["observed_license_labels"]):
            _fail("source_label_interpretation")
    return row


def validate_ledger(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "source_subjects", "evidence_sources", "bindings", "records", "counts"), "ledger")
    reference = _common(root, LEDGER_SCHEMA)
    subjects = _array(root["source_subjects"], MAX_RECORDS, "source_subjects", 1)
    for index, subject in enumerate(subjects):
        validate_subject(subject, reference, index)
    subject_by_key = {row["source_key"]: row for row in subjects}
    if len(subject_by_key) != len(subjects):
        _fail("duplicate_source_key")
    _unique([(row["subject_type"], row["subject_id"]) for row in subjects], "source_subject_ids")
    _unique([(row["source_artifact"], row["source_json_pointer"]) for row in subjects], "source_pointers")
    sources = _array(root["evidence_sources"], MAX_EVIDENCE_SOURCES, "evidence_sources")
    for source in sources:
        _validate_source(source)
    source_by_id = {row["evidence_id"]: row for row in sources}
    if len(source_by_id) != len(sources):
        _fail("duplicate_evidence_id")
    # Identical selected content may retain multiple explicit evidence IDs.
    unique_files = {(row["sha256"], row["bytes"]) for row in sources if row["file_present"]}
    if sum(size for _digest, size in unique_files) > MAX_TOTAL_EVIDENCE_BYTES:
        _fail("evidence_total_bytes")
    bindings = _array(root["bindings"], MAX_BINDING_REQUESTS, "bindings")
    binding_by_request = {}
    for row in bindings:
        closed(row, BINDING_FIELDS, "binding")
        request_id = identifier(row["request_id"], "request_id")
        if request_id in binding_by_request:
            _fail("duplicate_request_id")
        _source_key(row["source_key"], "binding_source_key")
        identifier(row["evidence_id"], "binding_evidence_id")
        if row["source_key"] not in subject_by_key or row["evidence_id"] not in source_by_id:
            _fail("binding_reference")
        _enum(row["status"], BINDING_STATUSES, "binding_status")
        _codes(row["reason_codes"], "binding_reasons")
        _file_ref(row["matched_source_file_ref"], "matched_source_file_ref", nullable=True)
        _labels(row["observed_license_labels"], "binding_license_labels")
        source = source_by_id[row["evidence_id"]]
        subject = subject_by_key[row["source_key"]]
        _fixed(row["observed_license_labels"], source["observed_license_labels"], "binding_observed_labels")
        if row["matched_source_file_ref"] is not None and (
                row["matched_source_file_ref"] not in source["baseline_file_refs"]
                or row["matched_source_file_ref"] not in subject["base_source_file_refs"]):
            _fail("binding_file_relationship")
        if row["status"] == "binding_confirmed_within_source":
            if (not source["file_present"] or source["integrity_status"] == "expected_hash_mismatch"
                    or source["format_status"] not in ("license_header_observed", "metadata_declaration_observed")
                    or source["kind"] == "unverified_external_evidence" or row["matched_source_file_ref"] is None
                    or source["kind"] == "first_party_license_file" and subject["subject_type"] != "component"
                    or source["kind"] == "dependency_license_file" and subject["subject_type"] != "dependency"):
                _fail("confirmed_binding_conditions")
            expected_format = ("license_header_observed" if source["kind"] in (
                "first_party_license_file", "dependency_license_file") else "metadata_declaration_observed")
            _fixed(source["format_status"], expected_format, "confirmed_kind_format")
            if (subject["subject_type"] == "dependency" and (
                    source["kind"] in ("package_metadata", "source_manifest_declaration")
                    or source["kind"] == "dependency_license_file"
                    and row["matched_source_file_ref"] == subject["manifest_file_ref"])):
                _fail("declaring_manifest_is_not_dependency_license_proof")
        binding_by_request[request_id] = row
    records = _array(root["records"], MAX_RECORDS, "records", 1)
    if len(records) != len(subjects):
        _fail("source_record_projection_count")
    status_counts = Counter()
    for subject, row in zip(subjects, records):
        closed(row, RECORD_FIELDS, "record")
        _fixed(row["source_key"], subject["source_key"], "record_source_order")
        _refs(row["evidence_refs"], MAX_EVIDENCE_SOURCES, "record_evidence_refs")
        _refs(row["request_refs"], MAX_BINDING_REQUESTS, "record_request_refs")
        relevant = [binding for binding in bindings if binding["source_key"] == row["source_key"]]
        _fixed(row["request_refs"], [binding["request_id"] for binding in relevant], "record_requests")
        _fixed(row["evidence_refs"], list(dict.fromkeys(binding["evidence_id"] for binding in relevant)), "record_evidence")
        _enum(row["evidence_status"], EVIDENCE_STATUSES, "record_evidence_status")
        _enum(row["review_status"], REVIEW_STATUSES, "record_review_status")
        _labels(row["observed_license_labels"], "record_license_labels", MAX_EVIDENCE_SOURCES * 8)
        observed = list(dict.fromkeys(label for binding in relevant
                                     if binding["status"] == "binding_confirmed_within_source"
                                     for label in binding["observed_license_labels"]))
        _fixed(row["observed_license_labels"], observed, "record_observed_labels")
        _codes(row["reason_codes"], "record_reasons")
        _fixed(row["human_review_required"], True, "human_review_required")
        _fixed(row["phase24_license_review_required"], True, "phase24_license_review_required")
        if not relevant:
            _fixed(row["evidence_status"], "evidence_missing", "unselected_evidence_status")
        status_counts[row["evidence_status"]] += 1
    # The shared pure projection never imports/calls this validator recursively.
    from .evidence_binding import derive_records
    _fixed(records, derive_records(subjects, bindings), "record_projection")
    counts = closed(root["counts"], LEDGER_COUNT_FIELDS, "ledger_counts")
    expected_counts = {"source_record_count": len(subjects),
                       "base_unknown_license_count": sum(row["base_declared_license"] is None or row["base_evidence_level"] == "conflicting_declarations" for row in subjects),
                       "evidence_file_count": sum(row["file_present"] for row in sources),
                       "binding_request_count": len(bindings),
                       **{field: status_counts[status] for field, status in (
                           ("evidence_present_record_count", "evidence_present"),
                           ("missing_evidence_record_count", "evidence_missing"),
                           ("ambiguous_record_count", "binding_ambiguous"),
                           ("conflicting_record_count", "binding_conflict"),
                           ("unsupported_record_count", "evidence_unsupported"),
                           ("unverified_source_record_count", "source_not_verified"))}}
    for field, actual in expected_counts.items():
        _fixed(counts[field], actual, "ledger_count")
    return copy.deepcopy(root)


def validate_conflicts(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "conflicts", "counts"), "conflicts")
    _common(root, CONFLICTS_SCHEMA)
    rows = _array(root["conflicts"], MAX_RECORDS * len(CONFLICT_CATEGORIES), "conflict_rows")
    categories = Counter()
    identities = []
    for row in rows:
        closed(row, ("category", "source_key", "evidence_refs", "request_refs", "human_review_required"), "conflict")
        _enum(row["category"], CONFLICT_CATEGORIES, "conflict_category")
        _source_key(row["source_key"], "conflict_source_key")
        _refs(row["evidence_refs"], MAX_EVIDENCE_SOURCES, "conflict_evidence_refs")
        _refs(row["request_refs"], MAX_BINDING_REQUESTS, "conflict_request_refs")
        _fixed(row["human_review_required"], True, "conflict_human_review")
        categories[row["category"]] += 1
        identities.append((row["category"], row["source_key"], tuple(row["evidence_refs"]), tuple(row["request_refs"])))
    _unique(identities, "duplicate_conflict_event")
    counts = closed(root["counts"], ("conflict_count", "by_category"), "conflict_counts")
    _fixed(counts["conflict_count"], len(rows), "conflict_count")
    grouped = _array(counts["by_category"], len(CONFLICT_CATEGORIES), "category_counts")
    seen = []
    for row in grouped:
        closed(row, ("category", "record_count"), "category_count")
        category = _enum(row["category"], CONFLICT_CATEGORIES, "conflict_category")
        seen.append(category)
        _fixed(row["record_count"], categories[category], "category_count")
        if categories[category] == 0:
            _fail("empty_category_count")
    _unique(seen, "duplicate_category_count")
    _fixed(set(seen), set(categories), "category_count_set")
    return copy.deepcopy(root)


def validate_queue(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "records", "counts"), "queue")
    _common(root, QUEUE_SCHEMA)
    rows = _array(root["records"], MAX_RECORDS, "queue_records", 1)
    groups = Counter()
    keys = []
    for row in rows:
        closed(row, ("source_key", "groups", "subject_type", "subject_id", "product_scope", "evidence_status",
                     "review_status", "next_human_action", "phase24_source_license_id", "human_review_required"), "queue_record")
        keys.append(_source_key(row["source_key"], "queue_source_key"))
        memberships = _array(row["groups"], len(QUEUE_GROUPS), "queue_groups", 1)
        for group in memberships:
            _enum(group, QUEUE_GROUPS, "queue_group")
            groups[group] += 1
        _unique(memberships, "queue_group_memberships")
        _enum(row["subject_type"], ("component", "dependency"), "queue_subject_type")
        identifier(row["subject_id"], "queue_subject_id")
        _enum(row["product_scope"], PRODUCT_SCOPES, "queue_product_scope")
        _enum(row["evidence_status"], EVIDENCE_STATUSES, "queue_evidence_status")
        _enum(row["review_status"], REVIEW_STATUSES, "queue_review_status")
        _enum(row["next_human_action"], NEXT_HUMAN_ACTIONS, "next_human_action")
        _license_id(row["phase24_source_license_id"], "queue_source_license_id")
        _fixed(row["human_review_required"], True, "queue_human_review")
    _unique(keys, "queue_source_keys")
    counts = closed(root["counts"], ("unique_source_record_count", "queue_record_count", "group_membership_count", "by_group"), "queue_counts")
    _fixed(counts["unique_source_record_count"], len(keys), "queue_unique_count")
    _fixed(counts["queue_record_count"], len(rows), "queue_record_count")
    _fixed(counts["group_membership_count"], sum(groups.values()), "queue_membership_count")
    grouped = _array(counts["by_group"], len(QUEUE_GROUPS), "group_counts")
    seen = []
    for row in grouped:
        closed(row, ("group", "record_count"), "group_count")
        group = _enum(row["group"], QUEUE_GROUPS, "queue_group")
        seen.append(group)
        _fixed(row["record_count"], groups[group], "group_count")
        if groups[group] == 0:
            _fail("empty_group_count")
    _unique(seen, "duplicate_group_count")
    _fixed(set(seen), set(groups), "group_count_set")
    return copy.deepcopy(root)


def validate_documents(ledger: object, queue: object, conflicts: object) -> None:
    """Check new metadata projections only, without reopening base/evidence files."""
    checked = validate_ledger(ledger)
    checked_queue = validate_queue(queue)
    checked_conflicts = validate_conflicts(conflicts)
    for document in (checked_queue, checked_conflicts):
        _fixed(document["composition_reference"], checked["composition_reference"], "composition_reference_relationship")
    subjects = {row["source_key"]: row for row in checked["source_subjects"]}
    record_by_key = {row["source_key"]: row for row in checked["records"]}
    for row in checked_queue["records"]:
        if row["source_key"] not in subjects:
            _fail("queue_source_reference")
        subject, record = subjects[row["source_key"]], record_by_key[row["source_key"]]
        for field in ("subject_type", "subject_id", "product_scope"):
            _fixed(row[field], subject[field], "queue_subject_relationship")
        for field in ("evidence_status", "review_status"):
            _fixed(row[field], record[field], "queue_record_relationship")
        _fixed(row["phase24_source_license_id"], subject["source_license_id"], "queue_license_relationship")
    _fixed([row["source_key"] for row in checked_queue["records"]], list(subjects), "queue_complete_ordered_projection")
    for row in checked_conflicts["conflicts"]:
        if row["source_key"] not in subjects:
            _fail("conflict_source_reference")
        record = record_by_key[row["source_key"]]
        if (not set(row["evidence_refs"]) <= set(record["evidence_refs"])
                or not set(row["request_refs"]) <= set(record["request_refs"])):
            _fail("conflict_reference")
    # These builders are pure and only use validate_ledger; never this function.
    from .conflict_analysis import build_conflicts
    from .review_queue import build_queue
    _fixed(checked_conflicts, build_conflicts(checked), "conflict_projection")
    _fixed(checked_queue, build_queue(checked, checked_conflicts), "queue_projection")
