"""Closed co-reference correspondence; reuse protected wire primitives.

These models describe recorded disclosed metadata only. Neither a set
intersection nor internal consistency establishes physical or source truth.
"""
from __future__ import annotations

import copy
from itertools import combinations

from index_contracts import (
    InputError, FALSE_FLAGS, parse_json, json_bytes, fixed, closed, integer,
    identifier, sha256, digest_id,
    INDEX_SCHEMA as SOURCE_INDEX_SCHEMA,
    LOOKUP_SCHEMA as SOURCE_LOOKUP_SCHEMA,
    RECEIPT_SCHEMA as SOURCE_RECEIPT_SCHEMA,
    MANIFEST_SCHEMA as SOURCE_MANIFEST_SCHEMA,
    validate_file_ids as source_file_ids,
    _provided_packets as owner_provided_packets,
)
from capsule_contracts import RESULT_LIMITATIONS

REQUEST_SCHEMA = "termivar-offline-co-reference-request/v1"
JOIN_SCHEMA = "termivar-offline-disclosed-co-reference/v1"
LOOKUP_SCHEMA = "termivar-offline-co-reference-lookup/v1"
RECEIPT_SCHEMA = "termivar-offline-co-reference-source-receipt/v1"
MANIFEST_SCHEMA = "termivar-offline-co-reference-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-co-reference-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — DISCLOSED CO-REFERENCE ONLY — NO PHYSICAL FILE OR SOURCE RELATIONSHIP VERIFIED"
MAX_REQUEST_BYTES = 32 * 1024
MAX_JOIN_BYTES = 256 * 1024
MAX_LOOKUP_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
MAX_REFERENCES = MAX_REQUESTED_FILES = 8
MAX_PROJECTIONS = MAX_VISIBLE_FILES = 64
MAX_PAIRS = 28
SOURCE_NAMES = ("file-reference-index.json", "file-reference-lookup.json", "index-source-receipt.json",
                "file-index-summary.md", "manifest.json")
SOURCE_LIMITS = dict(zip(SOURCE_NAMES, (262144, 131072, 65536, 131072, 65536)))
SOURCE_SCHEMAS = dict(zip(SOURCE_NAMES, (SOURCE_INDEX_SCHEMA, SOURCE_LOOKUP_SCHEMA,
                                      SOURCE_RECEIPT_SCHEMA, None, SOURCE_MANIFEST_SCHEMA)))
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "trust_flags")
REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "source_index_sha256",
                  "source_manifest_sha256", "requested_file_ids")
SOURCE_COUNT_FIELDS = ("file_count", "reference_count", "candidate_count", "projection_count",
                       "present_projection_count", "absence_projection_count")
CONTENT_SCOPE = "five_Phase37_artifact_internal_correspondence_only"
LIMITATIONS = (
    "recorded_disclosed_co_reference_only", "not_physical_file_or_content_equality",
    "not_source_compiler_ownership_or_security_relation", "source_files_not_reobserved",
    "upstream_guard_not_independently_verified", "internal_hashes_not_producer_authentication",
    "no_human_legal_customer_or_release_authority", "minimization_is_not_anonymization",
)


def fail(code: str) -> None:
    raise InputError("co_reference_invalid_" + code)


def common(schema: str) -> dict:
    if schema not in (JOIN_SCHEMA, LOOKUP_SCHEMA, RECEIPT_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "trust_flags": {flag: False for flag in FALSE_FLAGS}}


def _common_row(value: object, schema: str, fields: tuple, maximum: int) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *fields), "closed_model_fields")
    fixed({key: row[key] for key in COMMON_FIELDS}, common(schema), "common_fields")
    fixed(row["limitations"], list(LIMITATIONS), "limitations")
    return row


def validate_file_ids(value: object) -> list:
    ids = source_file_ids(value)
    if len(ids) < 2:
        fail("at_least_two_requested_files")
    return ids


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "request_schema")
    fixed(row["mode"], "demo", "mode")
    identifier(row["request_reference"], "request_reference")
    sha256(row["source_index_sha256"], "source_index_sha256")
    sha256(row["source_manifest_sha256"], "source_manifest_sha256")
    validate_file_ids(row["requested_file_ids"])
    return copy.deepcopy(row)


