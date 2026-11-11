"""Closed, bounded Rust-reference metadata; never reads or lexes source bodies.

The inspector validates recorded projections only. Hashes and local lexical
observations are not compiler, source-authenticity, ownership or release proof.
"""
from __future__ import annotations

import copy
import re
from collections import Counter

from commercial_composition.composition_contracts import (
    InputError, closed, text, integer, identifier, relative_path, sha256,
    parse_json as _parse_json, json_bytes as _json_bytes,
)
from commercial_license_review.evidence_contracts import record_digest
from commercial_entrypoint_coverage.coverage_contracts import (
    FALSE_FLAGS as _PREVIOUS_FALSE_FLAGS, validate_context as _validate_phase24_context,
)

SCOPE_SCHEMA = "termivar-offline-rust-source-graph-scope/v1"
LEDGER_SCHEMA = "termivar-offline-rust-source-reference-ledger/v1"
GRAPH_SCHEMA = "termivar-offline-rust-source-evidence-graph/v1"
COVERAGE_SCHEMA = "termivar-offline-module-coverage-projection/v1"
MANIFEST_SCHEMA = "termivar-offline-rust-source-graph-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-rust-source-graph-inspection/v1"
CANDIDATE_REFERENCE = "DEMO-TERMIVAR-RUST-SOURCE-GRAPH-029"
COMPOSITION_CANDIDATE_REFERENCE = "DEMO-TERMIVAR-COMPOSITION-024"
DEMO_LABEL = "DEMONSTRATION ONLY — RUST SOURCE REFERENCES — NO MODULE CLOSURE OR BUILD AUTHORIZED"
FALSE_FLAGS = (*_PREVIOUS_FALSE_FLAGS, "module_closure_verified")
COMMON_FIELDS = ("schema_version", "source_reference", "demo_label", "demo_only", *FALSE_FLAGS)

MAX_SCOPE_BYTES = 128 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_MANIFEST_BYTES = 128 * 1024
MAX_OLD_SUMMARY_BYTES = 512 * 1024
MAX_SUMMARY_BYTES = 256 * 1024
MAX_SOURCE_BYTES = 512 * 1024
MAX_TOTAL_SOURCE_BYTES = 1024 * 1024
MAX_TOTAL_INPUT_BYTES = 12 * 1024 * 1024
MAX_CHUNK_BYTES = 64 * 1024
MAX_SOURCE_FILES = 16
MAX_REFERENCES = 2048
MAX_DIAGNOSTICS = 4096
MAX_CONDITIONS = 4096
MAX_NODES = 4096
MAX_EDGES = 8192
MAX_NESTING_DEPTH = 128
MAX_COMMENT_DEPTH = 64
MAX_RAW_HASHES = 64
MAX_TOKENS_PER_FILE = 400_000
MAX_TOTAL_TOKENS = 750_000
MAX_LINE = MAX_SOURCE_BYTES + 1
MAX_COLUMN = MAX_SOURCE_BYTES + 1

GROUP_SCHEMAS = {
    "composition_sources": {
        "inventory": "termivar-offline-composition/v1",
        "dependencies": "termivar-offline-dependency-license-ledger/v1",
        "constraints": "termivar-offline-release-constraints/v1",
        "summary": None, "manifest": "termivar-offline-composition-manifest/v1",
    },
    "dependency_evidence_sources": {
        "evidence": "termivar-offline-direct-dependency-evidence/v1",
        "graph": "termivar-offline-direct-dependency-graph/v1",
        "variants": "termivar-offline-variant-dependency-evidence/v1",
        "summary": None, "manifest": "termivar-offline-direct-dependency-manifest/v1",
    },
    "entrypoint_sources": {
        "coverage": "termivar-offline-entrypoint-coverage/v1",
        "delta": "termivar-offline-source-scope-delta/v1",
        "variants": "termivar-offline-variant-entrypoint-projection/v1",
        "summary": None, "manifest": "termivar-offline-entrypoint-coverage-manifest/v1",
    },
}
SUPPORTED_FORMS = (
    "external_mod", "explicit_path_mod", "literal_include", "inline_mod",
    "dynamic_include_unresolved", "conditional_reference", "unsupported_reference",
)
LIMITATIONS = (
    "explicit_artifacts_and_allowlisted_rust_files_only",
    "lexical_subset_is_not_rust_ast_or_module_resolution",
    "external_module_name_does_not_establish_a_file_path",
    "macro_expansion_and_generated_sources_not_performed",
    "feature_and_target_conditions_not_evaluated",
    "observed_hash_is_not_git_or_producer_attestation",
    "global_f_catalog_is_not_component_selection",
    "phase28_scope_delta_remains_unapplied",
    "module_closure_and_component_ownership_not_verified",
    "inspector_checks_projected_metadata_not_original_rust",
)
ENTRYPOINT_FIELDS = (
    "entrypoint_reference", "source_file_reference", "root_id", "pinned_commit", "path",
    "bytes", "sha256", "target_reference", "manifest_reference",
)
ALLOWLIST_FIELDS = (
    "source_file_reference", "root_id", "pinned_commit", "path", "expected_bytes",
    "expected_sha256", "max_bytes", "read_kind",
)
SOURCE_FILE_FIELDS = (*ALLOWLIST_FIELDS, "read_status", "source_file_presence", "regular_file",
                      "observed_byte_size", "observed_sha256")
DELTA_FIELDS = (
    "proposal_reference", "source_file_reference", "path", "root_id", "pinned_commit",
    "observed_byte_size", "observed_sha256", "application_authorized", "application_performed",
    "phase24_inventory_modified", "component_ownership_verified",
)


def _fail(label: str) -> None:
    raise InputError("source_graph_invalid_" + label)


