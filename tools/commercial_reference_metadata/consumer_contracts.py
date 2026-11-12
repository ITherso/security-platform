"""Small closed consumer wire models; no upstream guard or source I/O imports."""
from __future__ import annotations

import copy
import hashlib
import re

from commercial_composition.composition_contracts import (
    InputError, closed, integer, identifier, sha256,
    parse_json as _parse_json, json_bytes as _json_bytes,
)

REQUEST_SCHEMA = "termivar-offline-reference-metadata-request/v1"
RESPONSE_SCHEMA = "termivar-offline-reference-metadata-response/v1"
SELECTION_SCHEMA = "termivar-offline-reference-metadata-selection/v1"
MANIFEST_SCHEMA = "termivar-offline-reference-metadata-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-reference-metadata-inspection/v1"
DEMO_LABEL = "DEMONSTRATION ONLY — GUARDED REFERENCE METADATA — NO NEW SOURCE OBSERVATION"
FALSE_FLAGS = (
    "source_inventory_updated", "scope_delta_applied", "component_ownership_verified", "dependency_closure_verified",
    "build_verified", "runtime_verified", "producer_verified", "human_review_verified", "license_review_completed",
    "redistribution_authorized", "release_authorized", "production_ready", "module_closure_verified",
    "compiler_resolution_verified", "reference_context_revalidated", "independent_observation_verified", "source_files_reobserved",
)
COMMON_FIELDS = ("schema_version", "source_reference", "demo_label", "demo_only", *FALSE_FLAGS)
UPSTREAM_SCHEMAS = {
    "ledger": "termivar-offline-candidate-revalidation/v1", "reuse": "termivar-offline-candidate-evidence-reuse/v1",
    "summary": None, "manifest": "termivar-offline-candidate-revalidation-manifest/v1",
}
MAX_REQUEST_BYTES = 32 * 1024
MAX_JSON_BYTES = 512 * 1024
MAX_SUMMARY_BYTES = 128 * 1024
MAX_MANIFEST_BYTES = 128 * 1024
MAX_UPSTREAM_JSON_BYTES = 1024 * 1024
MAX_UPSTREAM_SUMMARY_BYTES = 256 * 1024
MAX_TOTAL_INPUT_BYTES = 4 * 1024 * 1024
MAX_NEW_DEPTH = 12
MAX_NEW_NODES = 20_000
MAX_NEW_STRING = 512
MAX_REFERENCES = 8
MAX_PROJECTIONS_PER_REFERENCE = 2
REQUEST_FIELDS = ("schema_version", "mode", "request_id", "expected_ledger_sha256", "expected_reuse_sha256", "reference_ids")
PROJECTION_FIELDS = ("reference_id", "candidate_id", "file_id", "upstream_projection_kind", "source_file_presence",
                     "observed_byte_size", "observed_sha256", "phase31_current_observation_id", "phase31_comparison_id",
                     "upstream_comparison_status", "interpretation_limitations")
RESULT_FIELDS = ("reference_id", "status", "upstream_reference_decision", "projections", "limitation_codes")
SELECTION_FIELDS = ("reference_id", "upstream_reference_decision", "response_status", "provided_projection_count", "limitation_codes")
STATUS_FOR_DECISION = {
    "candidate_observations_reobserved": "provided_limited_metadata",
    "candidate_reuse_blocked": "withheld_by_existing_guard",
    "candidate_change_observed": "withheld_by_existing_guard",
    "outside_scope": "unavailable_in_existing_scope",
}
GLOBAL_LIMITATIONS = (
    "recorded_upstream_metadata_only", "source_files_not_reobserved", "reference_context_not_revalidated",
    "independent_observation_not_verified", "upstream_fresh_code_does_not_mean_fresh_now",
    "no_physical_identity_or_compiler_proof", "no_authorization_ownership_or_release_proof",
    "data_minimization_is_not_anonymization",
)
PROJECTION_LIMITATIONS = (
    "recorded_upstream_projection_not_new_observation", "reference_context_not_revalidated",
    "byte_hash_not_physical_identity_or_compiler_proof", "no_future_validity_or_execution_authority",
)
RESULT_LIMITATIONS = {
    "provided_limited_metadata": ("limited_recorded_candidate_metadata", "no_reference_context_or_live_freshness_proof"),
    "withheld_by_existing_guard": ("reference_block_applies_to_all_candidate_projections", "no_partial_reference_disclosure"),
    "unavailable_in_existing_scope": ("reference_not_in_existing_candidate_scope", "no_new_source_discovery"),
}
RESPONSE_COUNT_FIELDS = ("requested_reference_count", "provided_reference_count", "withheld_reference_count",
                         "unavailable_reference_count", "projection_count", "unique_candidate_count", "unique_file_count",
                         "present_projection_count", "absence_projection_count")