def validate_source_artifacts(value: object) -> list:
    if type(value) is not list or len(value) != len(SOURCE_NAMES):
        fail("five_actual_source_artifacts")
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
    fixed(row["source_index_sha256"], artifacts[0]["sha256"], "actual_Phase37_index_identity")
    fixed(row["source_manifest_sha256"], artifacts[-1]["sha256"], "actual_Phase37_manifest_identity")
    fixed(row["source_schema_version"], SOURCE_INDEX_SCHEMA, "source_index_schema")


def validate_source_counts(value: object) -> dict:
    row = closed(value, SOURCE_COUNT_FIELDS, "visible_source_count_fields")
    for key in SOURCE_COUNT_FIELDS:
        integer(row[key], "visible_source_count", MAX_REFERENCES if key == "reference_count" else MAX_PROJECTIONS)
    projections = row["projection_count"]
    if (row["candidate_count"] != projections
            or projections != row["present_projection_count"] + row["absence_projection_count"]
            or not 0 <= row["file_count"] <= projections
            or row["reference_count"] > projections
            or (projections > 0 and (row["file_count"] == 0 or row["reference_count"] == 0))
            or (projections == 0 and row["reference_count"] != 0)):
        fail("visible_source_counts_relation")
    return copy.deepcopy(row)


def _file_results(value: object, requested_ids: list) -> list:
    if type(value) is not list or len(value) != len(requested_ids):
        fail("file_results")
    for row, file_id in zip(value, requested_ids):
        closed(row, ("file_id", "status", "visible_reference_ids"), "file_result_fields")
        fixed(row["file_id"], file_id, "file_result_order")
        refs = row["visible_reference_ids"]
        if type(refs) is not list or len(refs) > MAX_REFERENCES:
            fail("visible_reference_ids")
        for ref in refs:
            digest_id(ref, "rust-ref-", "visible_reference_id")
        fixed(refs, sorted(set(refs)), "visible_reference_uniqueness_order")
        if row["status"] == "matched":
            if not refs:
                fail("matched_file_without_visible_reference")
        elif row["status"] == "not_in_disclosed_index":
            if refs:
                fail("undisclosed_file_reference_oracle")
        else:
            fail("uniform_file_status")
    return copy.deepcopy(value)


def compute_pair_results(file_results: list, reference_packets: list) -> list:
    """Derive canonical pairs and their real shared-packet projection triples."""
    if type(file_results) is not list:
        fail("file_results")
    for row in file_results:
        closed(row, ("file_id", "status", "visible_reference_ids"), "file_result_fields")
    requested = validate_file_ids([row["file_id"] for row in file_results])
    files = {row["file_id"]: row for row in _file_results(file_results, requested)}
    packets = owner_provided_packets(reference_packets)
    by_reference = {packet["reference_id"]: packet for packet in packets}
    for packet in packets:
        for projection in packet["projections"]:
            file_id = projection["file_id"]
            if file_id in files and packet["reference_id"] not in files[file_id]["visible_reference_ids"]:
                fail("shared_packet_requested_file_reference_binding")
    pairs, shared_union = [], set()
    for left, right in combinations(sorted(requested), 2):
        if files[left]["status"] != "matched" or files[right]["status"] != "matched":
            status, shared = "not_in_disclosed_index", []
        else:
            shared = sorted(set(files[left]["visible_reference_ids"]) & set(files[right]["visible_reference_ids"]))
            status = "shared_disclosed_reference" if shared else "no_shared_disclosed_reference"
        bindings = []
        for reference_id in shared:
            if reference_id not in by_reference:
                fail("shared_reference_packet_missing")
            triples = [(reference_id, p["candidate_id"], p["file_id"])
                       for p in by_reference[reference_id]["projections"] if p["file_id"] in (left, right)]
            if {triple[2] for triple in triples} != {left, right}:
                fail("shared_reference_both_file_bindings_required")
            bindings.extend(triples)
        if len(set(bindings)) != len(bindings) or len(bindings) > MAX_PROJECTIONS:
            fail("duplicate_or_excess_pair_binding")
        pairs.append({"left_file_id": left, "right_file_id": right,
                      "relationship_status": status, "shared_reference_ids": shared,
                      "supporting_projection_bindings": [
                          {"reference_id": ref, "candidate_id": candidate, "file_id": file_id}
                          for ref, candidate, file_id in sorted(bindings)
                      ]})
        shared_union.update(shared)
    fixed([packet["reference_id"] for packet in packets], sorted(shared_union), "exact_shared_reference_catalog")
    return pairs


