"""Strict Phase31 metadata. No I/O, source discovery or Rust evaluation."""
from __future__ import annotations

import copy
import re

from commercial_composition.composition_contracts import (
    InputError, closed, integer, identifier, sha256,
    parse_json as _parse_json, json_bytes as _json_bytes,
)
from commercial_composition.artifact_manifest import identity
from commercial_license_review.evidence_contracts import record_digest
from commercial_module_candidates import candidate_contracts as previous

SCOPE_SCHEMA = "termivar-offline-candidate-revalidation-scope/v1"
LEDGER_SCHEMA = "termivar-offline-candidate-revalidation/v1"
REUSE_SCHEMA = "termivar-offline-candidate-evidence-reuse/v1"
MANIFEST_SCHEMA = "termivar-offline-candidate-revalidation-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-candidate-revalidation-inspection/v1"
REVIEW_REFERENCE = "DEMO-TERMIVAR-CANDIDATE-REVALIDATION-031"
DEMO_LABEL = "DEMONSTRATION ONLY — CANDIDATE EVIDENCE REVALIDATION — NO COMPILER RESOLUTION VERIFIED"
FALSE_FLAGS = (*previous.FALSE_FLAGS, "reference_context_revalidated")
COMMON_FIELDS = ("schema_version", "source_reference", "demo_label", "demo_only", *FALSE_FLAGS)
MAX_SCOPE_BYTES = 128 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_SUMMARY_BYTES = 256 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_CANDIDATE_BYTES = 512 * 1024
MAX_TOTAL_CANDIDATE_BYTES = 4 * 1024 * 1024
MAX_CHUNK_BYTES = 64 * 1024
MAX_FILES = 64
BASELINE_SCHEMAS = {
    "evidence": previous.LEDGER_SCHEMA, "triage": previous.TRIAGE_SCHEMA,
    "coverage": previous.COVERAGE_SCHEMA, "summary": None, "manifest": previous.MANIFEST_SCHEMA,
}
REVIEW_FIELDS = ("selected_files", "read_constraints", "reuse_policy")
SELECTED_FIELDS = ("file_id", "candidate_ids", "root_id", "pinned_commit", "path", "max_bytes", "current_expected_sha256", "read_kind")
CURRENT_FIELDS = ("observation_id", "file_id", "root_id", "pinned_commit", "path", "candidate_ids",
                  "baseline_sha256", "current_expected_sha256", "read_status", "source_file_presence",
                  "regular_file", "current_observed_byte_size", "current_observed_sha256", "read_stability", "physical_identity")
READ_CONSTRAINTS = {"candidate_file_max_bytes": MAX_CANDIDATE_BYTES,
                    "candidate_total_max_bytes": MAX_TOTAL_CANDIDATE_BYTES, "chunk_max_bytes": MAX_CHUNK_BYTES,
                    "metadata_total_max_bytes": MAX_METADATA_BYTES, "allowlist_expansion": False}
REUSE_POLICY = {"equal_bytes": "fresh_candidate_byte_metadata_only", "equal_absence": "fresh_absence_metadata_only",
                "otherwise": "block_without_historical_fallback", "reference_context_revalidated": False,
                "ttl": "not_defined"}


def fail(code: str) -> None:
    raise InputError("candidate_revalidation_invalid_" + code)


def parse_json(raw: bytes, maximum: int = MAX_JSON_BYTES) -> object:
    integer(maximum, "json_limit", MAX_JSON_BYTES)
    return _parse_json(raw, maximum=maximum)


def json_bytes(value: object, maximum: int = MAX_JSON_BYTES) -> bytes:
    integer(maximum, "json_limit", MAX_JSON_BYTES)
    return _json_bytes(value, maximum=maximum)


def fixed(value: object, expected: object, label: str) -> None:
    if type(value) is not type(expected) or json_bytes(value) != json_bytes(expected):
        fail(label)


