"""Closed recorded-missing follow-up models; no observation or assignment."""
from __future__ import annotations

import copy
import hashlib

from cohort_contracts import (
    InputError, FALSE_FLAGS, parse_json, json_bytes, fixed, closed, integer,
    identifier, sha256, digest_id, source_file_ids, owner_provided_packets,
    QUERY_SCHEMA as SOURCE_QUERY_SCHEMA,
    WITNESSES_SCHEMA as SOURCE_WITNESSES_SCHEMA,
    RECEIPT_SCHEMA as SOURCE_RECEIPT_SCHEMA,
    MANIFEST_SCHEMA as SOURCE_MANIFEST_SCHEMA,
    COUNT_FIELDS as SOURCE_COUNT_FIELDS,
)
from capsule_contracts import RESULT_LIMITATIONS

REQUEST_SCHEMA = "termivar-offline-evidence-followup-request/v1"
QUEUE_SCHEMA = "termivar-offline-evidence-followup-queue/v1"
HANDOFF_SCHEMA = "termivar-offline-evidence-analyst-handoff/v1"
RECEIPT_SCHEMA = "termivar-offline-evidence-followup-source-receipt/v1"
MANIFEST_SCHEMA = "termivar-offline-evidence-followup-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-evidence-followup-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — RECORDED MISSING EVIDENCE FOLLOW-UP ONLY — NO OBSERVATION OR ASSIGNMENT AUTHORIZED"
MAX_REQUEST_BYTES = 32 * 1024
MAX_QUEUE_BYTES = 256 * 1024
MAX_HANDOFF_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
MAX_REFERENCES = 8
MAX_PROJECTIONS = MAX_TASKS = 64
SOURCE_NAMES = ("cohort-query.json", "cohort-witnesses.json", "cohort-source-receipt.json",
                "cohort-summary.md", "manifest.json")
SOURCE_LIMITS = dict(zip(SOURCE_NAMES, (131072, 262144, 65536, 131072, 65536)))
SOURCE_SCHEMAS = dict(zip(SOURCE_NAMES, (SOURCE_QUERY_SCHEMA, SOURCE_WITNESSES_SCHEMA,
                                      SOURCE_RECEIPT_SCHEMA, None, SOURCE_MANIFEST_SCHEMA)))
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "trust_flags")
REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "source_phase39_witnesses_sha256",
                  "source_phase39_manifest_sha256", "requested_reference_ids")
PACKET_FIELDS = ("reference_id", "disclosure_status", "matched_file_ids",
                 "supporting_projection_bindings", "projections")
TASK_FIELDS = ("task_id", "reference_id", "candidate_id", "file_id", "recorded_source_file_presence",
               "followup_kind", "task_status", "fulfillment_status")
COUNT_FIELDS = ("selected_reference_count", "selected_projection_count",
                "recorded_present_projection_count", "recorded_missing_projection_count",
                "pending_task_count", "distinct_file_count", "distinct_candidate_count")
CONTENT_SCOPE = "five_Phase39_artifact_internal_correspondence_only"
LIMITATIONS = (
    "recorded_missing_evidence_followup_only", "not_current_file_state_or_source_observation",
    "prepared_unassigned_not_authorized_or_fulfilled", "whole_reference_packet_metadata_only",
    "not_source_compiler_ownership_or_security_relation", "source_files_not_reobserved",
    "upstream_guard_not_independently_verified", "internal_hashes_not_producer_authentication",
    "no_human_legal_customer_or_release_authority", "minimization_is_not_anonymization",
)


def fail(code: str) -> None:
    raise InputError("evidence_followup_invalid_" + code)


def common(schema: str) -> dict:
    if schema not in (QUEUE_SCHEMA, HANDOFF_SCHEMA, RECEIPT_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "trust_flags": {flag: False for flag in FALSE_FLAGS}}


def _common_row(value: object, schema: str, fields: tuple, maximum: int) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *fields), "followup_closed_model_fields")
    fixed({key: row[key] for key in COMMON_FIELDS}, common(schema), "followup_common_fields")
    fixed(row["limitations"], list(LIMITATIONS), "followup_limitations")
    return row