def join_counts(file_results: list, pair_results: list, reference_packets: list) -> dict:
    bindings = [binding for pair in pair_results for binding in pair["supporting_projection_bindings"]]
    unique = {(b["reference_id"], b["candidate_id"], b["file_id"]) for b in bindings}
    return {"requested_file_count": len(file_results),
            "matched_file_count": sum(row["status"] == "matched" for row in file_results),
            "not_in_disclosed_index_file_count": sum(row["status"] == "not_in_disclosed_index" for row in file_results),
            "pair_count": len(pair_results),
            "shared_pair_count": sum(row["relationship_status"] == "shared_disclosed_reference" for row in pair_results),
            "no_shared_pair_count": sum(row["relationship_status"] == "no_shared_disclosed_reference" for row in pair_results),
            "not_in_disclosed_index_pair_count": sum(row["relationship_status"] == "not_in_disclosed_index" for row in pair_results),
            "shared_reference_count": len(reference_packets),
            "supporting_binding_count": len(bindings), "unique_supporting_binding_count": len(unique)}


def _source_bounds(source_counts: dict, files: list, packets: list) -> None:
    matched_files = sum(row["status"] == "matched" for row in files)
    visible_refs = {ref for row in files for ref in row["visible_reference_ids"]}
    projections = [p for packet in packets for p in packet["projections"]]
    projected_files = {p["file_id"] for p in projections}
    actual = {"file_count": len(projected_files), "reference_count": len(packets),
              "candidate_count": len({p["candidate_id"] for p in projections}),
              "projection_count": len(projections),
              "present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
              "absence_projection_count": sum(p["source_file_presence"] == "missing" for p in projections)}
    if (matched_files > source_counts["file_count"] or len(visible_refs) > source_counts["reference_count"]
            or any(actual[key] > source_counts[key] for key in SOURCE_COUNT_FIELDS)):
        fail("shared_disclosure_exceeds_visible_source_counts")


def validate_join(value: object) -> dict:
    row = _common_row(value, JOIN_SCHEMA, ("source_index_sha256", "source_manifest_sha256", "source_schema_version",
                      "source_artifacts", "source_counts", "requested_file_ids", "file_results", "pair_results",
                      "reference_packets", "counts", "limitations"), MAX_JOIN_BYTES)
    _source_identity(row)
    source_counts = validate_source_counts(row["source_counts"])
    requested = validate_file_ids(row["requested_file_ids"])
    files = _file_results(row["file_results"], requested)
    packets = owner_provided_packets(row["reference_packets"])
    pairs = compute_pair_results(files, packets)
    fixed(row["pair_results"], pairs, "canonical_pair_results")
    if len(pairs) > MAX_PAIRS:
        fail("pair_count")
    fixed(row["counts"], join_counts(files, pairs, packets), "join_counts")
    _source_bounds(source_counts, files, packets)
    return copy.deepcopy(row)


def lookup_counts(results: list) -> dict:
    projections = [p for result in results for p in result["projections"]]
    return {"reference_count": len(results), "projection_count": len(projections),
            "candidate_count": len({p["candidate_id"] for p in projections}),
            "present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
            "absence_projection_count": sum(p["source_file_presence"] == "missing" for p in projections),
            "matched_file_count": len({file_id for result in results for file_id in result["matched_file_ids"]})}


