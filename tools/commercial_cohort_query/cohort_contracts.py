"""Closed cohort/witness wire models over recorded disclosed metadata only."""
from __future__ import annotations

import copy

from co_reference_contracts import (
    InputError, FALSE_FLAGS, parse_json, json_bytes, fixed, closed, integer,
    identifier, sha256, digest_id,
    JOIN_SCHEMA as SOURCE_JOIN_SCHEMA,
    LOOKUP_SCHEMA as SOURCE_LOOKUP_SCHEMA,
    RECEIPT_SCHEMA as SOURCE_RECEIPT_SCHEMA,
    MANIFEST_SCHEMA as SOURCE_MANIFEST_SCHEMA,
    validate_file_ids as source_file_ids,
    validate_source_counts,
    owner_provided_packets,
)
from capsule_contracts import PROJECTION_FIELDS, RESULT_LIMITATIONS

REQUEST_SCHEMA = "termivar-offline-disclosed-cohort-query-request/v1"
QUERY_SCHEMA = "termivar-offline-disclosed-cohort-query/v1"
WITNESSES_SCHEMA = "termivar-offline-disclosed-cohort-witnesses/v1"
RECEIPT_SCHEMA = "termivar-offline-cohort-source-receipt/v1"
MANIFEST_SCHEMA = "termivar-offline-cohort-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-cohort-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — DISCLOSED COHORT MATCH ONLY — NO CURRENT FILE OR SOURCE RELATIONSHIP VERIFIED"
MAX_REQUEST_BYTES = 32 * 1024
MAX_QUERY_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_WITNESSES_BYTES = 256 * 1024
MAX_RECEIPT_BYTES = MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
MAX_REFERENCES = MAX_REQUIRED_FILES = 8
MAX_PROJECTIONS = 64
SOURCE_NAMES = ("co-reference-join.json", "co-reference-lookup.json", "co-reference-source-receipt.json",
                "co-reference-summary.md", "manifest.json")
SOURCE_LIMITS = dict(zip(SOURCE_NAMES, (262144, 131072, 65536, 131072, 65536)))
SOURCE_SCHEMAS = dict(zip(SOURCE_NAMES, (SOURCE_JOIN_SCHEMA, SOURCE_LOOKUP_SCHEMA,
                                      SOURCE_RECEIPT_SCHEMA, None, SOURCE_MANIFEST_SCHEMA)))
SOURCE_SCHEMAS_SOURCE = dict(SOURCE_SCHEMAS)
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "trust_flags")
REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "source_phase38_join_sha256",
                  "source_phase38_manifest_sha256", "required_file_assertions")
COUNT_FIELDS = ("required_file_count", "matched_reference_count", "matched_projection_count",
                "matched_candidate_count", "matched_present_projection_count", "matched_absence_projection_count")
CONTENT_SCOPE = "five_Phase38_artifact_internal_correspondence_only"
LIMITATIONS = (
    "recorded_disclosed_cohort_match_only", "not_current_file_state_or_physical_relationship",
    "not_source_compiler_ownership_or_security_relation", "source_files_not_reobserved",
    "upstream_guard_not_independently_verified", "internal_hashes_not_producer_authentication",
    "no_human_legal_customer_or_release_authority", "minimization_is_not_anonymization",
)


def fail(code: str) -> None:
    raise InputError("cohort_query_invalid_" + code)


def common(schema: str) -> dict:
    if schema not in (QUERY_SCHEMA, WITNESSES_SCHEMA, RECEIPT_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "trust_flags": {flag: False for flag in FALSE_FLAGS}}


def _common_row(value: object, schema: str, fields: tuple, maximum: int) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *fields), "closed_model_fields")
    fixed({key: row[key] for key in COMMON_FIELDS}, common(schema), "common_fields")
    fixed(row["limitations"], list(LIMITATIONS), "limitations")
    return row


def validate_assertions(value: object) -> list:
    if type(value) is not list or not 2 <= len(value) <= MAX_REQUIRED_FILES:
        fail("required_file_assertions")
    ids = []
    for assertion in value:
        row = closed(assertion, ("file_id", "expected_source_file_presence"), "assertion_fields")
        ids.append(row["file_id"])
        # Exact values of the protected projection validator: present/missing.
        # "missing" is recorded absence metadata, never a new filesystem query.
        presence = row["expected_source_file_presence"]
        if type(presence) is not str or presence not in ("present", "missing"):
            fail("source_presence_enum")
    source_file_ids(ids)
    return copy.deepcopy(value)


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "request_schema")
    fixed(row["mode"], "demo", "mode")
    identifier(row["request_reference"], "request_reference")
    sha256(row["source_phase38_join_sha256"], "source_phase38_join_sha256")
    sha256(row["source_phase38_manifest_sha256"], "source_phase38_manifest_sha256")
    validate_assertions(row["required_file_assertions"])
    return copy.deepcopy(row)


