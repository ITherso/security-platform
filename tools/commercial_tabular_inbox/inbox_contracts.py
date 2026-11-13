"""Closed typed-import models, reusing the owning strict JSON primitives."""
from __future__ import annotations

import copy
import json

from capsule_contracts import (
    InputError, FALSE_FLAGS, PROJECTION_FIELDS, closed, integer, identifier,
    sha256, reference_ids, digest_id, validate_projection,
    _tree, _pairs, _parse_int, _reject_number,
)
from tabular_contracts import (
    DATASET_SCHEMA as SOURCE_DATASET_SCHEMA,
    MANIFEST_SCHEMA as SOURCE_MANIFEST_SCHEMA,
    REF_HEADERS, PROJECTION_HEADERS, validate_reference_record, dataset_counts,
)

REQUEST_SCHEMA = "termivar-offline-tabular-inbox-request/v1"
INBOX_SCHEMA = "termivar-offline-tabular-inbox/v1"
QUERY_SCHEMA = "termivar-offline-tabular-reference-query/v1"
RECEIPT_SCHEMA = "termivar-offline-tabular-import-receipt/v1"
MANIFEST_SCHEMA = "termivar-offline-tabular-inbox-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-tabular-inbox-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — TYPED CSV IMPORT ONLY — NO CURRENT SOURCE VERIFICATION"
MAX_REQUEST_BYTES = 32 * 1024
MAX_INBOX_BYTES = 256 * 1024
MAX_QUERY_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
SOURCE_NAMES = ("tabular-dataset.json", "reference-register.csv", "projection-register.csv",
                "tabular-summary.md", "manifest.json")
SOURCE_LIMITS = dict(zip(SOURCE_NAMES, (131072, 131072, 131072, 131072, 65536)))
CSV_HEADERS = {"reference": list(REF_HEADERS), "projection": list(PROJECTION_HEADERS)}
INBOX_SCOPE = "five_explicit_Phase35_artifacts_canonical_CSV_typed_records_only"
QUERY_SCOPE = "in_memory_imported_reference_metadata_only"
RECEIPT_SCOPE = "recorded_five_artifact_import_relationship_not_independent_source_truth"
LIMITATIONS = (
    "CSV_records_only_not_new_observations", "source_files_not_reobserved",
    "reference_context_not_revalidated", "upstream_guard_not_independently_verified",
    "internal_hashes_not_producer_authentication", "no_second_host_or_spreadsheet_import_acceptance",
    "no_ownership_human_legal_or_release_authority", "minimization_is_not_anonymization",
)
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", *FALSE_FLAGS)
REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "source_manifest_sha256",
                  "requested_reference_ids")


def fail(code: str) -> None:
    raise InputError("tabular_inbox_invalid_" + code)


def _maximum(value: int) -> int:
    if type(value) is not int or not 0 < value <= MAX_INBOX_BYTES:
        fail("JSON_limit")
    return value


def parse_json(raw: bytes, maximum: int = MAX_QUERY_BYTES) -> object:
    """Use unchanged owner hooks/tree with a bounded new-inbox byte ceiling."""
    _maximum(maximum)
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        fail("JSON_bytes")
    try:
        text = raw.decode("utf-8", "strict")
        if text.startswith("\ufeff"):
            fail("JSON_BOM")
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_parse_int,
                           parse_float=_reject_number, parse_constant=_reject_number)
        _tree(value)
        return value
    except InputError:
        raise
    except (UnicodeError, ValueError, RecursionError, TypeError, OverflowError):
        fail("strict_JSON")


def json_bytes(value: object, maximum: int = MAX_QUERY_BYTES) -> bytes:
    _maximum(maximum)
    try:
        _tree(value)
        raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                          allow_nan=False) + "\n").encode("utf-8", "strict")
    except InputError:
        raise
    except (UnicodeError, ValueError, RecursionError, TypeError, OverflowError):
        fail("JSON_encoding")
    if not 0 < len(raw) <= maximum:
        fail("JSON_size")
    return raw


def fixed(value: object, expected: object, code: str) -> None:
    if (type(value) is not type(expected)
            or json_bytes(value, maximum=MAX_INBOX_BYTES) != json_bytes(expected, maximum=MAX_INBOX_BYTES)):
        fail(code)


