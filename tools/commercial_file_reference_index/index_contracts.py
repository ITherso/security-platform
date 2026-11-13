"""Closed disclosed-file relationships over recorded typed inbox metadata.

No source reader, guard or evaluator lives here. Validation establishes only
new-output correspondence, never independent source or producer authority.
"""
from __future__ import annotations

import copy

from inbox_contracts import (
    InputError, FALSE_FLAGS, PROJECTION_FIELDS, CSV_HEADERS,
    INBOX_SCHEMA as SOURCE_INBOX_SCHEMA,
    QUERY_SCHEMA as SOURCE_QUERY_SCHEMA,
    RECEIPT_SCHEMA as SOURCE_RECEIPT_SCHEMA,
    MANIFEST_SCHEMA as SOURCE_MANIFEST_SCHEMA,
    parse_json, json_bytes, fixed, closed, integer, identifier, sha256, digest_id,
    validate_records as validate_source_records,
)

INDEX_SCHEMA = "termivar-offline-disclosed-file-index/v1"
LOOKUP_SCHEMA = "termivar-offline-disclosed-file-lookup/v1"
REQUEST_SCHEMA = "termivar-offline-disclosed-file-lookup-request/v1"
RECEIPT_SCHEMA = "termivar-offline-file-index-source-receipt/v1"
MANIFEST_SCHEMA = "termivar-offline-file-index-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-file-index-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — DISCLOSED METADATA ONLY — NO CURRENT SOURCE VERIFICATION"
MAX_REQUEST_BYTES = 32 * 1024
MAX_INDEX_BYTES = 256 * 1024
MAX_LOOKUP_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
MAX_REFERENCES = MAX_REQUESTED_FILES = 8
MAX_PROJECTIONS = MAX_VISIBLE_FILES = 64
SOURCE_NAMES = ("typed-inbox.json", "reference-query.json", "import-receipt.json",
                "inbox-summary.md", "manifest.json")
SOURCE_LIMITS = dict(zip(SOURCE_NAMES, (262144, 131072, 65536, 131072, 65536)))
SOURCE_SCHEMAS = dict(zip(SOURCE_NAMES, (SOURCE_INBOX_SCHEMA, SOURCE_QUERY_SCHEMA,
                                      SOURCE_RECEIPT_SCHEMA, None, SOURCE_MANIFEST_SCHEMA)))
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "trust_flags")
REFERENCE_FIELDS = tuple(CSV_HEADERS["reference"])
REFERENCE_PACKET_FIELDS = (*REFERENCE_FIELDS, "projections")
REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "source_inbox_sha256",
                  "source_manifest_sha256", "requested_file_ids")
SOURCE_COUNT_FIELDS = (
    "requested_reference_count", "provided_reference_count", "withheld_reference_count",
    "unavailable_reference_count", "projection_count", "unique_candidate_count",
    "unique_file_count", "present_projection_count", "absence_projection_count",
)
CONTENT_SCOPE = "five_Phase36_artifact_internal_correspondence_only"
LIMITATIONS = (
    "recorded_disclosed_metadata_only", "source_files_not_reobserved",
    "reference_context_not_revalidated", "upstream_guard_not_independently_verified",
    "internal_hashes_not_producer_authentication", "file_id_not_physical_identity",
    "no_ownership_human_legal_or_release_authority", "minimization_is_not_anonymization",
)


def fail(code: str) -> None:
    raise InputError("file_reference_index_invalid_" + code)


def common(schema: str) -> dict:
    if schema not in (INDEX_SCHEMA, LOOKUP_SCHEMA, RECEIPT_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "trust_flags": {flag: False for flag in FALSE_FLAGS}}


def _common_row(value: object, schema: str, fields: tuple, maximum: int) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *fields), "file_index_fields")
    fixed({key: row[key] for key in COMMON_FIELDS}, common(schema), "file_index_common")
    fixed(row["limitations"], list(LIMITATIONS), "file_index_limitations")
    return row