def _request_binding(row: dict) -> dict:
    request = validate_request(row["request"])
    for key in ("source_phase38_join_sha256", "source_phase38_manifest_sha256"):
        fixed(row[key], request[key], "actual_Phase38_request_binding")
    return request


def _validate_results(request: dict, results: object) -> list:
    json_bytes(results, maximum=MAX_WITNESSES_BYTES)
    if type(results) is not list or len(results) > MAX_REFERENCES:
        fail("witness_results")
    required_ids = [assertion["file_id"] for assertion in request["required_file_assertions"]]
    packets = []
    for result in results:
        closed(result, ("reference_id", "disclosure_status", "matched_file_ids",
                        "supporting_projection_bindings", "projections"), "witness_result_fields")
        fixed(result["disclosure_status"], "provided_limited_metadata", "provided_witness_only")
        fixed(result["matched_file_ids"], required_ids, "all_required_files_in_request_order")
        if type(result["projections"]) is not list or not 1 <= len(result["projections"]) <= MAX_PROJECTIONS:
            fail("witness_projection_list")
        packets.append({"reference_id": result["reference_id"], "disclosure_status": result["disclosure_status"],
                        "projection_count": len(result["projections"]),
                        "interpretation_limitations": list(RESULT_LIMITATIONS["provided_limited_metadata"]),
                        "projections": result["projections"]})
    # Empty is valid for a no-match result. Otherwise this owning function checks
    # whole reference bindings, all eleven fields, global candidate uniqueness,
    # shared-file consistency and sorted, unique reference IDs.
    packets = owner_provided_packets(packets)
    for result, packet in zip(results, packets):
        for assertion in request["required_file_assertions"]:
            supporting = [p for p in packet["projections"] if p["file_id"] == assertion["file_id"]]
            if not supporting:
                fail("required_file_without_projection")
            states = {p["source_file_presence"] for p in supporting}
            if states != {assertion["expected_source_file_presence"]}:
                fail("recorded_presence_assertion_mismatch_or_conflict")
        triples = [(packet["reference_id"], p["candidate_id"], p["file_id"])
                   for p in packet["projections"] if p["file_id"] in required_ids]
        if len(set(triples)) != len(triples):
            fail("duplicate_supporting_binding")
        expected = [{"reference_id": ref, "candidate_id": candidate, "file_id": file_id}
                    for ref, candidate, file_id in sorted(triples)]
        fixed(result["supporting_projection_bindings"], expected, "all_real_required_projection_bindings")
    return copy.deepcopy(results)


def cohort_counts(request: dict, results: list) -> dict:
    request = validate_request(request)
    results = _validate_results(request, results)
    projections = [p for result in results for p in result["projections"]]
    return {"required_file_count": len(request["required_file_assertions"]),
            "matched_reference_count": len(results),
            "matched_projection_count": len(projections),
            "matched_candidate_count": len({p["candidate_id"] for p in projections}),
            "matched_present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
            "matched_absence_projection_count": sum(p["source_file_presence"] == "missing" for p in projections)}


def validate_query(value: object) -> dict:
    row = _common_row(value, QUERY_SCHEMA, ("source_phase38_join_sha256", "source_phase38_manifest_sha256",
                      "request", "query_status", "matched_reference_ids", "counts", "limitations"), MAX_QUERY_BYTES)
    request = _request_binding(row)
    ids = row["matched_reference_ids"]
    if type(ids) is not list or len(ids) > MAX_REFERENCES:
        fail("matched_reference_ids")
    for ref in ids:
        digest_id(ref, "rust-ref-", "matched_reference_id")
    fixed(ids, sorted(set(ids)), "sorted_unique_matched_references")
    fixed(row["query_status"], "matched_in_disclosed_scope" if ids else "no_match_in_disclosed_scope", "query_status")
    counts = closed(row["counts"], COUNT_FIELDS, "query_count_fields")
    for key in COUNT_FIELDS:
        integer(counts[key], "query_count", 8 if key in ("required_file_count", "matched_reference_count") else 64)
    required = len(request["required_file_assertions"])
    matched = len(ids)
    fixed(counts["required_file_count"], required, "required_file_count")
    fixed(counts["matched_reference_count"], matched, "matched_reference_count")
    expected_present = sum(a["expected_source_file_presence"] == "present" for a in request["required_file_assertions"])
    expected_missing = required - expected_present
    if (counts["matched_candidate_count"] != counts["matched_projection_count"]
            or counts["matched_projection_count"] != counts["matched_present_projection_count"] + counts["matched_absence_projection_count"]
            or counts["matched_projection_count"] < required * matched
            or counts["matched_present_projection_count"] < expected_present * matched
            or counts["matched_absence_projection_count"] < expected_missing * matched
            or (not matched and any(counts[key] for key in COUNT_FIELDS if key != "required_file_count"))):
        fail("query_count_relations")
    return copy.deepcopy(row)


