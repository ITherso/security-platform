"""Closed portable wire protocol. Standard library only; no upstream imports.

Validating this protocol establishes internal correspondence, never original
source truth, disclosure authority, live freshness or producer identity.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re

REQUEST_SCHEMA = "termivar-offline-guarded-reference-capsule-request/v1"
CAPSULE_SCHEMA = "termivar-offline-guarded-reference-capsule/v1"
LOOKUP_SCHEMA = "termivar-offline-reference-capsule-lookup/v1"
INSPECTION_SCHEMA = "termivar-offline-reference-capsule-inspection/v1"
BINDINGS_SCHEMA = "termivar-offline-reference-capsule-source-bindings/v1"
BUNDLE_MANIFEST_SCHEMA = "termivar-offline-reference-capsule-manifest/v1"
ASSEMBLY_MANIFEST_SCHEMA = "termivar-offline-reference-capsule-assembly-manifest/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION"
FALSE_FLAGS = (
    "source_inventory_updated", "scope_delta_applied", "component_ownership_verified",
    "dependency_closure_verified", "build_verified", "runtime_verified", "producer_verified",
    "human_review_verified", "license_review_completed", "redistribution_authorized",
    "release_authorized", "production_ready", "module_closure_verified",
    "compiler_resolution_verified", "reference_context_revalidated",
    "independent_observation_verified", "source_files_reobserved",
    "upstream_guard_independently_verified",
)
MAX_ZIP_BYTES = 256 * 1024
MAX_MEMBER_BYTES = 128 * 1024
MAX_EXPANDED_BYTES = 256 * 1024
MAX_COMPRESSION_RATIO = 20
MAX_REFERENCES = MAX_LOOKUP_REFERENCES = 8
MAX_PROJECTIONS = 64
MAX_REQUEST_BYTES = 32 * 1024
MAX_TOTAL_INPUT_BYTES = 4 * 1024 * 1024
MAX_NEW_DEPTH = 12
MAX_NEW_NODES = 20_000
MAX_NEW_STRING = 512
INSPECTION_CONSTRAINTS = {
    "max_archive_bytes": MAX_ZIP_BYTES, "max_member_bytes": MAX_MEMBER_BYTES,
    "max_expanded_bytes": MAX_EXPANDED_BYTES, "max_compression_ratio": MAX_COMPRESSION_RATIO,
    "max_references": MAX_REFERENCES, "max_projections": MAX_PROJECTIONS,
    "max_json_depth": MAX_NEW_DEPTH, "max_json_nodes": MAX_NEW_NODES,
    "max_text_chars": MAX_NEW_STRING,
}
SOURCE_SCHEMAS = {
    "response": "termivar-offline-reference-metadata-response/v1",
    "selection": "termivar-offline-reference-metadata-selection/v1",
    "summary": None,
    "manifest": "termivar-offline-reference-metadata-manifest/v1",
}
SOURCE_LIMITS = {"response": 512 * 1024, "selection": 512 * 1024,
                 "summary": 128 * 1024, "manifest": 128 * 1024}
REQUEST_FIELDS = ("schema_version", "mode", "capsule_reference", "source_response_sha256",
                  "source_selection_sha256", "requested_reference_ids", "inspection_constraints")
PROJECTION_FIELDS = ("reference_id", "candidate_id", "file_id", "upstream_projection_kind",
                     "source_file_presence", "observed_byte_size", "observed_sha256",
                     "phase31_current_observation_id", "phase31_comparison_id",
                     "upstream_comparison_status", "interpretation_limitations")
RESULT_FIELDS = ("reference_id", "status", "upstream_reference_decision", "projections", "limitation_codes")
STATUS_FOR_DECISION = {
    "candidate_observations_reobserved": "provided_limited_metadata",
    "candidate_reuse_blocked": "withheld_by_existing_guard",
    "candidate_change_observed": "withheld_by_existing_guard",
    "outside_scope": "unavailable_in_existing_scope",
}
PROJECTION_LIMITATIONS = (
    "recorded_upstream_projection_not_new_observation", "reference_context_not_revalidated",
    "byte_hash_not_physical_identity_or_compiler_proof", "no_future_validity_or_execution_authority",
)
RESULT_LIMITATIONS = {
    "provided_limited_metadata": ("limited_recorded_candidate_metadata", "no_reference_context_or_live_freshness_proof"),
    "withheld_by_existing_guard": ("reference_block_applies_to_all_candidate_projections", "no_partial_reference_disclosure"),
    "unavailable_in_existing_scope": ("reference_not_in_existing_candidate_scope", "no_new_source_discovery"),
}
GLOBAL_LIMITATIONS = (
    "recorded_phase32_wire_metadata_only", "source_files_not_reobserved",
    "upstream_guard_not_independently_verified", "reference_context_not_revalidated",
    "no_current_freshness_or_future_validity", "no_producer_signature_or_attestation",
    "no_authorization_ownership_compiler_or_release_proof", "minimization_is_not_anonymization",
)
COMMON_FIELDS = ("schema_version", "capsule_reference", "source_bindings", "demo_label", "demo_only", *FALSE_FLAGS)


class InputError(ValueError):
    """Fixed error codes only; caller text and raw source content stay private."""


def fail(code: str) -> None:
    raise InputError("reference_capsule_invalid_" + code)


def integer(value: object, code: str, maximum: int = 2**53 - 1) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        fail(code)
    return value


def closed(value: object, fields, code: str) -> dict:
    if type(value) is not dict or set(value) != set(fields):
        fail(code)
    return value


def _tree(value: object) -> None:
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NEW_NODES or depth > MAX_NEW_DEPTH:
            fail("tree_limit")
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    fail("key_type")
                pending.extend(((key, depth + 1), (child, depth + 1)))
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            if len(item) > MAX_NEW_STRING:
                fail("string_limit")
            item.encode("utf-8", "strict")
        elif type(item) is int:
            integer(item, "safe_integer")
        elif item is not None and type(item) is not bool:
            fail("value_type")


def _pairs(pairs: list) -> dict:
    row = {}
    for key, value in pairs:
        if key in row:
            fail("duplicate_key")
        row[key] = value
    return row


def _parse_int(text: str) -> int:
    if len(text) > 16:
        fail("integer_limit")
    return integer(int(text), "safe_integer")


def _reject_number(_text: str):
    fail("non_integer_number")


def parse_json(raw: bytes, maximum: int = MAX_MEMBER_BYTES) -> object:
    integer(maximum, "json_maximum", MAX_MEMBER_BYTES)
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        fail("json_bytes")
    try:
        text = raw.decode("utf-8", "strict")
        if text.startswith("\ufeff"):
            fail("utf8_bom")
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_parse_int,
                           parse_float=_reject_number, parse_constant=_reject_number)
        _tree(value)
        return value
    except InputError:
        raise
    except (UnicodeError, ValueError, RecursionError, TypeError, OverflowError):
        fail("strict_json")


def json_bytes(value: object, maximum: int = MAX_MEMBER_BYTES) -> bytes:
    integer(maximum, "json_maximum", MAX_MEMBER_BYTES)
    try:
        _tree(value)
        raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                          allow_nan=False) + "\n").encode("utf-8", "strict")
    except InputError:
        raise
    except (UnicodeError, ValueError, RecursionError, TypeError, OverflowError):
        fail("json_encoding")
    if len(raw) > maximum:
        fail("json_size")
    return raw


def fixed(value: object, expected: object, code: str) -> None:
    if type(value) is not type(expected) or json_bytes(value) != json_bytes(expected):
        fail(code)


def identifier(value: object, code: str) -> str:
    if type(value) is not str or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value) is None:
        fail(code)
    return value


def sha256(value: object, code: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        fail(code)
    return value


def digest_id(value: object, prefix: str, code: str) -> str:
    if type(value) is not str or not value.startswith(prefix):
        fail(code)
    sha256(value[len(prefix):], code)
    return value


def record_digest(value: object) -> str:
    return hashlib.sha256(json_bytes(value)).hexdigest()


def reference_ids(value: object) -> list:
    if type(value) is not list or not 1 <= len(value) <= MAX_REFERENCES:
        fail("reference_ids")
    for ref in value:
        digest_id(ref, "rust-ref-", "reference_id")
    if len(set(value)) != len(value):
        fail("duplicate_reference")
    return value


def validate_request(value: object) -> dict:
    _tree(value)
    row = closed(value, REQUEST_FIELDS, "request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "request_schema")
    fixed(row["mode"], "demo", "request_mode")
    identifier(row["capsule_reference"], "capsule_reference")
    sha256(row["source_response_sha256"], "response_sha256")
    sha256(row["source_selection_sha256"], "selection_sha256")
    reference_ids(row["requested_reference_ids"])
    fixed(row["inspection_constraints"], INSPECTION_CONSTRAINTS, "inspection_constraints")
    return copy.deepcopy(row)


def make_source_bindings(raw: dict) -> dict:
    closed(raw, SOURCE_SCHEMAS, "source_roles")
    sources = {}
    for role, schema in SOURCE_SCHEMAS.items():
        body = raw[role]
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[role]:
            fail("source_bytes")
        sources[role] = {"schema_version": schema, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    return validate_source_bindings({"snapshot_id": "phase32-artifact-snapshot-" + record_digest(sources), "sources": sources})


def validate_source_bindings(value: object) -> dict:
    row = closed(value, ("snapshot_id", "sources"), "source_bindings")
    sources = closed(row["sources"], SOURCE_SCHEMAS, "source_roles")
    for role, schema in SOURCE_SCHEMAS.items():
        source = closed(sources[role], ("schema_version", "bytes", "sha256"), "source_descriptor")
        fixed(source["schema_version"], schema, "source_schema")
        if integer(source["bytes"], "source_bytes", SOURCE_LIMITS[role]) == 0:
            fail("empty_source")
        sha256(source["sha256"], "source_sha256")
    fixed(row["snapshot_id"], "phase32-artifact-snapshot-" + record_digest(sources), "source_snapshot")
    return copy.deepcopy(row)


def common(schema: str, capsule_reference: str, source_bindings: dict) -> dict:
    if schema not in (CAPSULE_SCHEMA, LOOKUP_SCHEMA, INSPECTION_SCHEMA, BINDINGS_SCHEMA,
                      BUNDLE_MANIFEST_SCHEMA, ASSEMBLY_MANIFEST_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "capsule_reference": identifier(capsule_reference, "capsule_reference"),
            "source_bindings": validate_source_bindings(source_bindings), "demo_label": DEMO_LABEL,
            "demo_only": True, **{flag: False for flag in FALSE_FLAGS}}


def validate_common(value: object, schema: str, fields: tuple) -> dict:
    _tree(value)
    row = closed(value, (*COMMON_FIELDS, *fields), "document_fields")
    fixed({key: row[key] for key in COMMON_FIELDS},
          common(schema, row["capsule_reference"], row["source_bindings"]), "common_fields")
    return row


def validate_projection(value: object, reference_id: str) -> dict:
    row = closed(value, PROJECTION_FIELDS, "projection_fields")
    fixed(row["reference_id"], reference_id, "projection_reference")
    identifier(row["candidate_id"], "candidate_id")
    digest_id(row["file_id"], "candidate-file-", "file_id")
    digest_id(row["phase31_current_observation_id"], "current-observation-", "current_observation_id")
    digest_id(row["phase31_comparison_id"], "observation-comparison-", "comparison_id")
    fixed(row["interpretation_limitations"], list(PROJECTION_LIMITATIONS), "projection_limitations")
    if row["upstream_projection_kind"] == "fresh_candidate_byte_metadata_only":
        fixed(row["source_file_presence"], "present", "presence")
        fixed(row["upstream_comparison_status"], "bytes_reobserved_equal", "comparison")
        integer(row["observed_byte_size"], "observed_bytes", 512 * 1024)
        sha256(row["observed_sha256"], "observed_sha256")
    elif row["upstream_projection_kind"] == "fresh_absence_metadata_only":
        fixed(row["source_file_presence"], "missing", "presence")
        fixed(row["upstream_comparison_status"], "absence_reobserved", "comparison")
        fixed(row["observed_byte_size"], None, "absence_bytes")
        fixed(row["observed_sha256"], None, "absence_sha256")
    else:
        fail("projection_kind")
    return copy.deepcopy(row)


def validate_result(value: object) -> dict:
    row = closed(value, RESULT_FIELDS, "result_fields")
    ref = digest_id(row["reference_id"], "rust-ref-", "reference_id")
    decision = row["upstream_reference_decision"]
    if type(decision) is not str or decision not in STATUS_FOR_DECISION:
        fail("recorded_decision")
    status = STATUS_FOR_DECISION[decision]
    fixed(row["status"], status, "recorded_status")
    fixed(row["limitation_codes"], list(RESULT_LIMITATIONS[status]), "result_limitations")
    rows = row["projections"]
    if type(rows) is not list or len(rows) > MAX_PROJECTIONS:
        fail("projection_count")
    if (status == "provided_limited_metadata" and not rows) or (status != "provided_limited_metadata" and rows):
        fail("whole_reference_disclosure")
    for projection in rows:
        validate_projection(projection, ref)
    return copy.deepcopy(row)


def result_counts(results: list) -> dict:
    projections = [p for row in results for p in row["projections"]]
    return {"requested_reference_count": len(results),
            "provided_reference_count": sum(r["status"] == "provided_limited_metadata" for r in results),
            "withheld_reference_count": sum(r["status"] == "withheld_by_existing_guard" for r in results),
            "unavailable_reference_count": sum(r["status"] == "unavailable_in_existing_scope" for r in results),
            "projection_count": len(projections), "unique_candidate_count": len({p["candidate_id"] for p in projections}),
            "unique_file_count": len({p["file_id"] for p in projections}),
            "present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
            "absence_projection_count": sum(p["source_file_presence"] == "missing" for p in projections)}


def validate_results(results: object, ids: list) -> None:
    if type(results) is not list or len(results) != len(ids):
        fail("results")
    candidates, by_file, total = [], {}, 0
    for expected, result in zip(ids, results):
        row = validate_result(result)
        fixed(row["reference_id"], expected, "result_order")
        for p in row["projections"]:
            total += 1
            if total > MAX_PROJECTIONS:
                fail("total_projections")
            candidates.append(p["candidate_id"])
            identity = {key: p[key] for key in PROJECTION_FIELDS if key not in ("reference_id", "candidate_id")}
            if p["file_id"] in by_file:
                fixed(identity, by_file[p["file_id"]], "shared_file_metadata")
            by_file[p["file_id"]] = identity
    if len(set(candidates)) != len(candidates):
        fail("duplicate_candidate")


def validate_capsule(value: object) -> dict:
    row = validate_common(value, CAPSULE_SCHEMA, ("requested_reference_ids", "results", "counts", "limitations", "inspection_constraints"))
    ids = reference_ids(row["requested_reference_ids"])
    validate_results(row["results"], ids)
    fixed(row["counts"], result_counts(row["results"]), "counts")
    fixed(row["limitations"], list(GLOBAL_LIMITATIONS), "limitations")
    fixed(row["inspection_constraints"], INSPECTION_CONSTRAINTS, "inspection_constraints")
    return copy.deepcopy(row)


def build_lookup(capsule: dict, requested_ids: list) -> dict:
    capsule = validate_capsule(capsule)
    ids = reference_ids(requested_ids)
    indexed = {row["reference_id"]: row for row in capsule["results"]}
    if any(ref not in indexed for ref in ids):
        fail("lookup_reference_not_in_capsule")
    results = [copy.deepcopy(indexed[ref]) for ref in ids]
    return {**common(LOOKUP_SCHEMA, capsule["capsule_reference"], capsule["source_bindings"]),
            "requested_reference_ids": list(ids), "results": results, "counts": result_counts(results),
            "limitations": list(GLOBAL_LIMITATIONS), "lookup_scope": "explicit_capsule_records_only"}