def reference_ids(value: object) -> list:
    if type(value) is not list or not 1 <= len(value) <= MAX_REFERENCES:
        fail("requested_reference_ids")
    for reference_id in value:
        digest_id(reference_id, "rust-ref-", "followup_requested_reference_id")
    if len(set(value)) != len(value):
        fail("duplicate_requested_reference_id")
    return copy.deepcopy(value)


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "followup_request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "followup_request_schema")
    fixed(row["mode"], "demo", "followup_request_mode")
    identifier(row["request_reference"], "followup_request_reference")
    sha256(row["source_phase39_witnesses_sha256"], "followup_source_witnesses_sha256")
    sha256(row["source_phase39_manifest_sha256"], "followup_source_manifest_sha256")
    reference_ids(row["requested_reference_ids"])
    return copy.deepcopy(row)


def validate_reference_packets(value: object) -> list:
    """Validate whole disclosed packets without inventing an old request."""
    json_bytes(value, maximum=MAX_QUEUE_BYTES)
    if type(value) is not list or len(value) > MAX_REFERENCES:
        fail("reference_packets")
    owner_packets = []
    for packet in value:
        closed(packet, PACKET_FIELDS, "followup_reference_packet_fields")
        fixed(packet["disclosure_status"], "provided_limited_metadata", "followup_provided_packet_only")
        source_file_ids(packet["matched_file_ids"])
        projections = packet["projections"]
        if type(projections) is not list or not 1 <= len(projections) <= MAX_PROJECTIONS:
            fail("reference_projection_list")
        owner_packets.append({
            "reference_id": packet["reference_id"], "disclosure_status": packet["disclosure_status"],
            "projection_count": len(projections),
            "interpretation_limitations": list(RESULT_LIMITATIONS["provided_limited_metadata"]),
            "projections": projections,
        })
    # The owner checks all eleven projection fields, sorted unique references,
    # global candidate uniqueness and shared-file metadata correspondence.
    validated = owner_provided_packets(owner_packets)
    for packet, owner_packet in zip(value, validated):
        projections = owner_packet["projections"]
        for file_id in packet["matched_file_ids"]:
            matching = [p for p in projections if p["file_id"] == file_id]
            if not matching or len({p["source_file_presence"] for p in matching}) != 1:
                fail("matched_file_projection_missing_or_conflicting")
        triples = [(packet["reference_id"], p["candidate_id"], p["file_id"])
                   for p in projections if p["file_id"] in packet["matched_file_ids"]]
        if len(set(triples)) != len(triples):
            fail("duplicate_projection_binding")
        expected = [{"reference_id": ref, "candidate_id": candidate, "file_id": file_id}
                    for ref, candidate, file_id in sorted(triples)]
        fixed(packet["supporting_projection_bindings"], expected, "followup_all_original_support_bindings")
    return copy.deepcopy(value)


def derive_followup_tasks(reference_packets: object) -> list:
    """One prepared local task per real supported recorded-missing triple."""
    packets = validate_reference_packets(reference_packets)
    missing = []
    for packet in packets:
        support = {(b["reference_id"], b["candidate_id"], b["file_id"])
                   for b in packet["supporting_projection_bindings"]}
        for projection in packet["projections"]:
            if projection["source_file_presence"] != "missing":
                continue
            triple = (packet["reference_id"], projection["candidate_id"], projection["file_id"])
            if triple not in support:
                # Retaining the whole packet must not silently drop an
                # unsupported missing record from the requested follow-up.
                fail("missing_projection_without_real_support")
            missing.append(triple)
    if len(missing) > MAX_TASKS or len(set(missing)) != len(missing):
        fail("duplicate_or_excess_missing_binding")
    return [{
        "task_id": f"F{number:04d}", "reference_id": ref, "candidate_id": candidate,
        "file_id": file_id, "recorded_source_file_presence": "missing",
        "followup_kind": "request_fresh_source_observation", "task_status": "prepared_unassigned",
        "fulfillment_status": "not_observed",
    } for number, (ref, candidate, file_id) in enumerate(sorted(missing), 1)]


