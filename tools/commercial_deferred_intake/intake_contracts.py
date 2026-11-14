"""Closed deferred intake correspondence, never candidate observation proof."""
from __future__ import annotations

import copy
import hashlib

from slot_contracts import (
    InputError, FALSE_FLAGS, parse_json, json_bytes, fixed, closed, integer,
    identifier, sha256, digest_id, task_id,
    SLOTS_SCHEMA as SOURCE_SLOTS_SCHEMA,
    TEMPLATE_SCHEMA as SOURCE_TEMPLATE_SCHEMA,
    RECEIPT_SCHEMA as SOURCE_RECEIPT_SCHEMA,
    MANIFEST_SCHEMA as SOURCE_MANIFEST_SCHEMA,
    COUNT_FIELDS as SOURCE_SLOT_COUNT_FIELDS,
    owner_reference_packets,
    validate_source_counts as owner_phase40_counts,
)

REQUEST_SCHEMA = "termivar-offline-deferred-intake-request/v1"
INTAKE_SCHEMA = "termivar-offline-deferred-intake-register/v1"
CLASSIFICATION_SCHEMA = "termivar-offline-deferred-intake-classification/v1"
RECEIPT_SCHEMA = "termivar-offline-deferred-intake-source-receipt/v1"
MANIFEST_SCHEMA = "termivar-offline-deferred-intake-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-deferred-intake-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — DEFERRED RESPONSE INTAKE ONLY — NO CANDIDATE RESPONSE RECEIVED"
MAX_REQUEST_BYTES = 32 * 1024
MAX_INTAKE_BYTES = 256 * 1024
MAX_CLASSIFICATION_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
MAX_SELECTED_TASKS = MAX_REFERENCES = 8
MAX_PROJECTIONS = 64
SOURCE_NAMES = ("task-response-slots.json", "response-template.json", "response-slot-source-receipt.json",
                "response-slot-summary.md", "manifest.json")
SOURCE_LIMITS = dict(zip(SOURCE_NAMES, (262144, 131072, 65536, 131072, 65536)))
SOURCE_SCHEMAS = dict(zip(SOURCE_NAMES, (SOURCE_SLOTS_SCHEMA, SOURCE_TEMPLATE_SCHEMA,
                                      SOURCE_RECEIPT_SCHEMA, None, SOURCE_MANIFEST_SCHEMA)))
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "trust_flags")
REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "source_phase41_slots_sha256",
                  "source_phase41_manifest_sha256", "selected_task_ids", "candidate_source")
ENTRY_FIELDS = ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest", "slot_status",
                "response_status", "candidate_present", "candidate_classification", "candidate_response")
CLASSIFICATION_FIELDS = ("task_id", "binding_digest", "intake_status", "structural_result",
                         "observation_verified", "task_completed")
COUNT_FIELDS = ("selected_task_count", "selected_reference_count", "intake_entry_count", "awaiting_submission_count",
                "candidate_present_count", "structurally_compatible_count", "observation_verified_count", "completed_task_count")
CONTENT_SCOPE = "five_Phase41_artifact_internal_correspondence_only"
LIMITATIONS = (
    "recorded_unsubmitted_template_intake_only", "no_candidate_supplied_or_structurally_evaluated",
    "structural_compatibility_is_not_observation_verification", "binding_match_is_not_submission_authorization",
    "whole_reference_packet_metadata_only", "original_binding_not_independently_recomputed_from_new_outputs",
    "source_files_not_reobserved", "upstream_guard_not_independently_verified",
    "internal_hashes_not_producer_authentication", "no_human_legal_customer_or_release_authority",
    "minimization_is_not_anonymization",
)


def fail(code: str) -> None:
    raise InputError("deferred_intake_invalid_" + code)


def common(schema: str) -> dict:
    if schema not in (INTAKE_SCHEMA, CLASSIFICATION_SCHEMA, RECEIPT_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "trust_flags": {flag: False for flag in FALSE_FLAGS}}