def common(schema: str) -> dict:
    if schema not in (INBOX_SCHEMA, QUERY_SCHEMA, RECEIPT_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            **{flag: False for flag in FALSE_FLAGS}}


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "inbox_request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "request_schema")
    fixed(row["mode"], "demo", "mode")
    identifier(row["request_reference"], "request_reference")
    sha256(row["source_manifest_sha256"], "source_manifest_sha256")
    reference_ids(row["requested_reference_ids"])
    return copy.deepcopy(row)


def validate_source_artifacts(value: object) -> list:
    if type(value) is not list or len(value) != len(SOURCE_NAMES):
        fail("source_artifacts")
    for record, name in zip(value, SOURCE_NAMES):
        row = closed(record, ("name", "bytes", "sha256"), "source_identity_fields")
        fixed(row["name"], name, "source_identity_name")
        if integer(row["bytes"], "source_identity_bytes", SOURCE_LIMITS[name]) == 0:
            fail("source_identity_empty")
        sha256(row["sha256"], "source_identity_sha256")
    return copy.deepcopy(value)


def validate_records(references: object, projections: object) -> tuple[list, list]:
    """Retain owner field validators and check the new inbox relationships."""
    if type(references) is not list or not 1 <= len(references) <= 8:
        fail("references")
    if type(projections) is not list or len(projections) > 64:
        fail("projections")
    for record in references:
        validate_reference_record(record)
    ids = reference_ids([record["reference_id"] for record in references])
    indexed = {record["reference_id"]: record for record in references}
    candidates, files = set(), {}
    per_ref = {reference: 0 for reference in ids}
    for record in projections:
        closed(record, PROJECTION_FIELDS, "inbox_projection_fields")
        ref = digest_id(record["reference_id"], "rust-ref-", "inbox_projection_reference")
        if ref not in indexed or indexed[ref]["disclosure_status"] != "provided_limited_metadata":
            fail("whole_reference_disclosure")
        validate_projection(record, ref)
        if record["candidate_id"] in candidates:
            fail("duplicate_projection")
        candidates.add(record["candidate_id"])
        per_ref[ref] += 1
        identity = {k: record[k] for k in PROJECTION_FIELDS if k not in ("reference_id", "candidate_id")}
        if record["file_id"] in files:
            fixed(identity, files[record["file_id"]], "shared_file_metadata")
        files[record["file_id"]] = identity
    for ref in references:
        fixed(ref["projection_count"], per_ref[ref["reference_id"]], "reference_projection_count")
    return copy.deepcopy(references), copy.deepcopy(projections)


def _common_row(value: object, schema: str, extra: tuple, maximum: int) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *extra), "inbox_model_fields")
    fixed({k: row[k] for k in COMMON_FIELDS}, common(schema), "inbox_common")
    fixed(row["limitations"], list(LIMITATIONS), "inbox_limitations")
    return row


def validate_inbox(value: object) -> dict:
    row = _common_row(value, INBOX_SCHEMA, ("source_artifacts", "source_dataset_schema",
                      "reference_records", "projection_records", "reference_projection_links",
                      "counts", "import_scope", "limitations"), MAX_INBOX_BYTES)
    validate_source_artifacts(row["source_artifacts"])
    fixed(row["source_dataset_schema"], SOURCE_DATASET_SCHEMA, "inbox_source_schema")
    references, projections = validate_records(row["reference_records"], row["projection_records"])
    links = [{"reference_id": ref["reference_id"],
              "candidate_ids": [p["candidate_id"] for p in projections if p["reference_id"] == ref["reference_id"]]}
             for ref in references]
    fixed(row["reference_projection_links"], links, "inbox_reference_links")
    fixed(row["counts"], dataset_counts(references, projections), "inbox_counts")
    fixed(row["import_scope"], INBOX_SCOPE, "import_scope")
    return copy.deepcopy(row)


