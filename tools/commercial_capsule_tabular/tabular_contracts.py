"""Closed tabular views of recorded capsule metadata; no evaluator or I/O."""
from __future__ import annotations

import copy

from capsule_contracts import (
    InputError, FALSE_FLAGS, PROJECTION_FIELDS, RESULT_LIMITATIONS,
    closed, integer, sha256, reference_ids, digest_id, fixed,
    parse_json, json_bytes, validate_projection,
)
from derivation_contracts import validate_identity

SCOPE_SCHEMA = "termivar-offline-capsule-tabular-scope/v1"
DATASET_SCHEMA = "termivar-offline-capsule-tabular-dataset/v1"
MANIFEST_SCHEMA = "termivar-offline-capsule-tabular-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-capsule-tabular-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — TABULAR DISCLOSURE ONLY — NO CURRENT SOURCE VERIFICATION"
MAX_SCOPE_BYTES = 32 * 1024
MAX_SOURCE_ZIP_BYTES = 256 * 1024
MAX_DATASET_BYTES = MAX_CSV_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
MAX_CELL_BYTES = 4096
MAX_ROW_BYTES = 65536
REFERENCE_FIELDS = REF_HEADERS = ("reference_id", "disclosure_status", "projection_count", "interpretation_limitations")
PROJECTION_HEADERS = PROJECTION_FIELDS
SCOPE_FIELDS = ("schema_version", "mode", "source_capsule_sha256", "export_reference_ids", "export_constraints")
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", *FALSE_FLAGS)
EXPORT_CONSTRAINTS = {
    "max_source_zip_bytes": MAX_SOURCE_ZIP_BYTES,
    "max_dataset_bytes": MAX_DATASET_BYTES,
    "max_csv_bytes": MAX_CSV_BYTES,
    "max_summary_bytes": MAX_SUMMARY_BYTES,
    "max_reference_records": 8,
    "max_projection_records": 64,
    "max_cell_bytes": MAX_CELL_BYTES,
    "max_row_bytes": MAX_ROW_BYTES,
    "max_total_input_bytes": MAX_TOTAL_INPUT_BYTES,
}
CSV_ENCODING = {
    "cell_prefix": "j:", "payload_format": "canonical_compact_ASCII_JSON",
    "cell_types": "string_integer_null_or_string_array",
    "null_encoding": "j:null", "empty_string_encoding": 'j:""', "zero_encoding": "j:0",
    "collection_encoding": "JSON_string_array", "value_source": "typed_dataset_JSON",
    "header_encoding": "plain_fixed_column_names", "delimiter": ",", "quoting": "all",
    "line_ending": "LF", "utf8_bom": False,
    "max_cell_bytes": MAX_CELL_BYTES, "max_row_bytes": MAX_ROW_BYTES,
}
GLOBAL_LIMITATIONS = (
    "recorded_capsule_metadata_only", "source_files_not_reobserved",
    "reference_context_not_revalidated", "upstream_guard_not_independently_verified",
    "CSV_encoding_is_not_source_value", "no_spreadsheet_import_acceptance",
    "no_producer_authority_ownership_or_release_proof", "minimization_is_not_anonymization",
)


def fail(code: str) -> None:
    raise InputError("capsule_tabular_invalid_" + code)


def validate_scope(value: object) -> dict:
    json_bytes(value, maximum=MAX_SCOPE_BYTES)
    row = closed(value, SCOPE_FIELDS, "tabular_scope_fields")
    fixed(row["schema_version"], SCOPE_SCHEMA, "tabular_scope_schema")
    fixed(row["mode"], "demo", "tabular_mode")
    sha256(row["source_capsule_sha256"], "tabular_source_sha256")
    reference_ids(row["export_reference_ids"])
    fixed(row["export_constraints"], EXPORT_CONSTRAINTS, "tabular_export_constraints")
    return copy.deepcopy(row)


def make_scope(source_sha256: str, ids: list) -> dict:
    return validate_scope({"schema_version": SCOPE_SCHEMA, "mode": "demo",
                           "source_capsule_sha256": source_sha256,
                           "export_reference_ids": copy.deepcopy(ids),
                           "export_constraints": copy.deepcopy(EXPORT_CONSTRAINTS)})