def followup_counts(reference_packets: object, tasks: object) -> dict:
    packets = validate_reference_packets(reference_packets)
    fixed(tasks, derive_followup_tasks(packets), "followup_exact_pending_tasks")
    projections = [projection for packet in packets for projection in packet["projections"]]
    return {"selected_reference_count": len(packets), "selected_projection_count": len(projections),
            "recorded_present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
            "recorded_missing_projection_count": sum(p["source_file_presence"] == "missing" for p in projections),
            "pending_task_count": len(tasks), "distinct_file_count": len({p["file_id"] for p in projections}),
            "distinct_candidate_count": len({p["candidate_id"] for p in projections})}


def validate_queue(value: object) -> dict:
    row = _common_row(value, QUEUE_SCHEMA, ("source_phase39_witnesses_sha256", "source_phase39_manifest_sha256",
                      "request", "reference_packets", "followup_tasks", "counts", "limitations"), MAX_QUEUE_BYTES)
    request = validate_request(row["request"])
    for key in ("source_phase39_witnesses_sha256", "source_phase39_manifest_sha256"):
        fixed(row[key], request[key], "followup_queue_request_source_binding")
    packets = validate_reference_packets(row["reference_packets"])
    fixed([packet["reference_id"] for packet in packets], sorted(request["requested_reference_ids"]),
          "followup_complete_requested_packets")
    fixed(row["followup_tasks"], derive_followup_tasks(packets), "followup_queue_tasks")
    fixed(row["counts"], followup_counts(packets, row["followup_tasks"]), "followup_queue_whole_packet_counts")
    return copy.deepcopy(row)


def validate_handoff(value: object) -> dict:
    row = _common_row(value, HANDOFF_SCHEMA, ("source_phase39_witnesses_sha256", "source_phase39_manifest_sha256",
                      "queue_sha256", "request_reference", "reference_packets", "handoff_tasks", "counts",
                      "limitations"), MAX_HANDOFF_BYTES)
    for key in ("source_phase39_witnesses_sha256", "source_phase39_manifest_sha256", "queue_sha256"):
        sha256(row[key], "followup_handoff_digest")
    identifier(row["request_reference"], "followup_handoff_request_reference")
    packets = validate_reference_packets(row["reference_packets"])
    fixed(row["handoff_tasks"], derive_followup_tasks(packets), "followup_handoff_tasks")
    fixed([packet["reference_id"] for packet in packets],
          sorted({task["reference_id"] for task in row["handoff_tasks"]}), "followup_handoff_only_task_references")
    fixed(row["counts"], followup_counts(packets, row["handoff_tasks"]), "followup_handoff_whole_packet_counts")
    return copy.deepcopy(row)


def handoff_from_queue(queue: object) -> dict:
    queue = validate_queue(queue)
    tasks = copy.deepcopy(queue["followup_tasks"])
    task_references = {task["reference_id"] for task in tasks}
    packets = [copy.deepcopy(packet) for packet in queue["reference_packets"]
               if packet["reference_id"] in task_references]
    return validate_handoff({
        **common(HANDOFF_SCHEMA),
        "source_phase39_witnesses_sha256": queue["source_phase39_witnesses_sha256"],
        "source_phase39_manifest_sha256": queue["source_phase39_manifest_sha256"],
        "queue_sha256": hashlib.sha256(json_bytes(queue, maximum=MAX_QUEUE_BYTES)).hexdigest(),
        "request_reference": queue["request"]["request_reference"], "reference_packets": packets,
        "handoff_tasks": tasks, "counts": followup_counts(packets, tasks), "limitations": list(LIMITATIONS),
    })