def _fixed(value: object, expected: object, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        _fail(label)


def _enum(value: object, choices: object, label: str) -> str:
    if type(value) is not str or value not in choices:
        _fail(label)
    return value


def _array(value: object, maximum: int, label: str, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        _fail(label)
    return value


def _unique(values: list, label: str) -> None:
    if len(set(values)) != len(values):
        _fail(label)


def _ids(value: object, maximum: int, label: str) -> list:
    rows = _array(value, maximum, label)
    for item in rows:
        identifier(item, label)
    _unique(rows, label)
    return rows


def _pin(value: object, label: str = "pin") -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        _fail(label)
    return value


def _rsf(value: object, label: str = "source_reference", nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or re.fullmatch(r"RSF[0-9]{4}", value) is None or not 1 <= int(value[3:]) <= MAX_SOURCE_FILES:
        _fail(label)
    return value


def _epf(value: object, label: str = "entrypoint_reference") -> str:
    if type(value) is not str or re.fullmatch(r"EPF[0-9]{4}", value) is None or not 1 <= int(value[3:]) <= 32:
        _fail(label)
    return value


def _digest_id(value: object, prefix: str, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or not value.startswith(prefix):
        _fail(label)
    sha256(value[len(prefix):], label)
    return value


def _rust_name(value: object, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or len(value) > 128 or re.fullmatch(r"(?:r#)?[A-Za-z_][A-Za-z_0-9]*", value) is None:
        _fail(label)
    return value


def parse_json(raw: bytes, maximum: int = MAX_JSON_BYTES) -> object:
    integer(maximum, "json_limit", MAX_JSON_BYTES)
    return _parse_json(raw, maximum=maximum)


def json_bytes(value: object, maximum: int = MAX_JSON_BYTES) -> bytes:
    integer(maximum, "json_limit", MAX_JSON_BYTES)
    return _json_bytes(value, maximum=maximum)


def _group(value: object, name: str, *, paths: bool) -> dict:
    result = closed(value, GROUP_SCHEMAS[name], "source_group")
    for role, schema in GROUP_SCHEMAS[name].items():
        row = closed(result[role], ("path", "schema_version", "bytes", "sha256") if paths else ("schema_version", "bytes", "sha256"), "source_descriptor")
        _fixed(row["schema_version"], schema, "source_schema")
        if paths:
            relative_path(row["path"], "artifact_path")
        maximum = MAX_ARTIFACT_MANIFEST_BYTES if role == "manifest" else MAX_OLD_SUMMARY_BYTES if role == "summary" else MAX_JSON_BYTES
        if integer(row["bytes"], "artifact_bytes", maximum) == 0:
            _fail("artifact_bytes")
        sha256(row["sha256"], "artifact_sha256")
    return result


def validate_reference(value: object, *, full: bool = True) -> dict:
    fields = ("candidate_reference", "composition_candidate_reference", "source_commits")
    ref = closed(value, (*fields, *GROUP_SCHEMAS) if full else fields, "source_reference")
    _fixed(ref["candidate_reference"], CANDIDATE_REFERENCE, "candidate")
    _fixed(ref["composition_candidate_reference"], COMPOSITION_CANDIDATE_REFERENCE, "composition_candidate")
    pins = closed(ref["source_commits"], ("termivar", "platform"), "source_commits")
    for pin in pins.values():
        _pin(pin)
    if full:
        for name in GROUP_SCHEMAS:
            _group(ref[name], name, paths=False)
        if sum(row["bytes"] for name in GROUP_SCHEMAS for row in ref[name].values()) > MAX_TOTAL_INPUT_BYTES:
            _fail("artifact_total")
    return copy.deepcopy(ref)


validate_source_reference = validate_reference


def common(schema: str, reference: dict) -> dict:
    _enum(schema, (LEDGER_SCHEMA, GRAPH_SCHEMA, COVERAGE_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA), "schema")
    return {"schema_version": schema, "source_reference": validate_reference(reference),
            "demo_label": DEMO_LABEL, "demo_only": True, **{flag: False for flag in FALSE_FLAGS}}


def _common(value: object, schema: str, fields: object) -> dict:
    row = closed(value, (*COMMON_FIELDS, *fields), "document_fields")
    _fixed(row["schema_version"], schema, "schema")
    validate_reference(row["source_reference"])
    _fixed(row["demo_label"], DEMO_LABEL, "demo_label")
    _fixed(row["demo_only"], True, "demo_only")
    for name in FALSE_FLAGS:
        _fixed(row[name], False, "trust_flag")
    return row


def _entrypoints(value: object) -> list:
    rows = _array(value, MAX_SOURCE_FILES, "entrypoints", 1)
    for row in rows:
        closed(row, ENTRYPOINT_FIELDS, "entrypoint_fields")
        _epf(row["entrypoint_reference"])
        _rsf(row["source_file_reference"])
        _fixed(row["root_id"], "termivar", "entrypoint_root")
        _pin(row["pinned_commit"])
        relative_path(row["path"], "entrypoint_path")
        if not row["path"].endswith(".rs"):
            _fail("entrypoint_extension")
        integer(row["bytes"], "entrypoint_bytes", MAX_SOURCE_BYTES)
        sha256(row["sha256"], "entrypoint_hash")
        _digest_id(row["target_reference"], "target-", "entrypoint_target")
        identifier(row["manifest_reference"], "entrypoint_manifest")
    for field in ("entrypoint_reference", "source_file_reference", "target_reference"):
        _unique([row[field] for row in rows], "entrypoint_ids")
    _unique([(row["root_id"], row["pinned_commit"], row["path"]) for row in rows], "entrypoint_paths")
    return rows


def _allowlist(value: object) -> list:
    rows = _array(value, MAX_SOURCE_FILES, "allowlist", 1)
    for row in rows:
        closed(row, ALLOWLIST_FIELDS, "allowlist_fields")
        _rsf(row["source_file_reference"])
        _fixed(row["root_id"], "termivar", "source_root")
        _pin(row["pinned_commit"])
        relative_path(row["path"], "source_path")
        if not row["path"].endswith(".rs"):
            _fail("source_extension")
        integer(row["expected_bytes"], "source_expected_bytes", MAX_SOURCE_BYTES)
        sha256(row["expected_sha256"], "source_expected_hash")
        if not row["expected_bytes"] <= integer(row["max_bytes"], "source_limit", MAX_SOURCE_BYTES) or row["max_bytes"] == 0:
            _fail("source_limit")
        _fixed(row["read_kind"], "bounded_sha256", "read_kind")
    _unique([r["source_file_reference"] for r in rows], "allowlist_ids")
    _unique([(r["root_id"], r["pinned_commit"], r["path"]) for r in rows], "allowlist_paths")
    if sum(r["expected_bytes"] for r in rows) > MAX_TOTAL_SOURCE_BYTES:
        _fail("total_source_bytes")
    return rows


def validate_scope(value: object) -> dict:
    scope = closed(value, ("schema_version", "mode", "source_reference", "entrypoint_sources", "coverage_sources",
                           "allowed_source_files", "reference_policy", "inspection_constraints"), "scope_fields")
    _fixed(scope["schema_version"], SCOPE_SCHEMA, "scope_schema")
    _fixed(scope["mode"], "demo", "scope_mode")
    ref = validate_reference(scope["source_reference"], full=False)
    entries = _entrypoints(scope["entrypoint_sources"])
    groups = closed(scope["coverage_sources"], GROUP_SCHEMAS, "coverage_sources")
    for name in GROUP_SCHEMAS:
        _group(groups[name], name, paths=True)
    if sum(r["bytes"] for name in GROUP_SCHEMAS for r in groups[name].values()) > MAX_TOTAL_INPUT_BYTES:
        _fail("artifact_total")
    paths = [r["path"] for name in GROUP_SCHEMAS for r in groups[name].values()]
    _unique(paths, "artifact_paths")
    allowed = _allowlist(scope["allowed_source_files"])
    by_id = {r["source_file_reference"]: r for r in allowed}
    for entry in entries:
        a = by_id.get(entry["source_file_reference"])
        if (a is None or any(entry[k] != a[k] for k in ("root_id", "pinned_commit", "path"))
                or entry["bytes"] != a["expected_bytes"] or entry["sha256"] != a["expected_sha256"]):
            _fail("entrypoint_allowlist")
    if any(r["pinned_commit"] != ref["source_commits"][r["root_id"]] for r in allowed):
        _fail("source_pin")
    policy = closed(scope["reference_policy"], ("supported_forms", "macro_expansion_performed", "feature_evaluation_performed",
                                               "target_evaluation_performed", "module_resolution_performed"), "reference_policy")
    _fixed(policy["supported_forms"], list(SUPPORTED_FORMS), "supported_forms")
    for k in policy:
        if k != "supported_forms":
            _fixed(policy[k], False, "reference_policy_flag")
    constraints = closed(scope["inspection_constraints"], ("projected_metadata_only", "original_sources_read", "lexer_reexecuted", "source_attestation_performed"), "inspection_constraints")
    for k in constraints:
        _fixed(constraints[k], k == "projected_metadata_only", "inspection_constraint")
    json_bytes(scope, MAX_SCOPE_BYTES)
    return copy.deepcopy(scope)


def validate_parent_context(value: object) -> dict:
    context = closed(value, ("phase24_context", "phase28_entrypoints", "phase28_deltas"), "parent_context")
    old = _validate_phase24_context(context["phase24_context"])
    pins = {r["root_id"]: r["pinned_commit"] for r in old["source_roots"]}
    entries = _entrypoints(context["phase28_entrypoints"])
    if any(r["pinned_commit"] != pins[r["root_id"]] for r in entries):
        _fail("parent_pin")
    _parent_deltas(context["phase28_deltas"], entries)
    return copy.deepcopy(context)


def _parent_deltas(value: object, entries: list) -> list:
    deltas = _array(value, 64, "phase28_deltas")
    entry_by_epf = {r["entrypoint_reference"]: r for r in entries}
    for d in deltas:
        closed(d, DELTA_FIELDS, "phase28_delta_fields")
        _digest_id(d["proposal_reference"], "proposal-", "phase28_proposal")
        _epf(d["source_file_reference"])
        e = entry_by_epf.get(d["source_file_reference"])
        if e is None or any(d[k] != e[k] for k in ("root_id", "pinned_commit", "path")):
            _fail("phase28_delta_identity")
        integer(d["observed_byte_size"], "phase28_delta_bytes", MAX_SOURCE_BYTES)
        sha256(d["observed_sha256"], "phase28_delta_sha256")
        if d["observed_byte_size"] != e["bytes"] or d["observed_sha256"] != e["sha256"]:
            _fail("phase28_delta_hash")
        expected = record_digest({"root_id": d["root_id"], "pinned_commit": d["pinned_commit"], "path": d["path"],
                                  "observed_byte_size": d["observed_byte_size"], "observed_sha256": d["observed_sha256"]})
        _fixed(d["proposal_reference"], "proposal-" + expected, "phase28_delta_id")
        for key in DELTA_FIELDS[-4:]:
            _fixed(d[key], False, "phase28_delta_flag")
    _unique([d["proposal_reference"] for d in deltas], "phase28_delta_ids")
    return deltas


validate_context = validate_parent_context


def validate_source_files(value: object, context: dict | None = None) -> list:
    rows = _array(value, MAX_SOURCE_FILES, "source_files", 1)
    _allowlist([{k: r[k] for k in ALLOWLIST_FIELDS} for r in rows if type(r) is dict and set(r) == set(SOURCE_FILE_FIELDS)])
    for row in rows:
        closed(row, SOURCE_FILE_FIELDS, "source_file_fields")
        status = _enum(row["read_status"], ("present_and_hashed", "declared_file_missing"), "read_status")
        if status == "present_and_hashed":
            _fixed(row["source_file_presence"], "present", "file_presence")
            _fixed(row["regular_file"], True, "regular_file")
            _fixed(row["observed_byte_size"], row["expected_bytes"], "observed_bytes")
            _fixed(row["observed_sha256"], row["expected_sha256"], "observed_hash")
        else:
            _fixed(row["source_file_presence"], "missing", "file_presence")
            for key in ("regular_file", "observed_byte_size", "observed_sha256"):
                _fixed(row[key], None, "missing_file_metadata")
    if context is not None:
        ctx = validate_parent_context(context)
        pins = {r["root_id"]: r["pinned_commit"] for r in ctx["phase24_context"]["source_roots"]}
        if any(r["pinned_commit"] != pins[r["root_id"]] for r in rows):
            _fail("source_context_pin")
        by_id = {r["source_file_reference"]: r for r in rows}
        for e in ctx["phase28_entrypoints"]:
            r = by_id.get(e["source_file_reference"])
            if (r is None or any(r[k] != e[k] for k in ("root_id", "pinned_commit", "path"))
                    or r["expected_bytes"] != e["bytes"] or r["expected_sha256"] != e["sha256"]):
                _fail("parent_source_identity")
    return copy.deepcopy(rows)


REFERENCE_KINDS = (
    "external_module_declaration", "explicit_path_module_declaration", "literal_include_reference",
    "inline_module_declaration", "dynamic_reference_unresolved", "unsupported_reference",
)
INTERPRETATION_STATUSES = (
    "observed_static_reference", "dynamic_reference_unresolved", "attribute_binding_unresolved",
    "conditional_path_unresolved", "path_resolution_context_unresolved", "macro_context_unresolved", "unsupported_reference",
)
REFERENCE_REASON_CODES = (
    "module_file_resolution_not_performed", "inline_module_has_no_external_file",
    "literal_path_requires_explicit_allowlist", "dynamic_include_not_evaluated",
    "condition_evaluation_not_performed", "conditional_path_not_established",
    "attribute_binding_not_established", "relative_path_context_not_established",
    "macro_expansion_not_performed", "unsupported_static_reference", "unsupported_literal_path",
    "lexical_context_not_established",
)
DIAGNOSTIC_CODES = (
    "unsupported_lexical_construct", "lexical_boundary_unresolved", "unsupported_literal_escape",
    "attribute_binding_unresolved", "conditional_path_unresolved", "path_resolution_context_unresolved",
    "macro_context_unresolved", "unsupported_reference", "dynamic_reference_unresolved",
)
LEXICAL_STATUSES = ("lexically_bounded", "unsupported_lexical_construct", "lexical_boundary_unresolved")
POSITION_FIELDS = ("byte_offset", "line", "column")
REFERENCE_FIELDS = (
    "reference_id", "source_file_reference", "source_sha256", "position", "byte_end", "reference_kind",
    "declared_module_name", "literal_relative_path", "lexical_scope", "nesting_depth", "parent_inline_reference",
    "condition_ids", "interpretation_status", "context_reliability", "resolved_file", "reason_codes",
)
CONDITION_FIELDS = (
    "condition_id", "source_file_reference", "source_sha256", "position", "byte_end", "kind",
    "attribute_style", "span_sha256", "evaluation_status",
)
DIAGNOSTIC_FIELDS = (
    "diagnostic_id", "source_file_reference", "source_sha256", "position", "byte_end", "code",
    "reference_id", "lexical_scope",
)
LEXICAL_SUMMARY_FIELDS = (
    "source_file_reference", "source_sha256", "lexical_status", "scan_complete", "token_count", "line_count",
    "crlf_count", "line_comment_count", "block_comment_count", "string_literal_count", "raw_string_literal_count",
    "byte_string_literal_count", "raw_byte_string_literal_count", "character_literal_count", "lifetime_count",
    "maximum_delimiter_depth", "maximum_comment_depth", "maximum_raw_hashes", "opaque_macro_tree_count",
    "reference_count", "condition_count", "diagnostic_count",
)
BINDING_STATUSES = (
    "inline_not_external", "external_module_path_unresolved", "dynamic_reference_unresolved",
    "path_resolution_context_unresolved", "unsupported_reference", "not_allowlisted", "file_missing",
    "bound_to_observed_file", "conditional_path_unresolved", "lexical_boundary_unresolved",
)
BINDING_FIELDS = (
    "binding_id", "reference_id", "source_file_reference", "literal_relative_path", "normalized_relative_path",
    "candidate_file_references", "bound_file_reference", "binding_status", "condition_ids", "reason_codes",
)
LEDGER_COUNT_FIELDS = (
    "source_file_count", "present_source_file_count", "missing_source_file_count", "observed_source_bytes",
    "lexically_bounded_file_count", "partial_unverified_file_count", "token_count", "reference_count",
    "external_module_count", "inline_module_count", "explicit_literal_reference_count", "conditional_reference_count",
    "condition_count", "diagnostic_count", "bound_file_reference_count", "unresolved_reference_count",
    "by_reference_kind", "by_binding_status",
)
NODE_TYPES = ("entrypoint_source", "allowlisted_source_file", "static_reference", "unresolved_reference")
EDGE_TYPES = (
    "source_contains_reference", "reference_explicitly_names_file", "reference_bound_to_observed_file",
    "reference_may_resolve_to_file", "reference_unresolved", "conditional_reference_unresolved",
)
CERTAINTIES = ("definite", "possible", "unresolved")


def reference_identifier(row: dict) -> str:
    return "rust-ref-" + record_digest({k: row[k] for k in (
        "source_file_reference", "source_sha256", "position", "byte_end", "reference_kind", "lexical_scope")})


def condition_identifier(row: dict) -> str:
    return "rust-condition-" + record_digest({k: row[k] for k in (
        "source_file_reference", "source_sha256", "position", "byte_end", "kind", "attribute_style", "span_sha256")})


def diagnostic_identifier(row: dict) -> str:
    return "rust-diagnostic-" + record_digest({k: row[k] for k in (
        "source_file_reference", "source_sha256", "position", "byte_end", "code", "reference_id", "lexical_scope")})


def _codes(value: object, choices: tuple, label: str) -> list:
    rows = _array(value, len(choices), label)
    for row in rows:
        _enum(row, choices, label)
    _unique(rows, label)
    return rows


def _position(value: object, byte_end: object, source: dict) -> None:
    position = closed(value, POSITION_FIELDS, "position")
    size = source["observed_byte_size"]
    if size is None:
        _fail("unread_source_position")
    offset = integer(position["byte_offset"], "byte_offset", size)
    end = integer(byte_end, "byte_end", size)
    if end < offset:
        _fail("byte_span")
    if integer(position["line"], "line", size + 1) == 0 or integer(position["column"], "column", size + 1) == 0:
        _fail("position_origin")


def _source_record(row: dict, sources: dict) -> dict:
    _rsf(row["source_file_reference"])
    source = sources.get(row["source_file_reference"])
    if source is None or source["read_status"] != "present_and_hashed":
        _fail("metadata_source")
    sha256(row["source_sha256"], "source_sha256")
    _fixed(row["source_sha256"], source["observed_sha256"], "metadata_source_sha256")
    return source


def _ordered_source_rows(rows: list, label: str) -> None:
    positions: dict[str, list] = {}
    for r in rows:
        positions.setdefault(r["source_file_reference"], []).append((r["position"]["byte_offset"], r["byte_end"]))
    for values in positions.values():
        if values != sorted(values):
            _fail(label)


def validate_conditions(value: object, source_files: list) -> list:
    rows = _array(value, MAX_CONDITIONS, "conditions")
    sources = {s["source_file_reference"]: s for s in validate_source_files(source_files)}
    for r in rows:
        closed(r, CONDITION_FIELDS, "condition_fields")
        source = _source_record(r, sources)
        _position(r["position"], r["byte_end"], source)
        _enum(r["kind"], ("cfg", "cfg_attr"), "condition_kind")
        _enum(r["attribute_style"], ("outer", "inner"), "attribute_style")
        sha256(r["span_sha256"], "condition_span_sha256")
        _fixed(r["evaluation_status"], "condition_declared_evaluation_not_performed", "condition_evaluation")
        _fixed(r["condition_id"], condition_identifier(r), "condition_id")
    _unique([r["condition_id"] for r in rows], "condition_ids")
    _ordered_source_rows(rows, "condition_order")
    return copy.deepcopy(rows)


def validate_references(value: object, source_files: list, conditions: list | None = None) -> list:
    rows = _array(value, MAX_REFERENCES, "references")
    sources = {s["source_file_reference"]: s for s in validate_source_files(source_files)}
    condition_map = None if conditions is None else {r["condition_id"]: r for r in validate_conditions(conditions, source_files)}
    for r in rows:
        closed(r, REFERENCE_FIELDS, "reference_fields")
        source = _source_record(r, sources)
        _position(r["position"], r["byte_end"], source)
        kind = _enum(r["reference_kind"], REFERENCE_KINDS, "reference_kind")
        _rust_name(r["declared_module_name"], "module_name", nullable=True)
        if r["literal_relative_path"] is not None:
            text(r["literal_relative_path"], "literal_path", 1024)
            relative_path(r["literal_relative_path"], "literal_path")
        if kind in ("external_module_declaration", "explicit_path_module_declaration", "inline_module_declaration"):
            if r["declared_module_name"] is None:
                _fail("module_name_required")
        elif r["declared_module_name"] is not None:
            _fail("non_module_name")
        if kind in ("external_module_declaration", "inline_module_declaration", "dynamic_reference_unresolved") and r["literal_relative_path"] is not None:
            _fail("non_literal_reference")
        if (kind in ("explicit_path_module_declaration", "literal_include_reference") and r["literal_relative_path"] is None
                and r["interpretation_status"] not in ("unsupported_reference", "attribute_binding_unresolved")):
            _fail("literal_reference_path")
        scope = _ids(r["lexical_scope"], MAX_NESTING_DEPTH, "lexical_scope")
        for ref in scope:
            _digest_id(ref, "rust-ref-", "scope_reference")
        _fixed(r["nesting_depth"], len(scope), "nesting_depth")
        _fixed(r["parent_inline_reference"], scope[-1] if scope else None, "inline_parent")
        ids = _ids(r["condition_ids"], MAX_CONDITIONS, "reference_conditions")
        for cid in ids:
            _digest_id(cid, "rust-condition-", "reference_condition")
            if condition_map is not None:
                c = condition_map.get(cid)
                if c is None or c["source_file_reference"] != r["source_file_reference"]:
                    _fail("condition_reference")
        _enum(r["interpretation_status"], INTERPRETATION_STATUSES, "interpretation_status")
        _enum(r["context_reliability"], ("lexically_bounded", "context_unresolved"), "context_reliability")
        _fixed(r["resolved_file"], False, "compiler_resolution")
        _codes(r["reason_codes"], REFERENCE_REASON_CODES, "reference_reasons")
        _fixed(r["reference_id"], reference_identifier(r), "reference_id")
    _unique([r["reference_id"] for r in rows], "reference_ids")
    ref_map = {r["reference_id"]: r for r in rows}
    for r in rows:
        for i, parent_id in enumerate(r["lexical_scope"]):
            parent = ref_map.get(parent_id)
            if (parent is None or parent["reference_kind"] != "inline_module_declaration"
                    or parent["source_file_reference"] != r["source_file_reference"]
                    or parent["lexical_scope"] != r["lexical_scope"][:i]
                    or not parent["position"]["byte_offset"] < r["position"]["byte_offset"] < r["byte_end"] <= parent["byte_end"]):
                _fail("inline_scope_binding")
            if not set(parent["condition_ids"]).issubset(r["condition_ids"]):
                _fail("inline_condition_inheritance")
    _ordered_source_rows(rows, "reference_order")
    return copy.deepcopy(rows)


def validate_diagnostics(value: object, source_files: list, references: list | None = None) -> list:
    rows = _array(value, MAX_DIAGNOSTICS, "diagnostics")
    sources = {s["source_file_reference"]: s for s in validate_source_files(source_files)}
    ref_map = None if references is None else {r["reference_id"]: r for r in references}
    for r in rows:
        closed(r, DIAGNOSTIC_FIELDS, "diagnostic_fields")
        source = _source_record(r, sources)
        _position(r["position"], r["byte_end"], source)
        _enum(r["code"], DIAGNOSTIC_CODES, "diagnostic_code")
        _digest_id(r["reference_id"], "rust-ref-", "diagnostic_reference", nullable=True)
        scope = _ids(r["lexical_scope"], MAX_NESTING_DEPTH, "diagnostic_scope")
        for key in ([r["reference_id"]] if r["reference_id"] is not None else []) + scope:
            _digest_id(key, "rust-ref-", "diagnostic_scope_reference")
            if ref_map is not None and (key not in ref_map or ref_map[key]["source_file_reference"] != r["source_file_reference"]):
                _fail("diagnostic_reference")
        if ref_map is not None and any(ref_map[k]["reference_kind"] != "inline_module_declaration" for k in scope):
            _fail("diagnostic_inline_scope")
        _fixed(r["diagnostic_id"], diagnostic_identifier(r), "diagnostic_id")
    _unique([r["diagnostic_id"] for r in rows], "diagnostic_ids")
    _ordered_source_rows(rows, "diagnostic_order")
    return copy.deepcopy(rows)


def validate_lexical_summaries(value: object, source_files: list, references: list, conditions: list, diagnostics: list) -> list:
    rows = _array(value, MAX_SOURCE_FILES, "lexical_summaries")
    sources = {s["source_file_reference"]: s for s in validate_source_files(source_files)}
    for r in rows:
        closed(r, LEXICAL_SUMMARY_FIELDS, "lexical_summary_fields")
        source = _source_record(r, sources)
        status = _enum(r["lexical_status"], LEXICAL_STATUSES, "lexical_status")
        _fixed(r["scan_complete"], status == "lexically_bounded", "scan_complete")
        for key in LEXICAL_SUMMARY_FIELDS[4:]:
            maximum = MAX_TOKENS_PER_FILE if key == "token_count" else MAX_NESTING_DEPTH if key == "maximum_delimiter_depth" else MAX_COMMENT_DEPTH if key == "maximum_comment_depth" else MAX_RAW_HASHES if key == "maximum_raw_hashes" else MAX_REFERENCES if key == "reference_count" else MAX_CONDITIONS if key == "condition_count" else MAX_DIAGNOSTICS if key == "diagnostic_count" else MAX_SOURCE_BYTES + 1
            integer(r[key], "lexical_counter", maximum)
        if r["line_count"] == 0 or r["line_count"] > source["observed_byte_size"] + 1 or r["crlf_count"] >= r["line_count"]:
            _fail("lexical_lines")
        for key, data in (("reference_count", references), ("condition_count", conditions), ("diagnostic_count", diagnostics)):
            _fixed(r[key], sum(x["source_file_reference"] == r["source_file_reference"] for x in data), "lexical_record_count")
        if status != "lexically_bounded":
            if r["reference_count"] != 0 or r["condition_count"] != 0 or r["diagnostic_count"] != 1:
                _fail("failed_lexical_projection")
            diag = next(d for d in diagnostics if d["source_file_reference"] == r["source_file_reference"])
            allowed_codes = ("lexical_boundary_unresolved", "macro_context_unresolved") if status == "lexical_boundary_unresolved" else (status,)
            if diag["code"] not in allowed_codes or diag["reference_id"] is not None or diag["lexical_scope"]:
                _fail("failed_lexical_diagnostic")
        for data in (references, conditions, diagnostics):
            if any(x["source_file_reference"] == r["source_file_reference"] and x["position"]["line"] > r["line_count"] for x in data):
                _fail("lexical_line_bound")
    _unique([r["source_file_reference"] for r in rows], "summary_source_ids")
    if {r["source_file_reference"] for r in rows} != {r["source_file_reference"] for r in source_files if r["read_status"] == "present_and_hashed"}:
        _fail("summary_source_coverage")
    if sum(r["token_count"] for r in rows) > MAX_TOTAL_TOKENS:
        _fail("total_token_budget")
    return copy.deepcopy(rows)


def validate_inputs(parent_context: dict, source_files: list, lexical_summaries: list, references: list, conditions: list, diagnostics: list) -> None:
    validate_source_files(source_files, parent_context)
    validate_conditions(conditions, source_files)
    validate_references(references, source_files, conditions)
    validate_diagnostics(diagnostics, source_files, references)
    validate_lexical_summaries(lexical_summaries, source_files, references, conditions, diagnostics)


validate_ledger_inputs = validate_inputs


BINDING_REASON_CODES = (*REFERENCE_REASON_CODES, "explicit_literal_path_not_allowlisted", "allowlisted_file_missing",
                        "observed_file_identity_bound", "unsafe_literal_path")


def validate_bindings(value: object, source_files: list, references: list) -> list:
    rows = _array(value, MAX_REFERENCES, "bindings")
    refs = {r["reference_id"]: r for r in references}
    sources = {r["source_file_reference"]: r for r in source_files}
    for b in rows:
        closed(b, BINDING_FIELDS, "binding_fields")
        r = refs.get(b["reference_id"])
        if r is None:
            _fail("binding_reference")
        _fixed(b["binding_id"], "binding-" + record_digest({"reference_id": b["reference_id"]}), "binding_id")
        for key in ("source_file_reference", "literal_relative_path", "condition_ids"):
            _fixed(b[key], r[key], "binding_reference_metadata")
        status = _enum(b["binding_status"], BINDING_STATUSES, "binding_status")
        candidates = _ids(b["candidate_file_references"], MAX_SOURCE_FILES, "binding_candidates")
        for key in candidates:
            _rsf(key)
            if key not in sources:
                _fail("binding_candidate")
        bound = _rsf(b["bound_file_reference"], "bound_file_reference", nullable=True)
        if b["normalized_relative_path"] is not None:
            relative_path(b["normalized_relative_path"], "binding_path")
        _codes(b["reason_codes"], BINDING_REASON_CODES, "binding_reasons")
        if status == "bound_to_observed_file":
            if (bound not in sources or bound not in candidates or len(candidates) != 1
                    or sources[bound]["read_status"] != "present_and_hashed"
                    or r["reference_kind"] not in ("explicit_path_module_declaration", "literal_include_reference")
                    or r["literal_relative_path"] is None or r["lexical_scope"]
                    or r["context_reliability"] != "lexically_bounded"
                    or r["interpretation_status"] != "observed_static_reference"):
                _fail("observed_file_binding")
        elif bound is not None:
            _fail("unresolved_bound_file")
        if status == "file_missing" and (len(candidates) != 1 or sources[candidates[0]]["read_status"] != "declared_file_missing"):
            _fail("missing_file_binding")
        if candidates:
            source = sources[r["source_file_reference"]]
            if b["normalized_relative_path"] is None or status not in ("bound_to_observed_file", "file_missing", "conditional_path_unresolved"):
                _fail("binding_candidate_semantics")
            for key in candidates:
                target = sources[key]
                if (target["root_id"] != source["root_id"] or target["pinned_commit"] != source["pinned_commit"]
                        or target["path"] != b["normalized_relative_path"]):
                    _fail("binding_candidate_identity")
        if r["reference_kind"] in ("external_module_declaration", "inline_module_declaration", "dynamic_reference_unresolved"):
            expected = {"external_module_declaration": "external_module_path_unresolved",
                        "inline_module_declaration": "inline_not_external",
                        "dynamic_reference_unresolved": "dynamic_reference_unresolved"}[r["reference_kind"]]
            if r["context_reliability"] == "lexically_bounded" and r["interpretation_status"] == "observed_static_reference":
                _fixed(status, expected, "binding_kind")
            if candidates or b["normalized_relative_path"] is not None:
                _fail("invented_module_path")
    _unique([b["binding_id"] for b in rows], "binding_ids")
    _unique([b["reference_id"] for b in rows], "binding_reference_ids")
    if {b["reference_id"] for b in rows} != set(refs):
        _fail("binding_coverage")
    return copy.deepcopy(rows)


def ledger_counts(source_files: list, summaries: list, references: list, conditions: list, diagnostics: list, bindings: list) -> dict:
    kinds = Counter(r["reference_kind"] for r in references)
    statuses = Counter(b["binding_status"] for b in bindings)
    return {
        "source_file_count": len(source_files),
        "present_source_file_count": sum(r["read_status"] == "present_and_hashed" for r in source_files),
        "missing_source_file_count": sum(r["read_status"] == "declared_file_missing" for r in source_files),
        "observed_source_bytes": sum(r["observed_byte_size"] or 0 for r in source_files),
        "lexically_bounded_file_count": sum(r["lexical_status"] == "lexically_bounded" for r in summaries),
        "partial_unverified_file_count": sum(r["lexical_status"] != "lexically_bounded" for r in summaries),
        "token_count": sum(r["token_count"] for r in summaries), "reference_count": len(references),
        "external_module_count": kinds["external_module_declaration"], "inline_module_count": kinds["inline_module_declaration"],
        "explicit_literal_reference_count": sum(r["reference_kind"] in ("explicit_path_module_declaration", "literal_include_reference") and r["literal_relative_path"] is not None for r in references),
        "conditional_reference_count": sum(bool(r["condition_ids"]) for r in references),
        "condition_count": len(conditions), "diagnostic_count": len(diagnostics),
        "bound_file_reference_count": statuses["bound_to_observed_file"],
        "unresolved_reference_count": sum(b["binding_status"] not in ("bound_to_observed_file", "inline_not_external") for b in bindings),
        "by_reference_kind": [{"reference_kind": k, "reference_count": kinds[k]} for k in REFERENCE_KINDS],
        "by_binding_status": [{"binding_status": k, "reference_count": statuses[k]} for k in BINDING_STATUSES],
    }


def _count_rows(value: object, choices: tuple, key: str, count_keys: tuple, expected: dict, label: str) -> None:
    rows = _array(value, len(choices), label)
    if len(rows) != len(choices):
        _fail(label)
    for row, choice in zip(rows, choices):
        closed(row, (key, *count_keys), label)
        _fixed(row[key], choice, label)
        for k in count_keys:
            integer(row[k], label, MAX_EDGES)
            _fixed(row[k], expected[choice][k], label)


def validate_ledger(value: object) -> dict:
    row = _common(value, LEDGER_SCHEMA, ("parent_context", "source_files", "lexical_summaries", "references",
                                        "conditions", "diagnostics", "bindings", "counts", "limitations"))
    validate_inputs(row["parent_context"], row["source_files"], row["lexical_summaries"], row["references"], row["conditions"], row["diagnostics"])
    validate_bindings(row["bindings"], row["source_files"], row["references"])
    pins = {r["root_id"]: r["pinned_commit"] for r in row["parent_context"]["phase24_context"]["source_roots"]}
    _fixed(row["source_reference"]["source_commits"], pins, "parent_reference_pins")
    counts = closed(row["counts"], LEDGER_COUNT_FIELDS, "ledger_counts")
    expected = ledger_counts(row["source_files"], row["lexical_summaries"], row["references"], row["conditions"], row["diagnostics"], row["bindings"])
    for key in LEDGER_COUNT_FIELDS[:-2]:
        integer(counts[key], "ledger_count", MAX_TOTAL_TOKENS if key == "token_count" else MAX_TOTAL_SOURCE_BYTES)
        _fixed(counts[key], expected[key], "ledger_count")
    for key, enumkey, choices in (("by_reference_kind", "reference_kind", REFERENCE_KINDS), ("by_binding_status", "binding_status", BINDING_STATUSES)):
        expected_map = {r[enumkey]: r for r in expected[key]}
        _count_rows(counts[key], choices, enumkey, ("reference_count",), expected_map, "ledger_group_count")
    _fixed(row["limitations"], list(LIMITATIONS), "limitations")
    json_bytes(row)
    return copy.deepcopy(row)


NODE_FIELDS = ("node_id", "node_type", "source_reference_id", "source_fingerprint", "label", "evidence_status")
EDGE_FIELDS = ("edge_id", "edge_type", "from_node_id", "to_node_id", "certainty", "evidence_refs", "source_fingerprint")
GRAPH_COUNT_FIELDS = ("node_count", "edge_count", "source_file_node_count", "reference_node_count", "unresolved_reference_node_count",
                      "by_node_type", "by_edge_type", "by_certainty")


def validate_graph(value: object) -> dict:
    row = _common(value, GRAPH_SCHEMA, ("nodes", "edges", "counts", "limitations"))
    nodes = _array(row["nodes"], MAX_NODES, "nodes")
    edges = _array(row["edges"], MAX_EDGES, "edges")
    for n in nodes:
        closed(n, NODE_FIELDS, "node_fields")
        kind = _enum(n["node_type"], NODE_TYPES, "node_type")
        if kind in NODE_TYPES[:2]:
            _rsf(n["source_reference_id"])
        else:
            _digest_id(n["source_reference_id"], "rust-ref-", "node_reference")
        sha256(n["source_fingerprint"], "node_fingerprint")
        text(n["label"], "node_label", 256)
        _fixed(n["evidence_status"], "source_metadata_only", "node_evidence_status")
        _fixed(n["node_id"], "node-" + record_digest({k: n[k] for k in ("node_type", "source_reference_id", "source_fingerprint")}), "node_id")
    _unique([n["node_id"] for n in nodes], "node_ids")
    node_map = {n["node_id"]: n for n in nodes}
    for e in edges:
        closed(e, EDGE_FIELDS, "edge_fields")
        _enum(e["edge_type"], EDGE_TYPES, "edge_type")
        _enum(e["certainty"], CERTAINTIES, "edge_certainty")
        if e["from_node_id"] not in node_map or e["to_node_id"] not in node_map:
            _fail("edge_endpoint")
        refs = _ids(e["evidence_refs"], MAX_CONDITIONS + 4, "edge_evidence_refs")
        for ref in refs:
            if re.fullmatch(r"RSF[0-9]{4}", ref):
                _rsf(ref)
            elif ref.startswith("rust-ref-"):
                _digest_id(ref, "rust-ref-", "edge_evidence_reference")
            elif ref.startswith("rust-condition-"):
                _digest_id(ref, "rust-condition-", "edge_condition_reference")
            else:
                _digest_id(ref, "binding-", "edge_binding_reference")
        fp = record_digest({k: e[k] for k in ("edge_type", "from_node_id", "to_node_id", "certainty", "evidence_refs")})
        _fixed(e["source_fingerprint"], fp, "edge_fingerprint")
        _fixed(e["edge_id"], "edge-" + fp, "edge_id")
    _unique([e["edge_id"] for e in edges], "edge_ids")
    counts = closed(row["counts"], GRAPH_COUNT_FIELDS, "graph_counts")
    nc = Counter(n["node_type"] for n in nodes)
    expected = {"node_count": len(nodes), "edge_count": len(edges), "source_file_node_count": sum(nc[k] for k in NODE_TYPES[:2]),
                "reference_node_count": nc["static_reference"], "unresolved_reference_node_count": nc["unresolved_reference"]}
    for key, count in expected.items():
        integer(counts[key], "graph_count", MAX_EDGES)
        _fixed(counts[key], count, "graph_count")
    _count_rows(counts["by_node_type"], NODE_TYPES, "node_type", ("node_count",), {k: {"node_count": nc[k]} for k in NODE_TYPES}, "node_type_counts")
    ec = {k: {c + "_edge_count": sum(e["edge_type"] == k and e["certainty"] == c for e in edges) for c in CERTAINTIES} for k in EDGE_TYPES}
    _count_rows(counts["by_edge_type"], EDGE_TYPES, "edge_type", tuple(c + "_edge_count" for c in CERTAINTIES), ec, "edge_type_counts")
    _count_rows(counts["by_certainty"], CERTAINTIES, "certainty", ("edge_count",), {k: {"edge_count": sum(e["certainty"] == k for e in edges)} for k in CERTAINTIES}, "certainty_counts")
    _fixed(row["limitations"], list(LIMITATIONS), "limitations")
    json_bytes(row)
    return copy.deepcopy(row)


PROJECTION_FILE_FIELDS = (
    "source_file_reference", "entrypoint_reference", "root_id", "pinned_commit", "path", "observed_byte_size",
    "observed_sha256", "read_status", "lexical_status", "phase24_source_reference", "phase24_catalog_status",
    "phase24_identity_status", "component_source_status", "referencing_component_ids", "source_inventory_status",
    "phase28_target_reference", "component_ownership_status", "phase28_proposal_references", "graph_node_reference",
)
PROJECTION_REFERENCE_FIELDS = (
    "reference_id", "source_file_reference", "reference_kind", "graph_node_reference", "condition_status",
    "evaluation_status", "has_explicit_literal_path", "binding_status", "bound_source_file_reference",
    "candidate_source_file_references", "unresolved_reason_codes", "graph_edge_references",
)
COVERAGE_COUNT_FIELDS = (
    "source_file_count", "entrypoint_source_file_count", "present_and_hashed_source_file_count", "missing_source_file_count",
    "source_reference_count", "external_module_reference_count", "inline_module_reference_count", "explicit_literal_reference_count",
    "bound_reference_count", "unresolved_reference_count", "conditional_reference_count", "phase28_unapplied_delta_count",
    "global_f_catalog_count", "component_referenced_file_count", "files_not_in_global_f_catalog_count", "files_with_identity_mismatch_count",
    "source_dependency_record_count", "source_ambiguous_dependency_record_count", "source_definite_owner_count",
)
LICENSE_BOUNDARY_FIELDS = (
    "source_license_record_count", "base_unknown_license_count", "evidence_present_record_count",
    "missing_evidence_record_count", "human_review_required_record_count", "source_blocker_count",
)


def validate_coverage(value: object) -> dict:
    row = _common(value, COVERAGE_SCHEMA, ("source_files", "reference_coverage", "phase28_entrypoints", "phase28_deltas",
                                          "counts", "license_boundary_counts", "limitations"))
    files = _array(row["source_files"], MAX_SOURCE_FILES, "projection_files", 1)
    refs = _array(row["reference_coverage"], MAX_REFERENCES, "projection_references")
    entries = _entrypoints(row["phase28_entrypoints"])
    deltas = _parent_deltas(row["phase28_deltas"], entries)
    for f in files:
        closed(f, PROJECTION_FILE_FIELDS, "projection_file_fields")
        _rsf(f["source_file_reference"])
        if f["entrypoint_reference"] is not None:
            _epf(f["entrypoint_reference"])
        _fixed(f["root_id"], "termivar", "projection_source_root")
        _pin(f["pinned_commit"])
        _fixed(f["pinned_commit"], row["source_reference"]["source_commits"][f["root_id"]], "projection_source_pin")
        relative_path(f["path"], "projection_path")
        status = _enum(f["read_status"], ("present_and_hashed", "declared_file_missing"), "projection_read_status")
        if status == "present_and_hashed":
            integer(f["observed_byte_size"], "projection_source_bytes", MAX_SOURCE_BYTES)
            sha256(f["observed_sha256"], "projection_source_hash")
            _enum(f["lexical_status"], LEXICAL_STATUSES, "projection_lexical_status")
        else:
            _fixed(f["observed_byte_size"], None, "missing_source_bytes")
            _fixed(f["observed_sha256"], None, "missing_source_hash")
            _fixed(f["lexical_status"], "not_performed", "missing_source_scan")
        if f["phase24_source_reference"] is not None:
            if type(f["phase24_source_reference"]) is not str or re.fullmatch(r"F[0-9]{4}", f["phase24_source_reference"]) is None:
                _fail("projection_f_reference")
        _enum(f["phase24_catalog_status"], ("listed_in_global_f_catalog", "not_listed_in_global_f_catalog"), "projection_catalog_status")
        _fixed(f["phase24_catalog_status"], "listed_in_global_f_catalog" if f["phase24_source_reference"] is not None else "not_listed_in_global_f_catalog", "projection_catalog_reference")
        _enum(f["phase24_identity_status"], ("matched", "mismatch", "not_compared", "not_in_catalog"), "projection_identity_status")
        _enum(f["component_source_status"], ("referenced_by_component", "not_referenced_by_component"), "projection_component_status")
        component_ids = _ids(f["referencing_component_ids"], 64, "projection_component_references")
        _fixed(f["component_source_status"], "referenced_by_component" if component_ids else "not_referenced_by_component", "projection_component_relation")
        _enum(f["source_inventory_status"], ("source_present_inventory_gap", "catalog_identity_matched", "source_identity_mismatch", "catalog_identity_not_compared", "source_read_not_performed"), "projection_inventory_status")
        _digest_id(f["phase28_target_reference"], "target-", "projection_target", nullable=True)
        _fixed(f["component_ownership_status"], "component_ownership_unresolved", "projection_component_ownership")
        proposals = _ids(f["phase28_proposal_references"], 64, "projection_proposals")
        for proposal in proposals:
            _digest_id(proposal, "proposal-", "projection_proposal")
            if proposal not in {d["proposal_reference"] for d in deltas}:
                _fail("projection_proposal_reference")
        _digest_id(f["graph_node_reference"], "node-", "projection_source_node")
    _unique([f["source_file_reference"] for f in files], "projection_source_ids")
    _unique([(f["root_id"], f["pinned_commit"], f["path"]) for f in files], "projection_source_paths")
    by_source = {f["source_file_reference"]: f for f in files}
    for e in entries:
        f = by_source.get(e["source_file_reference"])
        if f is None or any(e[k] != f[k] for k in ("root_id", "pinned_commit", "path", "entrypoint_reference")) or f["phase28_target_reference"] != e["target_reference"]:
            _fail("projection_entrypoint")
        if f["read_status"] == "present_and_hashed" and (f["observed_byte_size"] != e["bytes"] or f["observed_sha256"] != e["sha256"]):
            _fail("projection_entrypoint_hash")
    for r in refs:
        closed(r, PROJECTION_REFERENCE_FIELDS, "projection_reference_fields")
        _digest_id(r["reference_id"], "rust-ref-", "projection_reference_id")
        if r["source_file_reference"] not in by_source:
            _fail("projection_reference_source")
        _enum(r["reference_kind"], REFERENCE_KINDS, "projection_reference_kind")
        _digest_id(r["graph_node_reference"], "node-", "projection_reference_node")
        _enum(r["condition_status"], ("condition_declared_evaluation_not_performed", "not_declared"), "projection_condition_status")
        _fixed(r["evaluation_status"], "not_performed", "projection_condition_evaluation")
        if type(r["has_explicit_literal_path"]) is not bool:
            _fail("projection_literal_flag")
        _enum(r["binding_status"], BINDING_STATUSES, "projection_binding_status")
        bound = _rsf(r["bound_source_file_reference"], "projection_bound_source", nullable=True)
        candidates = _ids(r["candidate_source_file_references"], MAX_SOURCE_FILES, "projection_candidates")
        if any(x not in by_source for x in candidates) or bound is not None and bound not in candidates:
            _fail("projection_candidate_reference")
        if r["binding_status"] == "bound_to_observed_file":
            if bound is None or by_source[bound]["read_status"] != "present_and_hashed" or not r["has_explicit_literal_path"]:
                _fail("projection_bound_file")
        elif bound is not None:
            _fail("projection_unresolved_bound_file")
        _codes(r["unresolved_reason_codes"], BINDING_REASON_CODES, "projection_unresolved_reasons")
        edges = _ids(r["graph_edge_references"], MAX_EDGES, "projection_edge_references")
        for key in edges:
            _digest_id(key, "edge-", "projection_edge_id")
    _unique([r["reference_id"] for r in refs], "projection_reference_ids")
    counts = closed(row["counts"], COVERAGE_COUNT_FIELDS, "coverage_counts")
    for key in COVERAGE_COUNT_FIELDS:
        integer(counts[key], "coverage_count", MAX_EDGES)
    expected = {
        "source_file_count": len(files), "entrypoint_source_file_count": len(entries),
        "present_and_hashed_source_file_count": sum(f["read_status"] == "present_and_hashed" for f in files),
        "missing_source_file_count": sum(f["read_status"] == "declared_file_missing" for f in files),
        "source_reference_count": len(refs),
        "external_module_reference_count": sum(r["reference_kind"] == "external_module_declaration" for r in refs),
        "inline_module_reference_count": sum(r["reference_kind"] == "inline_module_declaration" for r in refs),
        "explicit_literal_reference_count": sum(r["reference_kind"] in ("explicit_path_module_declaration", "literal_include_reference") and r["has_explicit_literal_path"] for r in refs),
        "bound_reference_count": sum(r["binding_status"] == "bound_to_observed_file" for r in refs),
        "unresolved_reference_count": sum(r["binding_status"] not in ("inline_not_external", "bound_to_observed_file") for r in refs),
        "conditional_reference_count": sum(r["condition_status"] != "not_declared" for r in refs),
        "phase28_unapplied_delta_count": len(deltas),
        "files_not_in_global_f_catalog_count": sum(f["phase24_catalog_status"] == "not_listed_in_global_f_catalog" for f in files),
        "files_with_identity_mismatch_count": sum(f["phase24_identity_status"] == "mismatch" for f in files),
    }
    for key, count in expected.items():
        _fixed(counts[key], count, "coverage_derived_count")
    if counts["component_referenced_file_count"] > counts["global_f_catalog_count"] or counts["source_ambiguous_dependency_record_count"] > counts["source_dependency_record_count"]:
        _fail("coverage_parent_count_bounds")
    boundary = closed(row["license_boundary_counts"], LICENSE_BOUNDARY_FIELDS, "license_boundary_fields")
    for key in LICENSE_BOUNDARY_FIELDS:
        integer(boundary[key], "license_boundary_count", MAX_EDGES * 9)
    total = boundary["source_license_record_count"]
    if (any(boundary[k] > total for k in LICENSE_BOUNDARY_FIELDS[1:-1])
            or boundary["evidence_present_record_count"] + boundary["missing_evidence_record_count"] > total):
        _fail("license_boundary_totals")
    _fixed(row["limitations"], list(LIMITATIONS), "limitations")
    json_bytes(row)
    return copy.deepcopy(row)


def validate_documents(ledger: object, graph: object, coverage: object) -> None:
    """Check only recorded metadata and pure projections; never relex Rust."""
    l = validate_ledger(ledger)
    g = validate_graph(graph)
    c = validate_coverage(coverage)
    if not l["source_reference"] == g["source_reference"] == c["source_reference"]:
        _fail("document_source_reference")
    from .source_file_binding import rebuild_ledger
    from .module_evidence_graph import build_graph
    from .coverage_projection import build_projection

    if l != rebuild_ledger(l):
        _fail("ledger_reprojection")
    expected_graph = build_graph(l)
    if g != expected_graph:
        _fail("graph_reprojection")
    if c != build_projection(l, expected_graph):
        _fail("coverage_reprojection")