def _common_row(value: object, schema: str, fields: tuple, maximum: int) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *fields), "intake_closed_model_fields")
    fixed({key: row[key] for key in COMMON_FIELDS}, common(schema), "intake_common_fields")
    fixed(row["limitations"], list(LIMITATIONS), "intake_limitations")
    return row


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "intake_request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "intake_request_schema")
    fixed(row["mode"], "demo", "intake_request_mode")
    fixed(row["candidate_source"], "existing_unsubmitted_template", "intake_candidate_source")
    identifier(row["request_reference"], "intake_request_reference")
    sha256(row["source_phase41_slots_sha256"], "intake_source_slots_sha256")
    sha256(row["source_phase41_manifest_sha256"], "intake_source_manifest_sha256")
    ids = row["selected_task_ids"]
    if type(ids) is not list or not 1 <= len(ids) <= MAX_SELECTED_TASKS:
        fail("selected_task_ids")
    for value in ids:
        task_id(value)
    if len(set(ids)) != len(ids):
        fail("duplicate_selected_task_id")
    return copy.deepcopy(row)


def intake_counts(intake_entries: object) -> dict:
    json_bytes(intake_entries, maximum=MAX_INTAKE_BYTES)
    if type(intake_entries) is not list or not 1 <= len(intake_entries) <= MAX_SELECTED_TASKS:
        fail("intake_entry_list")
    ids, digests, triples, references = [], [], [], set()
    for entry in intake_entries:
        closed(entry, ENTRY_FIELDS, "intake_entry_fields")
        ids.append(task_id(entry["task_id"]))
        digest_id(entry["reference_id"], "rust-ref-", "intake_reference_id")
        identifier(entry["candidate_id"], "intake_candidate_id")
        digest_id(entry["file_id"], "candidate-file-", "intake_file_id")
        digests.append(sha256(entry["binding_digest"], "intake_inherited_binding_digest"))
        fixed(entry["slot_status"], "awaiting_external_response", "intake_slot_status")
        fixed(entry["response_status"], "unsubmitted", "intake_response_status")
        fixed(entry["candidate_present"], False, "intake_candidate_absent")
        fixed(entry["candidate_classification"], "no_candidate_supplied", "intake_no_candidate_classification")
        fixed(entry["candidate_response"], None, "intake_candidate_response_must_be_null")
        triples.append((entry["reference_id"], entry["candidate_id"], entry["file_id"]))
        references.add(entry["reference_id"])
    if len(set(ids)) != len(ids) or len(set(digests)) != len(digests) or len(set(triples)) != len(triples):
        fail("duplicate_task_or_binding")
    fixed(ids, sorted(ids), "intake_original_task_order")
    count = len(intake_entries)
    return {"selected_task_count": count, "selected_reference_count": len(references),
            "intake_entry_count": count, "awaiting_submission_count": count,
            "candidate_present_count": 0, "structurally_compatible_count": 0,
            "observation_verified_count": 0, "completed_task_count": 0}


def validate_intake(value: object) -> dict:
    row = _common_row(value, INTAKE_SCHEMA, ("source_phase41_slots_sha256", "source_phase41_manifest_sha256",
                      "request", "reference_packets", "intake_entries", "counts", "limitations"), MAX_INTAKE_BYTES)
    request = validate_request(row["request"])
    for key in ("source_phase41_slots_sha256", "source_phase41_manifest_sha256"):
        fixed(row[key], request[key], "intake_request_source_binding")
    packets = owner_reference_packets(row["reference_packets"])
    fixed(row["counts"], intake_counts(row["intake_entries"]), "intake_exact_counts")
    fixed([entry["task_id"] for entry in row["intake_entries"]], sorted(request["selected_task_ids"]),
          "intake_complete_selected_tasks")
    fixed([packet["reference_id"] for packet in packets],
          sorted({entry["reference_id"] for entry in row["intake_entries"]}), "intake_only_task_reference_packets")
    by_reference = {packet["reference_id"]: packet for packet in packets}
    for entry in row["intake_entries"]:
        packet = by_reference[entry["reference_id"]]
        matching = [projection for projection in packet["projections"]
                    if projection["candidate_id"] == entry["candidate_id"] and projection["file_id"] == entry["file_id"]]
        if len(matching) != 1 or matching[0]["source_file_presence"] != "missing":
            fail("intake_recorded_missing_projection_binding")
        triple = {key: entry[key] for key in ("reference_id", "candidate_id", "file_id")}
        if triple not in packet["supporting_projection_bindings"]:
            fail("intake_real_supporting_binding")
        # The inherited binding uses parent Phase40 queue context, absent from
        # this new wire. Never rederive it with the current Phase41 slots hash.
        # The full-source owner validates it; this wire checks correspondence.
    return copy.deepcopy(row)