def validate_file_ids(value: object) -> list:
    if type(value) is not list or not 1 <= len(value) <= MAX_REQUESTED_FILES:
        fail("requested_file_ids")
    for file_id in value:
        digest_id(file_id, "candidate-file-", "requested_file_id")
    if len(set(value)) != len(value):
        fail("duplicate_requested_file")
    return copy.deepcopy(value)


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "lookup_request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "lookup_request_schema")
    fixed(row["mode"], "demo", "lookup_mode")
    identifier(row["request_reference"], "request_reference")
    sha256(row["source_inbox_sha256"], "source_inbox_sha256")
    sha256(row["source_manifest_sha256"], "source_manifest_sha256")
    validate_file_ids(row["requested_file_ids"])
    return copy.deepcopy(row)


def validate_source_artifacts(value: object) -> list:
    if type(value) is not list or len(value) != len(SOURCE_NAMES):
        fail("five_source_artifacts")
    for item, name in zip(value, SOURCE_NAMES):
        row = closed(item, ("name", "bytes", "sha256", "schema_version"), "source_artifact_fields")
        fixed(row["name"], name, "source_artifact_name")
        fixed(row["schema_version"], SOURCE_SCHEMAS[name], "source_artifact_schema")
        if integer(row["bytes"], "source_artifact_bytes", SOURCE_LIMITS[name]) == 0:
            fail("empty_source_artifact")
        sha256(row["sha256"], "source_artifact_sha256")
    return copy.deepcopy(value)


def _source_identity(row: dict) -> None:
    artifacts = validate_source_artifacts(row["source_artifacts"])
    fixed(row["source_inbox_sha256"], artifacts[0]["sha256"], "actual_Phase36_inbox_binding")
    fixed(row["source_manifest_sha256"], artifacts[-1]["sha256"], "actual_Phase36_manifest_binding")
    fixed(row["source_schema_version"], SOURCE_INBOX_SCHEMA, "source_inbox_schema")


def validate_source_counts(value: object) -> dict:
    row = closed(value, SOURCE_COUNT_FIELDS, "source_counts_fields")
    for key in SOURCE_COUNT_FIELDS:
        integer(row[key], "source_count", 8 if key.endswith("reference_count") else 64)
    refs, projections = row["requested_reference_count"], row["projection_count"]
    if (not 1 <= refs <= MAX_REFERENCES
            or refs != sum(row[k] for k in ("provided_reference_count", "withheld_reference_count", "unavailable_reference_count"))
            or projections != row["present_projection_count"] + row["absence_projection_count"]
            or row["unique_candidate_count"] != projections
            or not 0 <= row["unique_file_count"] <= projections
            or (projections > 0 and row["unique_file_count"] == 0)
            or row["provided_reference_count"] > projections
            or (row["provided_reference_count"] == 0 and projections != 0)):
        fail("source_counts_relationship")
    return copy.deepcopy(row)


def _provided_packets(value: object) -> list:
    json_bytes(value, maximum=MAX_INDEX_BYTES)
    if type(value) is not list or len(value) > MAX_REFERENCES:
        fail("disclosed_references")
    if not value:
        return []
    references, projections = [], []
    for packet in value:
        closed(packet, REFERENCE_PACKET_FIELDS, "disclosed_reference_fields")
        fixed(packet["disclosure_status"], "provided_limited_metadata", "provided_references_only")
        if type(packet["projections"]) is not list or not 1 <= len(packet["projections"]) <= MAX_PROJECTIONS:
            fail("disclosed_projection_list")
        fixed(packet["projection_count"], len(packet["projections"]), "disclosed_packet_projection_count")
        for projection in packet["projections"]:
            closed(projection, PROJECTION_FIELDS, "disclosed_packet_projection_fields")
            fixed(projection["reference_id"], packet["reference_id"], "disclosed_packet_projection_reference")
        references.append({key: packet[key] for key in REFERENCE_FIELDS})
        projections.extend(packet["projections"])
    validate_source_records(references, projections)
    ids = [reference["reference_id"] for reference in references]
    fixed(ids, sorted(ids), "disclosed_reference_order")
    return copy.deepcopy(value)


