"""Closed Phase30 metadata contracts. No source I/O, resolver or compiler."""
from __future__ import annotations

import copy
import re

from commercial_composition.composition_contracts import (
    InputError, closed, text, integer, identifier, relative_path, sha256,
    parse_json as _parse_json, json_bytes as _json_bytes,
)
from commercial_license_review.evidence_contracts import record_digest
from commercial_rust_source_graph import source_graph_contracts as previous

SCOPE_SCHEMA = "termivar-offline-rust-module-candidate-scope/v1"
LEDGER_SCHEMA = "termivar-offline-rust-module-candidate-evidence/v1"
TRIAGE_SCHEMA = "termivar-offline-module-candidate-triage/v1"
COVERAGE_SCHEMA = "termivar-offline-module-candidate-coverage/v1"
MANIFEST_SCHEMA = "termivar-offline-module-candidate-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-module-candidate-inspection/v1"
CANDIDATE_REFERENCE = "DEMO-TERMIVAR-MODULE-CANDIDATES-030"
DEMO_LABEL = "DEMONSTRATION ONLY — RUST MODULE CANDIDATE EVIDENCE — NO COMPILER RESOLUTION VERIFIED"
FALSE_FLAGS = (*previous.FALSE_FLAGS, "compiler_resolution_verified")
COMMON_FIELDS = ("schema_version", "source_reference", "demo_label", "demo_only", *FALSE_FLAGS)
MAX_SCOPE_BYTES = 128 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_SUMMARY_BYTES = 256 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_CANDIDATE_BYTES = 512 * 1024
MAX_TOTAL_CANDIDATE_BYTES = 4 * 1024 * 1024
MAX_CHUNK_BYTES = 64 * 1024
MAX_EXTERNAL_REFERENCES = 95
MAX_SELECTED_REFERENCES = 32
MAX_CANDIDATES = 64
ORIGINS = ("explicit_operator_candidate", "supported_static_path_context", "context_ambiguous", "unsupported_path_context")
REFERENCE_SCHEMAS = {
    "ledger": previous.LEDGER_SCHEMA, "graph": previous.GRAPH_SCHEMA,
    "coverage": previous.COVERAGE_SCHEMA, "summary": None, "manifest": previous.MANIFEST_SCHEMA,
}
INVENTORY_SCHEMAS = {
    "inventory": "termivar-offline-composition/v1", "dependencies": "termivar-offline-dependency-license-ledger/v1",
    "constraints": "termivar-offline-release-constraints/v1", "summary": None,
    "manifest": "termivar-offline-composition-manifest/v1",
}
GROUP_SCHEMAS = {"reference_sources": REFERENCE_SCHEMAS, "inventory_sources": INVENTORY_SCHEMAS}
REVIEW_FIELDS = ("selected_references", "allowed_candidate_files", "candidate_policy", "inspection_constraints")
CONTEXT_FIELDS = ("phase29_source_reference", "parent_context", "source_files", "references", "conditions")
CANDIDATE_FIELDS = ("candidate_id", "root_id", "pinned_commit", "path", "origin")
ALLOW_FIELDS = ("candidate_id", "reference_id", "root_id", "pinned_commit", "path", "expected_sha256", "max_bytes", "read_kind")
FILE_FIELDS = ("file_id", "root_id", "pinned_commit", "path", "candidate_ids", "expected_sha256", "max_bytes", "read_kind",
               "read_status", "source_file_presence", "regular_file", "observed_byte_size", "observed_sha256")
CANDIDATE_POLICY = {"automatic_path_generation": False, "automatic_discovery": False,
                    "condition_evaluation": "not_performed", "alternatives_exhaustive": False,
                    "compiler_resolution_verified": False}
INSPECTION_CONSTRAINTS = {
    "max_selected_references": 32, "max_candidates_per_reference": 2, "max_candidate_files": 64,
    "max_candidate_bytes": MAX_CANDIDATE_BYTES, "max_total_candidate_bytes": MAX_TOTAL_CANDIDATE_BYTES,
    "chunk_bytes": MAX_CHUNK_BYTES, "metadata_total_bytes": MAX_METADATA_BYTES,
}