def array(value: object, maximum: int, label: str) -> list:
    if type(value) is not list or len(value) > maximum:
        fail(label)
    return value


def unique(values: list, label: str) -> None:
    if len(set(values)) != len(values):
        fail(label)


def pin(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        fail("pin")
    return value


safe_path = previous.safe_path


def descriptors(group: dict) -> dict:
    return {role: {key: row[key] for key in ("schema_version", "bytes", "sha256")} for role, row in group.items()}


def validate_baseline_sources(value: object, *, paths: bool) -> dict:
    rows = closed(value, BASELINE_SCHEMAS, "baseline_sources")
    for role, schema in BASELINE_SCHEMAS.items():
        row = closed(rows[role], ("path", "schema_version", "bytes", "sha256") if paths else ("schema_version", "bytes", "sha256"), "baseline_descriptor")
        fixed(row["schema_version"], schema, "baseline_schema")
        if paths:
            safe_path(row["path"])
        maximum = MAX_MANIFEST_BYTES if role == "manifest" else MAX_SUMMARY_BYTES if role == "summary" else MAX_JSON_BYTES
        if integer(row["bytes"], "baseline_bytes", maximum) == 0:
            fail("empty_baseline")
        sha256(row["sha256"], "baseline_sha256")
    return copy.deepcopy(rows)


def validate_package(value: object, *, paths: bool) -> dict:
    row = closed(value, ("path", "bytes", "sha256") if paths else ("bytes", "sha256"), "source_package")
    if paths:
        safe_path(row["path"])
        if not row["path"].endswith(".zip"):
            fail("source_package_kind")
    if integer(row["bytes"], "package_bytes", MAX_PACKAGE_BYTES) == 0:
        fail("empty_source_package")
    sha256(row["sha256"], "package_sha256")
    return copy.deepcopy(row)


def validate_reference(value: object, *, full: bool = True) -> dict:
    fields = ("review_reference", "phase30_candidate_reference", "source_commits")
    ref = closed(value, (*fields, "baseline_sources", "source_package") if full else fields, "source_reference")
    fixed(ref["review_reference"], REVIEW_REFERENCE, "review_reference")
    fixed(ref["phase30_candidate_reference"], previous.CANDIDATE_REFERENCE, "phase30_reference")
    pins = closed(ref["source_commits"], ("termivar", "platform"), "source_commits")
    for value in pins.values():
        pin(value)
    if full:
        validate_baseline_sources(ref["baseline_sources"], paths=False)
        validate_package(ref["source_package"], paths=False)
        if sum(r["bytes"] for r in ref["baseline_sources"].values()) + ref["source_package"]["bytes"] > MAX_METADATA_BYTES:
            fail("metadata_budget")
    return copy.deepcopy(ref)


def common(schema: str, reference: dict) -> dict:
    if schema not in (LEDGER_SCHEMA, REUSE_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "source_reference": validate_reference(reference), "demo_label": DEMO_LABEL,
            "demo_only": True, **{name: False for name in FALSE_FLAGS}}


def validate_common(value: object, schema: str, fields: tuple) -> dict:
    row = closed(value, (*COMMON_FIELDS, *fields), "document_fields")
    fixed(row["schema_version"], schema, "schema")
    validate_reference(row["source_reference"])
    fixed(row["demo_label"], DEMO_LABEL, "demo_label")
    fixed(row["demo_only"], True, "demo_only")
    for flag in FALSE_FLAGS:
        fixed(row[flag], False, "trust_flag")
    return row


def baseline_payloads(evidence: dict) -> tuple[dict, dict, dict]:
    """Rebuild canonical Phase30 producer bytes, never reopen a parent file."""
    from commercial_module_candidates.candidate_triage import build_triage
    from commercial_module_candidates.inventory_projection import build_projection
    from commercial_module_candidates.output_renderer import render_summary
    from commercial_module_candidates.artifact_manifest import manifest_data
    triage = build_triage(evidence)
    coverage = build_projection(evidence, triage)
    previous.validate_documents(evidence, triage, coverage)
    payloads = {"module-candidate-evidence.json": previous.json_bytes(evidence),
                "candidate-triage.json": previous.json_bytes(triage),
                "candidate-coverage.json": previous.json_bytes(coverage),
                "candidate-summary.md": render_summary(evidence, triage, coverage)}
    raw = {"evidence": payloads["module-candidate-evidence.json"], "triage": payloads["candidate-triage.json"],
           "coverage": payloads["candidate-coverage.json"], "summary": payloads["candidate-summary.md"],
           "manifest": previous.json_bytes(manifest_data(evidence, triage, coverage, payloads), maximum=MAX_MANIFEST_BYTES)}
    return raw, triage, coverage


def validate_baseline_evidence(value: object, reference: dict) -> dict:
    if type(value) is not dict:
        fail("baseline_evidence")
    raw, _, _ = baseline_payloads(value)
    fixed(value["source_reference"]["candidate_reference"], reference["phase30_candidate_reference"], "baseline_candidate_reference")
    fixed(value["source_reference"]["source_commits"], reference["source_commits"], "baseline_source_pins")
    for role, body in raw.items():
        fixed({"schema_version": BASELINE_SCHEMAS[role], **identity(body)}, reference["baseline_sources"][role], "canonical_baseline_identity")
    return copy.deepcopy(value)


def validate_review_scope(value: object, evidence: dict) -> dict:
    review = closed(value, REVIEW_FIELDS, "review_scope")
    fixed(review["read_constraints"], READ_CONSTRAINTS, "read_constraints")
    fixed(review["reuse_policy"], REUSE_POLICY, "reuse_policy")
    selected = array(review["selected_files"], MAX_FILES, "selected_files")
    old = {row["file_id"]: row for row in evidence["candidate_files"]}
    allowed = {row["candidate_id"]: row for row in evidence["review_scope"]["allowed_candidate_files"]}
    ids, paths = [], []
    for row in selected:
        closed(row, SELECTED_FIELDS, "selected_file_fields")
        identifier(row["file_id"], "file_id")
        baseline = old.get(row["file_id"])
        if baseline is None:
            fail("file_not_previously_allowlisted")
        ids.append(row["file_id"])
        for key in ("candidate_ids", "root_id", "pinned_commit", "path", "read_kind"):
            fixed(row[key], baseline[key], "old_file_binding")
        safe_path(row["path"])
        fixed(row["root_id"], "termivar", "source_root")
        if integer(row["max_bytes"], "max_bytes", min(MAX_CANDIDATE_BYTES, baseline["max_bytes"])) == 0:
            fail("empty_file_budget")
        sha256(row["current_expected_sha256"], "current_expected_sha256", nullable=True)
        for cid in row["candidate_ids"]:
            prior = allowed.get(cid)
            if prior is None or any(prior[k] != row[k] for k in ("root_id", "pinned_commit", "path", "read_kind")):
                fail("allowlist_expansion")
        paths.append((row["root_id"], row["pinned_commit"], row["path"].casefold()))
    unique(ids, "duplicate_file_selection")
    unique(paths, "duplicate_or_case_alias_selection")
    return copy.deepcopy(review)


def validate_scope(value: object) -> dict:
    scope = closed(value, ("schema_version", "mode", "source_reference", "baseline_sources", "source_package", *REVIEW_FIELDS), "scope_fields")
    fixed(scope["schema_version"], SCOPE_SCHEMA, "scope_schema")
    fixed(scope["mode"], "demo", "mode")
    validate_reference(scope["source_reference"], full=False)
    validate_baseline_sources(scope["baseline_sources"], paths=True)
    validate_package(scope["source_package"], paths=True)
    fixed(scope["read_constraints"], READ_CONSTRAINTS, "read_constraints")
    fixed(scope["reuse_policy"], REUSE_POLICY, "reuse_policy")
    # Complete old-allowlist binding is mandatory after reading the baseline,
    # before the first candidate filesystem query.
    array(scope["selected_files"], MAX_FILES, "selected_files")
    paths = [r["path"].casefold() for r in scope["baseline_sources"].values()] + [scope["source_package"]["path"].casefold()]
    unique(paths, "duplicate_metadata_path")
    if sum(r["bytes"] for r in scope["baseline_sources"].values()) + scope["source_package"]["bytes"] > MAX_METADATA_BYTES:
        fail("metadata_budget")
    return copy.deepcopy(scope)


def current_identifier(row: dict) -> str:
    return "current-observation-" + record_digest({key: row[key] for key in CURRENT_FIELDS if key != "observation_id"})


def validate_current_observations(value: object, review: dict, evidence: dict) -> list:
    rows = array(value, MAX_FILES, "current_observations")
    selections = {row["file_id"]: row for row in review["selected_files"]}
    historical = {row["file_id"]: row for row in evidence["candidate_files"]}
    actual_ids, total = [], 0
    for row in rows:
        closed(row, CURRENT_FIELDS, "current_observation_fields")
        selection = selections.get(row["file_id"])
        if selection is None:
            fail("unexpected_current_observation")
        actual_ids.append(row["file_id"])
        for key in ("file_id", "root_id", "pinned_commit", "path", "candidate_ids", "current_expected_sha256"):
            fixed(row[key], selection[key], "current_scope_binding")
        fixed(row["baseline_sha256"], historical[row["file_id"]]["observed_sha256"], "historical_hash_unchanged")
        fixed(row["physical_identity"], "not_exported", "physical_identity")
        if row["read_status"] == "present_and_hashed":
            fixed(row["source_file_presence"], "present", "current_presence")
            fixed(row["regular_file"], True, "current_regular_file")
            total += integer(row["current_observed_byte_size"], "current_bytes", selection["max_bytes"])
            sha256(row["current_observed_sha256"], "current_observed_sha256")
            if row["current_expected_sha256"] is not None:
                fixed(row["current_observed_sha256"], row["current_expected_sha256"], "current_expectation_mismatch")
            fixed(row["read_stability"], "stable_bounded_read", "current_stability")
        elif row["read_status"] == "declared_file_missing":
            if row["current_expected_sha256"] is not None:
                fail("current_expectation_not_verified")
            fixed(row["source_file_presence"], "missing", "current_presence")
            for key in ("regular_file", "current_observed_byte_size", "current_observed_sha256"):
                fixed(row[key], None, "missing_current_metadata")
            fixed(row["read_stability"], "safe_absence_observed", "current_stability")
        else:
            fail("current_read_status")
        fixed(row["observation_id"], current_identifier(row), "current_observation_id")
    fixed(actual_ids, sorted(selections), "complete_unique_current_observations")
    unique([r["observation_id"] for r in rows], "duplicate_current_id")
    if total > MAX_TOTAL_CANDIDATE_BYTES:
        fail("current_total_bytes")
    return copy.deepcopy(rows)


def validate_documents(ledger: object, reuse: object) -> None:
    from .observation_comparison import rebuild_ledger
    from .evidence_reuse_guard import build_reuse
    row = validate_common(ledger, LEDGER_SCHEMA, ("baseline_evidence", "review_scope", "current_observations",
                                               "historical_observations", "comparisons", "counts", "limitations"))
    validate_baseline_evidence(row["baseline_evidence"], row["source_reference"])
    validate_review_scope(row["review_scope"], row["baseline_evidence"])
    validate_current_observations(row["current_observations"], row["review_scope"], row["baseline_evidence"])
    fixed(row, rebuild_ledger(row), "ledger_projection")
    fixed(reuse, build_reuse(row), "reuse_projection")