def derive_file_records(disclosed_references: list) -> list:
    """Derive only existing visible reference/candidate/file triples."""
    packets = _provided_packets(disclosed_references)
    grouped = {}
    triples = set()
    for packet in packets:
        reference_id = packet["reference_id"]
        for projection in packet["projections"]:
            file_id, candidate_id = projection["file_id"], projection["candidate_id"]
            triple = (reference_id, candidate_id, file_id)
            if triple in triples:
                fail("duplicate_projection_binding")
            triples.add(triple)
            group = grouped.setdefault(file_id, {"references": set(), "candidates": set(), "bindings": []})
            group["references"].add(reference_id)
            group["candidates"].add(candidate_id)
            group["bindings"].append(triple)
    if len(grouped) > MAX_VISIBLE_FILES:
        fail("visible_file_count")
    return [{"file_id": file_id,
             "reference_ids": sorted(grouped[file_id]["references"]),
             "candidate_ids": sorted(grouped[file_id]["candidates"]),
             "projection_bindings": [
                 {"reference_id": ref, "candidate_id": candidate, "file_id": bound_file}
                 for ref, candidate, bound_file in sorted(grouped[file_id]["bindings"])
             ]}
            for file_id in sorted(grouped)]


def index_counts(disclosed_references: list, file_records: list) -> dict:
    packets = _provided_packets(disclosed_references)
    expected_files = derive_file_records(packets)
    fixed(file_records, expected_files, "file_records_correspondence")
    projections = [p for packet in packets for p in packet["projections"]]
    return {"file_count": len(expected_files), "reference_count": len(packets),
            "candidate_count": len({p["candidate_id"] for p in projections}),
            "projection_count": len(projections),
            "present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
            "absence_projection_count": sum(p["source_file_presence"] == "missing" for p in projections)}


def _visible_source_counts(source_counts: dict, visible_counts: dict) -> None:
    mapping = {"provided_reference_count": "reference_count", "projection_count": "projection_count",
               "unique_candidate_count": "candidate_count", "unique_file_count": "file_count",
               "present_projection_count": "present_projection_count", "absence_projection_count": "absence_projection_count"}
    for source_key, visible_key in mapping.items():
        fixed(source_counts[source_key], visible_counts[visible_key], "visible_source_counts")


def validate_index(value: object) -> dict:
    row = _common_row(value, INDEX_SCHEMA, ("source_inbox_sha256", "source_manifest_sha256", "source_schema_version",
                      "source_artifacts", "source_counts", "disclosed_references", "file_records", "counts", "limitations"), MAX_INDEX_BYTES)
    _source_identity(row)
    source_counts = validate_source_counts(row["source_counts"])
    packets = _provided_packets(row["disclosed_references"])
    fixed(row["file_records"], derive_file_records(packets), "index_file_records")
    counts = index_counts(packets, row["file_records"])
    fixed(row["counts"], counts, "index_counts")
    _visible_source_counts(source_counts, counts)
    return copy.deepcopy(row)


def lookup_counts(file_results: list, reference_results: list) -> dict:
    projections = [p for packet in reference_results for p in packet["projections"]]
    return {"requested_file_count": len(file_results),
            "matched_file_count": sum(row["status"] == "matched" for row in file_results),
            "not_in_disclosed_index_count": sum(row["status"] == "not_in_disclosed_index" for row in file_results),
            "returned_reference_count": len(reference_results),
            "returned_projection_count": len(projections),
            "returned_candidate_count": len({p["candidate_id"] for p in projections}),
            "returned_present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
            "returned_absence_projection_count": sum(p["source_file_presence"] == "missing" for p in projections)}