def validate_lookup(value: object) -> dict:
    row = _common_row(value, LOOKUP_SCHEMA, ("source_index_sha256", "source_manifest_sha256", "requested_file_ids",
                      "results", "counts", "limitations"), MAX_LOOKUP_BYTES)
    sha256(row["source_index_sha256"], "lookup_source_index_sha256")
    sha256(row["source_manifest_sha256"], "lookup_source_manifest_sha256")
    requested = validate_file_ids(row["requested_file_ids"])
    results = row["results"]
    if type(results) is not list or len(results) > MAX_REFERENCES:
        fail("lookup_results")
    packets = []
    for result in results:
        closed(result, ("reference_id", "disclosure_status", "matched_file_ids", "projections"), "lookup_result_fields")
        fixed(result["disclosure_status"], "provided_limited_metadata", "lookup_provided_only")
        if type(result["projections"]) is not list or not 1 <= len(result["projections"]) <= MAX_PROJECTIONS:
            fail("lookup_projection_list")
        matched = validate_file_ids(result["matched_file_ids"])
        if any(file_id not in requested for file_id in matched):
            fail("lookup_matched_file_outside_request")
        fixed(matched, [file_id for file_id in requested if file_id in matched], "lookup_matched_file_order")
        packets.append({"reference_id": result["reference_id"], "disclosure_status": result["disclosure_status"],
                        "projection_count": len(result["projections"]),
                        "interpretation_limitations": list(RESULT_LIMITATIONS["provided_limited_metadata"]),
                        "projections": result["projections"]})
    owner_provided_packets(packets)
    for result in results:
        projection_files = {p["file_id"] for p in result["projections"]}
        if any(file_id not in projection_files for file_id in result["matched_file_ids"]):
            fail("lookup_matched_projection_binding")
    fixed(row["counts"], lookup_counts(results), "lookup_counts")
    return copy.deepcopy(row)


def lookup_from_join(join: dict) -> dict:
    join = validate_join(join)
    files = {row["file_id"]: row for row in join["file_results"]}
    results = [{"reference_id": packet["reference_id"], "disclosure_status": packet["disclosure_status"],
                "matched_file_ids": [file_id for file_id in join["requested_file_ids"]
                                     if packet["reference_id"] in files[file_id]["visible_reference_ids"]],
                "projections": copy.deepcopy(packet["projections"])}
               for packet in join["reference_packets"]]
    return validate_lookup({
        **common(LOOKUP_SCHEMA), "source_index_sha256": join["source_index_sha256"],
        "source_manifest_sha256": join["source_manifest_sha256"],
        "requested_file_ids": list(join["requested_file_ids"]), "results": results,
        "counts": lookup_counts(results), "limitations": list(LIMITATIONS),
    })


def validate_receipt(value: object) -> dict:
    row = _common_row(value, RECEIPT_SCHEMA, ("source_artifacts", "source_index_sha256", "source_manifest_sha256",
                      "source_schema_version", "source_counts", "content_scope", "limitations"), MAX_RECEIPT_BYTES)
    _source_identity(row)
    validate_source_counts(row["source_counts"])
    fixed(row["content_scope"], CONTENT_SCOPE, "source_content_scope")
    return copy.deepcopy(row)


def make_source_receipt(join: dict) -> dict:
    join = validate_join(join)
    return validate_receipt({
        **common(RECEIPT_SCHEMA), "source_artifacts": copy.deepcopy(join["source_artifacts"]),
        "source_index_sha256": join["source_index_sha256"], "source_manifest_sha256": join["source_manifest_sha256"],
        "source_schema_version": join["source_schema_version"], "source_counts": copy.deepcopy(join["source_counts"]),
        "content_scope": CONTENT_SCOPE, "limitations": list(LIMITATIONS),
    })


def validate_relationships(join: object, lookup: object, receipt: object) -> tuple[dict, dict, dict]:
    join, lookup, receipt = validate_join(join), validate_lookup(lookup), validate_receipt(receipt)
    fixed(lookup, lookup_from_join(join), "lookup_complete_shared_packets")
    fixed(receipt, make_source_receipt(join), "receipt_join_correspondence")
    return join, lookup, receipt