def validate_classification(value: object) -> dict:
    row = _common_row(value, CLASSIFICATION_SCHEMA, ("source_phase41_slots_sha256", "source_phase41_manifest_sha256",
                      "intake_register_sha256", "task_classifications", "counts", "limitations"), MAX_CLASSIFICATION_BYTES)
    for key in ("source_phase41_slots_sha256", "source_phase41_manifest_sha256", "intake_register_sha256"):
        sha256(row[key], "classification_digest")
    classifications = row["task_classifications"]
    if type(classifications) is not list or not 1 <= len(classifications) <= MAX_SELECTED_TASKS:
        fail("task_classifications")
    ids, digests = [], []
    for item in classifications:
        closed(item, CLASSIFICATION_FIELDS, "actual_deferred_classification_fields")
        ids.append(task_id(item["task_id"]))
        digests.append(sha256(item["binding_digest"], "classification_inherited_binding"))
        fixed(item["intake_status"], "awaiting_submission", "classification_awaiting_submission")
        fixed(item["structural_result"], "not_evaluated_no_candidate", "classification_not_evaluated")
        fixed(item["observation_verified"], False, "classification_observation_unverified")
        fixed(item["task_completed"], False, "classification_task_incomplete")
    if len(set(ids)) != len(ids) or len(set(digests)) != len(digests):
        fail("duplicate_classification_task_or_binding")
    fixed(ids, sorted(ids), "classification_original_task_order")
    counts = closed(row["counts"], COUNT_FIELDS, "classification_count_fields")
    for key in COUNT_FIELDS:
        integer(counts[key], "classification_count", MAX_SELECTED_TASKS)
    if not 1 <= counts["selected_reference_count"] <= len(classifications):
        fail("classification_reference_count")
    fixed(counts, {"selected_task_count": len(classifications), "selected_reference_count": counts["selected_reference_count"],
                   "intake_entry_count": len(classifications), "awaiting_submission_count": len(classifications),
                   "candidate_present_count": 0, "structurally_compatible_count": 0,
                   "observation_verified_count": 0, "completed_task_count": 0}, "classification_deferred_counts")
    return copy.deepcopy(row)


def classification_from_intake(intake: object) -> dict:
    intake = validate_intake(intake)
    return validate_classification({
        **common(CLASSIFICATION_SCHEMA), "source_phase41_slots_sha256": intake["source_phase41_slots_sha256"],
        "source_phase41_manifest_sha256": intake["source_phase41_manifest_sha256"],
        "intake_register_sha256": hashlib.sha256(json_bytes(intake, maximum=MAX_INTAKE_BYTES)).hexdigest(),
        "task_classifications": [{"task_id": entry["task_id"], "binding_digest": entry["binding_digest"],
                                  "intake_status": "awaiting_submission", "structural_result": "not_evaluated_no_candidate",
                                  "observation_verified": False, "task_completed": False}
                                 for entry in intake["intake_entries"]],
        "counts": copy.deepcopy(intake["counts"]), "limitations": list(LIMITATIONS),
    })


def validate_source_artifacts(value: object) -> list:
    if type(value) is not list or len(value) != len(SOURCE_NAMES):
        fail("five_actual_Phase41_sources")
    for item, name in zip(value, SOURCE_NAMES):
        row = closed(item, ("name", "bytes", "sha256", "schema_version"), "intake_source_artifact_fields")
        fixed(row["name"], name, "intake_source_artifact_name")
        fixed(row["schema_version"], SOURCE_SCHEMAS[name], "intake_source_artifact_schema")
        if integer(row["bytes"], "intake_source_artifact_bytes", SOURCE_LIMITS[name]) == 0:
            fail("empty_source_artifact")
        sha256(row["sha256"], "intake_source_artifact_sha256")
    return copy.deepcopy(value)