def validate_query(value: object) -> dict:
    row = _common_row(value, QUERY_SCHEMA, ("request", "source_manifest", "results", "counts",
                      "query_scope", "limitations"), MAX_QUERY_BYTES)
    request = validate_request(row["request"])
    source = closed(row["source_manifest"], ("name", "bytes", "sha256"), "query_source_manifest")
    fixed(source["name"], "manifest.json", "query_manifest_name")
    if integer(source["bytes"], "query_manifest_bytes", SOURCE_LIMITS["manifest.json"]) == 0:
        fail("query_manifest_empty")
    sha256(source["sha256"], "query_manifest_sha256")
    fixed(source["sha256"], request["source_manifest_sha256"], "query_manifest_binding")
    results = row["results"]
    if type(results) is not list or len(results) != len(request["requested_reference_ids"]):
        fail("query_results")
    references, projections = [], []
    for result in results:
        closed(result, (*REF_HEADERS, "projections"), "query_result_fields")
        reference = {k: result[k] for k in REF_HEADERS}
        refs, projs = validate_records([reference], result["projections"])
        references.extend(refs)
        projections.extend(projs)
    fixed([ref["reference_id"] for ref in references], request["requested_reference_ids"], "query_reference_order")
    validate_records(references, projections)
    fixed(row["counts"], dataset_counts(references, projections), "query_counts")
    fixed(row["query_scope"], QUERY_SCOPE, "query_scope")
    return copy.deepcopy(row)


def validate_receipt(value: object) -> dict:
    row = _common_row(value, RECEIPT_SCHEMA, ("source_artifacts", "source_dataset_schema",
                      "source_manifest_schema", "csv_headers", "csv_rows", "counts",
                      "canonical_CSV_reconciliation", "dataset_CSV_relation", "receipt_scope",
                      "limitations"), MAX_RECEIPT_BYTES)
    validate_source_artifacts(row["source_artifacts"])
    fixed(row["source_dataset_schema"], SOURCE_DATASET_SCHEMA, "receipt_dataset_schema")
    fixed(row["source_manifest_schema"], SOURCE_MANIFEST_SCHEMA, "receipt_manifest_schema")
    fixed(row["csv_headers"], CSV_HEADERS, "receipt_headers")
    counts = closed(row["counts"], tuple(dataset_counts([], [])), "receipt_counts_fields")
    for key, count in counts.items():
        integer(count, "receipt_count", 8 if key.endswith("reference_count") else 64)
    if (not 1 <= counts["requested_reference_count"] <= 8
            or counts["requested_reference_count"] != counts["provided_reference_count"] + counts["withheld_reference_count"] + counts["unavailable_reference_count"]
            or counts["projection_count"] != counts["present_projection_count"] + counts["absence_projection_count"]
            or counts["unique_candidate_count"] != counts["projection_count"]
            or counts["unique_file_count"] > counts["projection_count"]):
        fail("receipt_counts_relation")
    fixed(row["csv_rows"], {"reference_data_rows": counts["requested_reference_count"],
                           "projection_data_rows": counts["projection_count"]}, "receipt_CSV_rows")
    fixed(row["canonical_CSV_reconciliation"], "matched_during_import", "receipt_reconciliation")
    fixed(row["dataset_CSV_relation"], "typed_values_equal_during_import", "receipt_CSV_relation")
    fixed(row["receipt_scope"], RECEIPT_SCOPE, "receipt_scope")
    return copy.deepcopy(row)


def validate_relationships(inbox: object, query: object, receipt: object) -> tuple[dict, dict, dict]:
    inbox, query, receipt = validate_inbox(inbox), validate_query(query), validate_receipt(receipt)
    fixed(receipt["source_artifacts"], inbox["source_artifacts"], "receipt_inbox_source")
    fixed(receipt["counts"], inbox["counts"], "receipt_inbox_counts")
    fixed(query["source_manifest"], inbox["source_artifacts"][-1], "query_inbox_source")
    by_id = {ref["reference_id"]: ref for ref in inbox["reference_records"]}
    expected = []
    for ref in query["request"]["requested_reference_ids"]:
        if ref not in by_id:
            fail("query_unknown_reference")
        expected.append({**by_id[ref], "projections": [p for p in inbox["projection_records"] if p["reference_id"] == ref]})
    fixed(query["results"], expected, "query_inbox_results")
    return inbox, query, receipt