def validate_lookup(value: object) -> dict:
    row = _common_row(value, LOOKUP_SCHEMA, ("request", "source_inbox_sha256", "source_manifest_sha256",
                      "file_results", "reference_results", "counts", "limitations"), MAX_LOOKUP_BYTES)
    request = validate_request(row["request"])
    for key in ("source_inbox_sha256", "source_manifest_sha256"):
        fixed(row[key], request[key], "lookup_request_source_binding")
    files = row["file_results"]
    if type(files) is not list or len(files) != len(request["requested_file_ids"]):
        fail("lookup_file_results")
    references_by_file, union = {}, set()
    for result, requested in zip(files, request["requested_file_ids"]):
        closed(result, ("file_id", "status", "reference_ids"), "lookup_file_result_fields")
        fixed(result["file_id"], requested, "lookup_file_result_order")
        ids = result["reference_ids"]
        if type(ids) is not list or len(ids) > MAX_REFERENCES:
            fail("lookup_matched_reference_ids")
        for ref in ids:
            digest_id(ref, "rust-ref-", "lookup_reference_id")
        fixed(ids, sorted(set(ids)), "lookup_unique_sorted_reference_ids")
        if result["status"] == "matched":
            if not ids:
                fail("lookup_matched_without_reference")
        elif result["status"] == "not_in_disclosed_index":
            if ids:
                fail("lookup_unknown_reference_disclosure")
        else:
            fail("lookup_uniform_file_status")
        references_by_file[requested] = ids
        union.update(ids)
    results = row["reference_results"]
    if type(results) is not list or len(results) > MAX_REFERENCES:
        fail("lookup_reference_results")
    packets = []
    for result in results:
        closed(result, (*REFERENCE_PACKET_FIELDS, "matched_file_ids"), "lookup_reference_result_fields")
        packets.append({key: result[key] for key in REFERENCE_PACKET_FIELDS})
    packets = _provided_packets(packets)
    fixed([p["reference_id"] for p in packets], sorted(union), "lookup_unique_reference_union")
    for result in results:
        reference = result["reference_id"]
        expected_files = [file_id for file_id in request["requested_file_ids"] if reference in references_by_file[file_id]]
        fixed(result["matched_file_ids"], expected_files, "lookup_matched_file_ids")
        visible_files = {p["file_id"] for p in result["projections"]}
        if any(file_id not in visible_files for file_id in expected_files):
            fail("lookup_reference_file_binding")
    fixed(row["counts"], lookup_counts(files, results), "lookup_counts")
    return copy.deepcopy(row)


def validate_receipt(value: object) -> dict:
    row = _common_row(value, RECEIPT_SCHEMA, ("source_artifacts", "source_inbox_sha256", "source_manifest_sha256",
                      "source_schema_version", "source_counts", "index_counts", "content_scope", "limitations"), MAX_RECEIPT_BYTES)
    _source_identity(row)
    source_counts = validate_source_counts(row["source_counts"])
    expected_counts = {
        "file_count": source_counts["unique_file_count"], "reference_count": source_counts["provided_reference_count"],
        "candidate_count": source_counts["unique_candidate_count"], "projection_count": source_counts["projection_count"],
        "present_projection_count": source_counts["present_projection_count"], "absence_projection_count": source_counts["absence_projection_count"],
    }
    fixed(row["index_counts"], expected_counts, "receipt_index_counts")
    fixed(row["content_scope"], CONTENT_SCOPE, "receipt_content_scope")
    return copy.deepcopy(row)


def make_source_receipt(index: dict) -> dict:
    index = validate_index(index)
    return validate_receipt({
        **common(RECEIPT_SCHEMA),
        "source_artifacts": copy.deepcopy(index["source_artifacts"]),
        "source_inbox_sha256": index["source_inbox_sha256"],
        "source_manifest_sha256": index["source_manifest_sha256"],
        "source_schema_version": index["source_schema_version"],
        "source_counts": copy.deepcopy(index["source_counts"]),
        "index_counts": copy.deepcopy(index["counts"]),
        "content_scope": CONTENT_SCOPE,
        "limitations": list(LIMITATIONS),
    })


def validate_relationships(index: object, lookup: object, receipt: object) -> tuple[dict, dict, dict]:
    index, lookup, receipt = validate_index(index), validate_lookup(lookup), validate_receipt(receipt)
    for key in ("source_inbox_sha256", "source_manifest_sha256"):
        fixed(lookup[key], index[key], "lookup_index_actual_source")
    fixed(receipt, make_source_receipt(index), "receipt_index_correspondence")
    # Reuse the business lookup, with imports deferred until all closed wire
    # functions exist. This is internal reconstruction, not a second evaluator.
    from disclosed_file_index import ValidatedFileIndex
    from reverse_lookup import build_file_lookup

    snapshot = ValidatedFileIndex(json_bytes(index, maximum=MAX_INDEX_BYTES))
    expected_lookup = build_file_lookup(snapshot, lookup["request"])
    fixed(lookup, expected_lookup, "lookup_complete_index_correspondence")
    return index, lookup, receipt