def fail(code: str) -> None:
    raise InputError("reference_metadata_invalid_" + code)


def _tree(value: object) -> None:
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NEW_NODES or depth > MAX_NEW_DEPTH:
            fail("new_model_tree_limit")
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    fail("new_model_key")
                pending.extend(((key, depth + 1), (child, depth + 1)))
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            if len(item) > MAX_NEW_STRING:
                fail("new_model_string")
            item.encode("utf-8", "strict")
        elif type(item) is int:
            integer(item, "safe_integer")
        elif item is not None and type(item) is not bool:
            fail("new_model_type")


def parse_json(raw: bytes, maximum: int = MAX_JSON_BYTES) -> object:
    integer(maximum, "json_limit", MAX_JSON_BYTES)
    value = _parse_json(raw, maximum=maximum)
    _tree(value)
    return value


def json_bytes(value: object, maximum: int = MAX_JSON_BYTES) -> bytes:
    integer(maximum, "json_limit", MAX_JSON_BYTES)
    _tree(value)
    return _json_bytes(value, maximum=maximum)


def fixed(value: object, expected: object, code: str) -> None:
    if type(value) is not type(expected) or json_bytes(value) != json_bytes(expected):
        fail(code)


def array(value: object, maximum: int, code: str, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        fail(code)
    return value


def unique(values: list, code: str) -> None:
    if len(set(values)) != len(values):
        fail(code)


def digest_id(value: object, prefix: str, code: str) -> str:
    if type(value) is not str or not value.startswith(prefix):
        fail(code)
    sha256(value[len(prefix):], code)
    return value


def record_digest(value: object) -> str:
    return hashlib.sha256(json_bytes(value)).hexdigest()


def validate_request(value: object) -> dict:
    _tree(value)
    request = closed(value, REQUEST_FIELDS, "request_fields")
    fixed(request["schema_version"], REQUEST_SCHEMA, "request_schema")
    fixed(request["mode"], "demo", "request_mode")
    identifier(request["request_id"], "request_id")
    for key in ("expected_ledger_sha256", "expected_reuse_sha256"):
        sha256(request[key], key)
    ids = array(request["reference_ids"], MAX_REFERENCES, "reference_ids", 1)
    for ref in ids:
        digest_id(ref, "rust-ref-", "reference_id")
    unique(ids, "duplicate_reference")
    return copy.deepcopy(request)


def make_source_reference(raw: dict) -> dict:
    closed(raw, UPSTREAM_SCHEMAS, "upstream_roles")
    sources = {}
    for role, schema in UPSTREAM_SCHEMAS.items():
        maximum = MAX_MANIFEST_BYTES if role == "manifest" else MAX_UPSTREAM_SUMMARY_BYTES if role == "summary" else MAX_UPSTREAM_JSON_BYTES
        body = raw[role]
        if type(body) is not bytes or not 0 < len(body) <= maximum:
            fail("upstream_bytes")
        sources[role] = {"schema_version": schema, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    return validate_source_reference({"snapshot_id": "phase31-metadata-snapshot-" + record_digest(sources), "upstream_sources": sources})


def validate_source_reference(value: object) -> dict:
    ref = closed(value, ("snapshot_id", "upstream_sources"), "source_reference")
    sources = closed(ref["upstream_sources"], UPSTREAM_SCHEMAS, "upstream_sources")
    total = 0
    for role, schema in UPSTREAM_SCHEMAS.items():
        row = closed(sources[role], ("schema_version", "bytes", "sha256"), "source_descriptor")
        fixed(row["schema_version"], schema, "upstream_schema")
        maximum = MAX_MANIFEST_BYTES if role == "manifest" else MAX_UPSTREAM_SUMMARY_BYTES if role == "summary" else MAX_UPSTREAM_JSON_BYTES
        size = integer(row["bytes"], "source_bytes", maximum)
        if size == 0:
            fail("empty_source")
        total += size
        sha256(row["sha256"], "source_sha256")
    if total > MAX_TOTAL_INPUT_BYTES:
        fail("total_input_bytes")
    fixed(ref["snapshot_id"], "phase31-metadata-snapshot-" + record_digest(sources), "snapshot_id")
    return copy.deepcopy(ref)


def common(schema: str, reference: dict) -> dict:
    if schema not in (RESPONSE_SCHEMA, SELECTION_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "source_reference": validate_source_reference(reference),
            "demo_label": DEMO_LABEL, "demo_only": True, **{flag: False for flag in FALSE_FLAGS}}


def validate_common(value: object, schema: str, fields: tuple) -> dict:
    _tree(value)
    row = closed(value, (*COMMON_FIELDS, *fields), "document_fields")
    fixed(row["schema_version"], schema, "schema")
    validate_source_reference(row["source_reference"])
    fixed(row["demo_label"], DEMO_LABEL, "demo_label")
    fixed(row["demo_only"], True, "demo_only")
    for flag in FALSE_FLAGS:
        fixed(row[flag], False, "trust_flag")
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
        fixed(row["source_file_presence"], "present", "projection_presence")
        fixed(row["upstream_comparison_status"], "bytes_reobserved_equal", "projection_comparison")
        integer(row["observed_byte_size"], "observed_bytes", 512 * 1024)
        sha256(row["observed_sha256"], "observed_sha256")
    elif row["upstream_projection_kind"] == "fresh_absence_metadata_only":
        fixed(row["source_file_presence"], "missing", "projection_presence")
        fixed(row["upstream_comparison_status"], "absence_reobserved", "projection_comparison")
        fixed(row["observed_byte_size"], None, "absence_bytes")
        fixed(row["observed_sha256"], None, "absence_hash")
    else:
        fail("upstream_projection_kind")
    return copy.deepcopy(row)


def response_counts(results: list) -> dict:
    projections = [p for r in results for p in r["projections"]]
    return {"requested_reference_count": len(results),
            "provided_reference_count": sum(r["status"] == "provided_limited_metadata" for r in results),
            "withheld_reference_count": sum(r["status"] == "withheld_by_existing_guard" for r in results),
            "unavailable_reference_count": sum(r["status"] == "unavailable_in_existing_scope" for r in results),
            "projection_count": len(projections), "unique_candidate_count": len({p["candidate_id"] for p in projections}),
            "unique_file_count": len({p["file_id"] for p in projections}),
            "present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
            "absence_projection_count": sum(p["source_file_presence"] == "missing" for p in projections)}


def validate_response(value: object) -> dict:
    response = validate_common(value, RESPONSE_SCHEMA, ("request_id", "results", "counts", "limitations"))
    identifier(response["request_id"], "request_id")
    results = array(response["results"], MAX_REFERENCES, "results", 1)
    ids, candidate_ids, by_file = [], [], {}
    for result in results:
        closed(result, RESULT_FIELDS, "result_fields")
        ref = digest_id(result["reference_id"], "rust-ref-", "reference_id")
        ids.append(ref)
        decision = result["upstream_reference_decision"]
        if type(decision) is not str or decision not in STATUS_FOR_DECISION:
            fail("upstream_reference_decision")
        status = STATUS_FOR_DECISION[decision]
        fixed(result["status"], status, "reference_response_status")
        fixed(result["limitation_codes"], list(RESULT_LIMITATIONS[status]), "result_limitations")
        rows = array(result["projections"], MAX_PROJECTIONS_PER_REFERENCE, "projections", 1 if status == "provided_limited_metadata" else 0)
        if status != "provided_limited_metadata" and rows:
            fail("withheld_or_unavailable_projection")
        for projection in rows:
            validate_projection(projection, ref)
            candidate_ids.append(projection["candidate_id"])
            identity = {key: projection[key] for key in ("upstream_projection_kind", "source_file_presence", "observed_byte_size", "observed_sha256", "phase31_current_observation_id", "phase31_comparison_id", "upstream_comparison_status")}
            if projection["file_id"] in by_file:
                fixed(identity, by_file[projection["file_id"]], "shared_file_identity")
            by_file[projection["file_id"]] = identity
    unique(ids, "duplicate_result_reference")
    unique(candidate_ids, "duplicate_projection_candidate")
    fixed(response["counts"], response_counts(results), "response_counts")
    fixed(response["limitations"], list(GLOBAL_LIMITATIONS), "response_limitations")
    return copy.deepcopy(response)


def build_selection_model(response: dict, request: dict) -> dict:
    response = validate_response(response)
    request = validate_request(request)
    fixed(response["request_id"], request["request_id"], "response_request_id")
    fixed([r["reference_id"] for r in response["results"]], request["reference_ids"], "request_result_order")
    for role in ("ledger", "reuse"):
        fixed(response["source_reference"]["upstream_sources"][role]["sha256"], request["expected_" + role + "_sha256"], "request_source_digest")
    rows = [{"reference_id": r["reference_id"], "upstream_reference_decision": r["upstream_reference_decision"],
             "response_status": r["status"], "provided_projection_count": len(r["projections"]),
             "limitation_codes": copy.deepcopy(r["limitation_codes"])} for r in response["results"]]
    return {**common(SELECTION_SCHEMA, response["source_reference"]), "request": request,
            "selections": rows, "counts": copy.deepcopy(response["counts"]), "limitations": list(GLOBAL_LIMITATIONS)}


def validate_documents(response: object, selection: object) -> None:
    validated = validate_response(response)
    row = validate_common(selection, SELECTION_SCHEMA, ("request", "selections", "counts", "limitations"))
    fixed(row, build_selection_model(validated, row["request"]), "selection_correspondence")