def _source_slot_counts(value: object) -> dict:
    row = closed(value, SOURCE_SLOT_COUNT_FIELDS, "original_Phase41_slot_count_fields")
    for key in SOURCE_SLOT_COUNT_FIELDS:
        integer(row[key], "original_Phase41_slot_count", MAX_SELECTED_TASKS)
    count = row["selected_task_count"]
    if count == 0 or not 1 <= row["selected_reference_count"] <= count:
        fail("original_Phase41_selected_scope")
    fixed(row, {"selected_task_count": count, "selected_reference_count": row["selected_reference_count"],
                "response_slot_count": count, "unsubmitted_slot_count": count,
                "submitted_response_count": 0, "assigned_task_count": 0, "observed_task_count": 0},
          "original_Phase41_unsubmitted_counts")
    return copy.deepcopy(row)


def validate_source_counts(value: object) -> dict:
    row = closed(value, ("slots_counts", "template_counts", "phase40_counts"), "intake_four_source_count_scopes")
    slots, template = _source_slot_counts(row["slots_counts"]), _source_slot_counts(row["template_counts"])
    fixed(template, slots, "original_Phase41_template_slot_counts")
    phase40 = owner_phase40_counts(row["phase40_counts"])
    if any(slots["selected_task_count"] > group["pending_task_count"]
           or slots["selected_reference_count"] > group["selected_reference_count"] for group in phase40.values()):
        fail("original_Phase41_scope_exceeds_parent_counts")
    return {"slots_counts": slots, "template_counts": template, "phase40_counts": phase40}


def validate_receipt(value: object) -> dict:
    row = _common_row(value, RECEIPT_SCHEMA, ("source_artifacts", "source_phase41_slots_sha256",
                      "source_phase41_manifest_sha256", "source_schema_versions", "source_counts",
                      "content_scope", "limitations"), MAX_RECEIPT_BYTES)
    artifacts = validate_source_artifacts(row["source_artifacts"])
    fixed(row["source_phase41_slots_sha256"], artifacts[0]["sha256"], "actual_Phase41_slots_identity")
    fixed(row["source_phase41_manifest_sha256"], artifacts[-1]["sha256"], "actual_Phase41_manifest_identity")
    fixed(row["source_schema_versions"], dict(SOURCE_SCHEMAS), "intake_source_schema_versions")
    validate_source_counts(row["source_counts"])
    fixed(row["content_scope"], CONTENT_SCOPE, "intake_source_content_scope")
    return copy.deepcopy(row)


def validate_relationships(intake: object, classification: object, receipt: object) -> tuple[dict, dict, dict]:
    intake, classification, receipt = validate_intake(intake), validate_classification(classification), validate_receipt(receipt)
    fixed(classification, classification_from_intake(intake), "intake_classification_full_correspondence")
    for key in ("source_phase41_slots_sha256", "source_phase41_manifest_sha256"):
        fixed(intake[key], receipt[key], "current_Phase41_source_relation")
    source = receipt["source_counts"]
    if (intake["counts"]["selected_task_count"] > source["slots_counts"]["selected_task_count"]
            or intake["counts"]["selected_reference_count"] > source["slots_counts"]["selected_reference_count"]):
        fail("selected_intake_exceeds_original_slots_scope")
    projections = [projection for packet in intake["reference_packets"] for projection in packet["projections"]]
    selected = {"selected_reference_count": len(intake["reference_packets"]), "selected_projection_count": len(projections),
                "recorded_present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
                "recorded_missing_projection_count": sum(p["source_file_presence"] == "missing" for p in projections),
                "distinct_file_count": len({p["file_id"] for p in projections}),
                "distinct_candidate_count": len({p["candidate_id"] for p in projections})}
    for group in source["phase40_counts"].values():
        if any(count > group[key] for key, count in selected.items()):
            fail("selected_whole_packets_exceed_original_parent_scope")
    return intake, classification, receipt