def common(schema: str) -> dict:
    if schema not in (DATASET_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            **{flag: False for flag in FALSE_FLAGS}}


def validate_reference_record(value: object) -> dict:
    row = closed(value, REFERENCE_FIELDS, "reference_record_fields")
    digest_id(row["reference_id"], "rust-ref-", "tabular_reference_id")
    status = row["disclosure_status"]
    if type(status) is not str or status not in RESULT_LIMITATIONS:
        fail("disclosure_status")
    count = integer(row["projection_count"], "reference_projection_count", 64)
    if (status == "provided_limited_metadata" and count == 0) or (status != "provided_limited_metadata" and count != 0):
        fail("whole_reference_disclosure")
    fixed(row["interpretation_limitations"], list(RESULT_LIMITATIONS[status]), "reference_limitations")
    return copy.deepcopy(row)


def dataset_counts(references: list, projections: list) -> dict:
    return {
        "requested_reference_count": len(references),
        "provided_reference_count": sum(r["disclosure_status"] == "provided_limited_metadata" for r in references),
        "withheld_reference_count": sum(r["disclosure_status"] == "withheld_by_existing_guard" for r in references),
        "unavailable_reference_count": sum(r["disclosure_status"] == "unavailable_in_existing_scope" for r in references),
        "projection_count": len(projections),
        "unique_candidate_count": len({p["candidate_id"] for p in projections}),
        "unique_file_count": len({p["file_id"] for p in projections}),
        "present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
        "absence_projection_count": sum(p["source_file_presence"] == "missing" for p in projections),
    }


def validate_dataset(value: object) -> dict:
    json_bytes(value, maximum=MAX_DATASET_BYTES)
    row = closed(value, (*COMMON_FIELDS, "scope", "source_capsule", "reference_records", "projection_records",
                         "counts", "csv_encoding", "limitations"), "tabular_dataset_fields")
    fixed({k: row[k] for k in COMMON_FIELDS}, common(DATASET_SCHEMA), "tabular_dataset_common")
    scope = validate_scope(row["scope"])
    source = validate_identity(row["source_capsule"])
    fixed(source["sha256"], scope["source_capsule_sha256"], "tabular_source_binding")
    references, projections = row["reference_records"], row["projection_records"]
    if type(references) is not list or not 1 <= len(references) <= 8:
        fail("reference_records")
    if type(projections) is not list or len(projections) > 64:
        fail("projection_records")
    for ref in references:
        validate_reference_record(ref)
    fixed([r["reference_id"] for r in references], scope["export_reference_ids"], "reference_order")
    indexed = {r["reference_id"]: r for r in references}
    if len(indexed) != len(references):
        fail("duplicate_reference")
    candidate_ids, by_file, per_reference = [], {}, {ref: 0 for ref in indexed}
    for projection in projections:
        closed(projection, PROJECTION_FIELDS, "tabular_projection_fields")
        ref = digest_id(projection["reference_id"], "rust-ref-", "projection_reference_id")
        if ref not in indexed or indexed[ref]["disclosure_status"] != "provided_limited_metadata":
            fail("projection_disclosure_binding")
        validate_projection(projection, ref)
        per_reference[ref] += 1
        candidate_ids.append(projection["candidate_id"])
        identity = {k: projection[k] for k in PROJECTION_FIELDS if k not in ("reference_id", "candidate_id")}
        if projection["file_id"] in by_file:
            fixed(identity, by_file[projection["file_id"]], "shared_file_metadata")
        by_file[projection["file_id"]] = identity
    if len(set(candidate_ids)) != len(candidate_ids):
        fail("duplicate_projection_candidate")
    for ref in references:
        fixed(ref["projection_count"], per_reference[ref["reference_id"]], "reference_projection_correspondence")
    fixed(row["counts"], dataset_counts(references, projections), "tabular_counts")
    fixed(row["csv_encoding"], CSV_ENCODING, "CSV_encoding_policy")
    fixed(row["limitations"], list(GLOBAL_LIMITATIONS), "tabular_limitations")
    return copy.deepcopy(row)