def fail(code: str) -> None:
    raise InputError("module_candidate_invalid_" + code)


def fixed(value: object, expected: object, code: str) -> None:
    # Canonical JSON comparison distinguishes bool from integer even in nested rows.
    if type(value) is not type(expected) or json_bytes(value) != json_bytes(expected):
        fail(code)


def array(value: object, maximum: int, code: str, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        fail(code)
    return value


def unique(values: list, code: str) -> None:
    if len(set(values)) != len(values):
        fail(code)


def pin(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        fail("pin")
    return value


def safe_path(value: object) -> str:
    result = relative_path(value, "path")
    # Windows normalisation must not silently redirect a repository-relative path.
    for part in result.split("/"):
        if part.endswith((".", " ")) or part.split(".", 1)[0].upper() in {
            "CON", "PRN", "AUX", "NUL", *("COM" + str(n) for n in range(1, 10)),
            *("LPT" + str(n) for n in range(1, 10)),
        }:
            fail("path_component")
    return result


def parse_json(raw: bytes, maximum: int = MAX_JSON_BYTES) -> object:
    integer(maximum, "json_limit", MAX_JSON_BYTES)
    return _parse_json(raw, maximum=maximum)


def json_bytes(value: object, maximum: int = MAX_JSON_BYTES) -> bytes:
    integer(maximum, "json_limit", MAX_JSON_BYTES)
    return _json_bytes(value, maximum=maximum)


def group_descriptors(group: dict) -> dict:
    return {role: {key: row[key] for key in ("schema_version", "bytes", "sha256")} for role, row in group.items()}


def validate_group(value: object, name: str, *, paths: bool) -> dict:
    schemas = GROUP_SCHEMAS[name]
    group = closed(value, schemas, "source_group")
    for role, schema in schemas.items():
        row = closed(group[role], ("path", "schema_version", "bytes", "sha256") if paths else ("schema_version", "bytes", "sha256"), "source_descriptor")
        fixed(row["schema_version"], schema, "source_schema")
        if paths:
            safe_path(row["path"])
        maximum = MAX_MANIFEST_BYTES if role == "manifest" else MAX_SUMMARY_BYTES if role == "summary" else 1024 * 1024 if name == "reference_sources" else MAX_JSON_BYTES
        if integer(row["bytes"], "source_bytes", maximum) == 0:
            fail("empty_artifact")
        sha256(row["sha256"], "source_hash")
    return copy.deepcopy(group)


def validate_reference(value: object, *, full: bool = True) -> dict:
    fields = ("candidate_reference", "composition_candidate_reference", "source_commits")
    ref = closed(value, (*fields, *GROUP_SCHEMAS) if full else fields, "source_reference")
    fixed(ref["candidate_reference"], CANDIDATE_REFERENCE, "candidate_reference")
    fixed(ref["composition_candidate_reference"], previous.COMPOSITION_CANDIDATE_REFERENCE, "composition_reference")
    pins = closed(ref["source_commits"], ("termivar", "platform"), "source_commits")
    for value in pins.values():
        pin(value)
    if full:
        for group in GROUP_SCHEMAS:
            validate_group(ref[group], group, paths=False)
        if sum(r["bytes"] for name in GROUP_SCHEMAS for r in ref[name].values()) > MAX_METADATA_BYTES:
            fail("metadata_total")
    return copy.deepcopy(ref)


def common(schema: str, reference: dict) -> dict:
    if schema not in (LEDGER_SCHEMA, TRIAGE_SCHEMA, COVERAGE_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
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


def file_identifier(row: dict) -> str:
    return "candidate-file-" + record_digest({key: row[key] for key in ("root_id", "pinned_commit", "path")})


def validate_source_context(value: object, reference: dict) -> dict:
    ctx = closed(value, CONTEXT_FIELDS, "source_context")
    previous.validate_reference(ctx["phase29_source_reference"])
    fixed(ctx["phase29_source_reference"]["source_commits"], reference["source_commits"], "parent_source_pins")
    fixed(ctx["phase29_source_reference"]["composition_sources"], reference["inventory_sources"], "parent_inventory_sources")
    previous.validate_parent_context(ctx["parent_context"])
    array(ctx["parent_context"]["phase24_context"]["files"], 512, "inventory_file_limit")
    previous.validate_source_files(ctx["source_files"], ctx["parent_context"])
    previous.validate_references(ctx["references"], ctx["source_files"], ctx["conditions"])
    external = [r for r in ctx["references"] if r["reference_kind"] == "external_module_declaration"]
    array(external, MAX_EXTERNAL_REFERENCES, "external_reference_limit")
    required = {cid for r in ctx["references"] for cid in r["condition_ids"]}
    if {r["condition_id"] for r in ctx["conditions"]} != required:
        fail("unrelated_or_missing_conditions")
    roots = {r["root_id"]: r["pinned_commit"] for r in ctx["parent_context"]["phase24_context"]["source_roots"]}
    fixed(roots, reference["source_commits"], "inventory_pins")
    return copy.deepcopy(ctx)


def validate_review_scope(value: object, pins: dict, context: dict | None = None) -> dict:
    review = closed(value, REVIEW_FIELDS, "review_scope")
    fixed(review["candidate_policy"], CANDIDATE_POLICY, "candidate_policy")
    fixed(review["inspection_constraints"], INSPECTION_CONSTRAINTS, "inspection_constraints")
    selections = array(review["selected_references"], MAX_SELECTED_REFERENCES, "selected_references")
    refs, candidates, pairs = [], {}, []
    source_refs = None if context is None else {r["reference_id"]: r for r in context["references"]}
    for selected in selections:
        closed(selected, ("reference", "inspection_scope", "candidates"), "selected_reference")
        r = closed(selected["reference"], previous.REFERENCE_FIELDS, "selected_reference_fields")
        # Full source-bound validation occurs before any candidate filesystem access.
        identifier(r["reference_id"], "reference_id")
        fixed(r["reference_kind"], "external_module_declaration", "external_reference_required")
        if source_refs is not None:
            if r["reference_id"] not in source_refs:
                fail("unknown_reference")
            fixed(r, source_refs[r["reference_id"]], "selected_reference_source_binding")
        refs.append(r["reference_id"])
        fixed(selected["inspection_scope"], "explicit_candidates_only_non_exhaustive", "inspection_scope")
        for candidate in array(selected["candidates"], 2, "reference_candidates"):
            closed(candidate, CANDIDATE_FIELDS, "candidate_fields")
            cid = identifier(candidate["candidate_id"], "candidate_id")
            if cid in candidates:
                fail("duplicate_candidate")
            fixed(candidate["root_id"], "termivar", "candidate_root")
            fixed(candidate["pinned_commit"], pins["termivar"], "candidate_pin")
            safe_path(candidate["path"])
            if candidate["origin"] not in ORIGINS or type(candidate["origin"]) is not str:
                fail("candidate_origin")
            if context is not None:
                parent = next(row for row in context["source_files"] if row["source_file_reference"] == r["source_file_reference"])
                fixed(candidate["root_id"], parent["root_id"], "parent_root")
                fixed(candidate["pinned_commit"], parent["pinned_commit"], "parent_pin")
            candidates[cid] = (r["reference_id"], candidate)
            pairs.append((r["reference_id"], candidate["root_id"], candidate["pinned_commit"], candidate["path"].casefold()))
    unique(refs, "duplicate_selected_reference")
    unique(pairs, "duplicate_reference_candidate_path")
    if len(candidates) > MAX_CANDIDATES:
        fail("candidate_limit")
    allowed = array(review["allowed_candidate_files"], MAX_CANDIDATES, "allowlist")
    logical = {}
    for row in allowed:
        closed(row, ALLOW_FIELDS, "allowlist_fields")
        cid = identifier(row["candidate_id"], "allowlist_candidate")
        if cid not in candidates:
            fail("allowlist_unknown_candidate")
        refid, candidate = candidates[cid]
        fixed(row["reference_id"], refid, "allowlist_reference")
        for key in ("root_id", "pinned_commit", "path"):
            fixed(row[key], candidate[key], "allowlist_candidate_binding")
        sha256(row["expected_sha256"], "expected_sha256", nullable=True)
        if integer(row["max_bytes"], "max_candidate_bytes", MAX_CANDIDATE_BYTES) == 0:
            fail("empty_candidate_budget")
        fixed(row["read_kind"], "hash_only", "read_kind")
        key = (row["root_id"], row["pinned_commit"], row["path"])
        identity = (row["expected_sha256"], row["max_bytes"], row["read_kind"])
        if key in logical and logical[key] != identity:
            fail("conflicting_file_allowlist")
        logical[key] = identity
    unique([r["candidate_id"] for r in allowed], "duplicate_allowlist_candidate")
    # Different spellings of a logical Windows path may not bypass unique reads.
    unique([(a, b, c.casefold()) for a, b, c in logical], "casefold_file_alias")
    return copy.deepcopy(review)


def validate_file_observations(value: object, review: dict, pins: dict) -> list:
    rows = array(value, MAX_CANDIDATES, "file_observations")
    groups = {}
    for allowed in review["allowed_candidate_files"]:
        key = tuple(allowed[k] for k in ("root_id", "pinned_commit", "path"))
        groups.setdefault(key, []).append(allowed)
    expected_keys = sorted(groups)
    actual_keys, total = [], 0
    for row in rows:
        closed(row, FILE_FIELDS, "observed_file_fields")
        fixed(row["file_id"], file_identifier(row), "file_id")
        key = tuple(row[k] for k in ("root_id", "pinned_commit", "path"))
        if key not in groups:
            fail("unexpected_file_observation")
        actual_keys.append(key)
        group = groups[key]
        first = group[0]
        fixed(row["candidate_ids"], sorted(r["candidate_id"] for r in group), "file_candidate_bindings")
        for field in ("expected_sha256", "max_bytes", "read_kind"):
            fixed(row[field], first[field], "file_allowlist_metadata")
        if row["read_status"] == "present_and_hashed":
            fixed(row["source_file_presence"], "present", "file_presence")
            fixed(row["regular_file"], True, "regular_file")
            total += integer(row["observed_byte_size"], "observed_bytes", row["max_bytes"])
            sha256(row["observed_sha256"], "observed_sha256")
            if row["expected_sha256"] is not None:
                fixed(row["observed_sha256"], row["expected_sha256"], "expected_hash_mismatch")
        elif row["read_status"] == "declared_file_missing":
            fixed(row["source_file_presence"], "missing", "file_presence")
            for field in ("regular_file", "observed_byte_size", "observed_sha256"):
                fixed(row[field], None, "missing_file_metadata")
        else:
            fail("file_read_status")
    fixed([list(key) for key in actual_keys], [list(key) for key in expected_keys], "unique_file_observation_set")
    if total > MAX_TOTAL_CANDIDATE_BYTES:
        fail("total_candidate_byte_budget")
    return copy.deepcopy(rows)


def validate_documents(evidence: object, triage: object, coverage: object) -> None:
    # Pure metadata re-derivation; these modules never import the reader/adapter/CLI.
    from .candidate_binding import rebuild_evidence
    from .candidate_triage import build_triage
    from .inventory_projection import build_projection

    e = validate_common(evidence, LEDGER_SCHEMA, ("source_context", "review_scope", "candidate_files", "candidates", "counts", "limitations"))
    validate_source_context(e["source_context"], e["source_reference"])
    validate_review_scope(e["review_scope"], e["source_reference"]["source_commits"], e["source_context"])
    validate_file_observations(e["candidate_files"], e["review_scope"], e["source_reference"]["source_commits"])
    fixed(e, rebuild_evidence(e), "evidence_projection")
    fixed(triage, build_triage(e), "triage_projection")
    fixed(coverage, build_projection(e, triage), "coverage_projection")