def validate_witnesses(value: object) -> dict:
    row = _common_row(value, WITNESSES_SCHEMA, ("source_phase38_join_sha256", "source_phase38_manifest_sha256",
                      "request", "results", "counts", "limitations"), MAX_WITNESSES_BYTES)
    request = _request_binding(row)
    results = _validate_results(request, row["results"])
    fixed(row["counts"], cohort_counts(request, results), "witness_whole_packet_counts")
    return copy.deepcopy(row)


def query_from_witnesses(witnesses: dict) -> dict:
    witnesses = validate_witnesses(witnesses)
    ids = [result["reference_id"] for result in witnesses["results"]]
    return validate_query({
        **common(QUERY_SCHEMA),
        "source_phase38_join_sha256": witnesses["source_phase38_join_sha256"],
        "source_phase38_manifest_sha256": witnesses["source_phase38_manifest_sha256"],
        "request": copy.deepcopy(witnesses["request"]),
        "query_status": "matched_in_disclosed_scope" if ids else "no_match_in_disclosed_scope",
        "matched_reference_ids": ids, "counts": copy.deepcopy(witnesses["counts"]),
        "limitations": list(LIMITATIONS),
    })


def validate_source_artifacts(value: object) -> list:
    if type(value) is not list or len(value) != len(SOURCE_NAMES):
        fail("five_actual_Phase38_sources")
    for item, name in zip(value, SOURCE_NAMES):
        row = closed(item, ("name", "bytes", "sha256", "schema_version"), "source_artifact_fields")
        fixed(row["name"], name, "source_artifact_name")
        fixed(row["schema_version"], SOURCE_SCHEMAS[name], "source_artifact_schema")
        if integer(row["bytes"], "source_artifact_bytes", SOURCE_LIMITS[name]) == 0:
            fail("empty_source_artifact")
        sha256(row["sha256"], "source_artifact_sha256")
    return copy.deepcopy(value)


def validate_receipt(value: object) -> dict:
    row = _common_row(value, RECEIPT_SCHEMA, ("source_artifacts", "source_phase38_join_sha256",
                      "source_phase38_manifest_sha256", "source_schema_versions", "source_counts",
                      "content_scope", "limitations"), MAX_RECEIPT_BYTES)
    artifacts = validate_source_artifacts(row["source_artifacts"])
    fixed(row["source_phase38_join_sha256"], artifacts[0]["sha256"], "actual_Phase38_join_identity")
    fixed(row["source_phase38_manifest_sha256"], artifacts[-1]["sha256"], "actual_Phase38_manifest_identity")
    fixed(row["source_schema_versions"], SOURCE_SCHEMAS_SOURCE, "source_schema_versions")
    validate_source_counts(row["source_counts"])
    fixed(row["content_scope"], CONTENT_SCOPE, "source_content_scope")
    return copy.deepcopy(row)


def make_source_receipt(source_artifacts: list, source_counts: dict) -> dict:
    artifacts = validate_source_artifacts(source_artifacts)
    counts = validate_source_counts(source_counts)
    return validate_receipt({
        **common(RECEIPT_SCHEMA), "source_artifacts": artifacts,
        "source_phase38_join_sha256": artifacts[0]["sha256"],
        "source_phase38_manifest_sha256": artifacts[-1]["sha256"],
        "source_schema_versions": dict(SOURCE_SCHEMAS_SOURCE), "source_counts": counts,
        "content_scope": CONTENT_SCOPE, "limitations": list(LIMITATIONS),
    })


def validate_relationships(query: object, witnesses: object, receipt: object) -> tuple[dict, dict, dict]:
    query, witnesses, receipt = validate_query(query), validate_witnesses(witnesses), validate_receipt(receipt)
    fixed(query, query_from_witnesses(witnesses), "query_witness_correspondence")
    for key in ("source_phase38_join_sha256", "source_phase38_manifest_sha256"):
        fixed(query[key], receipt[key], "actual_Phase38_source_relation")
    counts, visible = query["counts"], receipt["source_counts"]
    mappings = {"matched_reference_count": "reference_count", "matched_projection_count": "projection_count",
                "matched_candidate_count": "candidate_count", "matched_present_projection_count": "present_projection_count",
                "matched_absence_projection_count": "absence_projection_count"}
    files = {p["file_id"] for result in witnesses["results"] for p in result["projections"]}
    if any(counts[key] > visible[target] for key, target in mappings.items()) or len(files) > visible["file_count"]:
        fail("matched_disclosure_exceeds_inherited_visible_counts")
    return query, witnesses, receipt