def validate_source_artifacts(value: object) -> list:
    if type(value) is not list or len(value) != len(SOURCE_NAMES):
        fail("five_actual_Phase39_sources")
    for item, name in zip(value, SOURCE_NAMES):
        row = closed(item, ("name", "bytes", "sha256", "schema_version"), "followup_source_artifact_fields")
        fixed(row["name"], name, "followup_source_artifact_name")
        fixed(row["schema_version"], SOURCE_SCHEMAS[name], "followup_source_artifact_schema")
        if integer(row["bytes"], "followup_source_artifact_bytes", SOURCE_LIMITS[name]) == 0:
            fail("empty_source_artifact")
        sha256(row["sha256"], "followup_source_artifact_sha256")
    return copy.deepcopy(value)


def validate_source_counts(value: object) -> dict:
    """The current Phase39 QUERY six counts, never the old visible receipt six."""
    row = closed(value, SOURCE_COUNT_FIELDS, "followup_source_QUERY_count_fields")
    for key in SOURCE_COUNT_FIELDS:
        integer(row[key], "followup_source_QUERY_count", 8 if key in ("required_file_count", "matched_reference_count") else 64)
    required, references, projections = row["required_file_count"], row["matched_reference_count"], row["matched_projection_count"]
    if (required < 2 or row["matched_candidate_count"] != projections
            or projections != row["matched_present_projection_count"] + row["matched_absence_projection_count"]
            or projections < required * references
            or (not references and any(row[key] for key in SOURCE_COUNT_FIELDS if key != "required_file_count"))):
        fail("source_QUERY_count_relations")
    return copy.deepcopy(row)


def validate_receipt(value: object) -> dict:
    row = _common_row(value, RECEIPT_SCHEMA, ("source_artifacts", "source_phase39_witnesses_sha256",
                      "source_phase39_manifest_sha256", "source_schema_versions", "source_counts",
                      "content_scope", "limitations"), MAX_RECEIPT_BYTES)
    artifacts = validate_source_artifacts(row["source_artifacts"])
    fixed(row["source_phase39_witnesses_sha256"], artifacts[1]["sha256"], "followup_actual_Phase39_witness_identity")
    fixed(row["source_phase39_manifest_sha256"], artifacts[-1]["sha256"], "followup_actual_Phase39_manifest_identity")
    fixed(row["source_schema_versions"], dict(SOURCE_SCHEMAS), "followup_source_schema_versions")
    validate_source_counts(row["source_counts"])
    fixed(row["content_scope"], CONTENT_SCOPE, "followup_source_content_scope")
    return copy.deepcopy(row)


def make_source_receipt(source_artifacts: list, source_counts: dict) -> dict:
    artifacts, counts = validate_source_artifacts(source_artifacts), validate_source_counts(source_counts)
    return validate_receipt({
        **common(RECEIPT_SCHEMA), "source_artifacts": artifacts,
        "source_phase39_witnesses_sha256": artifacts[1]["sha256"],
        "source_phase39_manifest_sha256": artifacts[-1]["sha256"],
        "source_schema_versions": dict(SOURCE_SCHEMAS), "source_counts": counts,
        "content_scope": CONTENT_SCOPE, "limitations": list(LIMITATIONS),
    })


def validate_relationships(queue: object, handoff: object, receipt: object) -> tuple[dict, dict, dict]:
    queue, handoff, receipt = validate_queue(queue), validate_handoff(handoff), validate_receipt(receipt)
    fixed(handoff, handoff_from_queue(queue), "followup_complete_queue_handoff_correspondence")
    for key in ("source_phase39_witnesses_sha256", "source_phase39_manifest_sha256"):
        fixed(queue[key], receipt[key], "followup_current_Phase39_source_relation")
    selected, source = queue["counts"], receipt["source_counts"]
    mappings = {"selected_reference_count": "matched_reference_count", "selected_projection_count": "matched_projection_count",
                "distinct_candidate_count": "matched_candidate_count", "recorded_present_projection_count": "matched_present_projection_count",
                "recorded_missing_projection_count": "matched_absence_projection_count"}
    if any(selected[key] > source[target] for key, target in mappings.items()):
        fail("selected_packets_exceed_current_QUERY_scope")
    # Whole packets can include unrequired file projections; required_file_count
    # must not be used as the distinct-file denominator for those packets.
    return queue, handoff, receipt
