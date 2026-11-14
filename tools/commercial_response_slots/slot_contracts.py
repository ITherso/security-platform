"""Closed unsubmitted response slots over recorded, unassigned task metadata."""
from __future__ import annotations

import copy
import hashlib
import re

from followup_contracts import (
    InputError, FALSE_FLAGS, parse_json, json_bytes, fixed, closed, integer,
    identifier, sha256, digest_id,
    QUEUE_SCHEMA as SOURCE_QUEUE_SCHEMA,
    HANDOFF_SCHEMA as SOURCE_HANDOFF_SCHEMA,
    RECEIPT_SCHEMA as SOURCE_RECEIPT_SCHEMA,
    MANIFEST_SCHEMA as SOURCE_MANIFEST_SCHEMA,
    COUNT_FIELDS as SOURCE_COUNT_FIELDS,
    validate_reference_packets as owner_reference_packets,
)
from task_binding import derive_task_binding, validate_task_record

REQUEST_SCHEMA = "termivar-offline-response-slot-request/v1"
SLOTS_SCHEMA = "termivar-offline-task-response-slots/v1"
TEMPLATE_SCHEMA = "termivar-offline-task-response-template/v1"
RECEIPT_SCHEMA = "termivar-offline-response-slot-source-receipt/v1"
MANIFEST_SCHEMA = "termivar-offline-response-slot-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-response-slot-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — TASK-BOUND RESPONSE SLOTS ONLY — NO RESPONSE OR OBSERVATION RECEIVED"
MAX_REQUEST_BYTES = 32 * 1024
MAX_SLOTS_BYTES = 256 * 1024
MAX_TEMPLATE_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
MAX_SELECTED_TASKS = MAX_REFERENCES = 8
MAX_PROJECTIONS = 64
SOURCE_NAMES = ("evidence-followup-queue.json", "analyst-handoff.json", "followup-source-receipt.json",
                "followup-summary.md", "manifest.json")
SOURCE_LIMITS = dict(zip(SOURCE_NAMES, (262144, 131072, 65536, 131072, 65536)))
SOURCE_SCHEMAS = dict(zip(SOURCE_NAMES, (SOURCE_QUEUE_SCHEMA, SOURCE_HANDOFF_SCHEMA,
                                      SOURCE_RECEIPT_SCHEMA, None, SOURCE_MANIFEST_SCHEMA)))
# The five owner sources have no workflow_flags member. Their 18 nested trust
# flags are preserved; the excluded sixth inspector's flat fields are not input.
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "trust_flags")
REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "source_phase40_queue_sha256",
                  "source_phase40_manifest_sha256", "selected_task_ids")
SLOT_FIELDS = ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest", "followup_kind",
               "task_status", "fulfillment_status", "slot_status", "submission", "submission_contract")
COUNT_FIELDS = ("selected_task_count", "selected_reference_count", "response_slot_count", "unsubmitted_slot_count",
                "submitted_response_count", "assigned_task_count", "observed_task_count")
CONTENT_SCOPE = "five_Phase40_artifact_internal_correspondence_only"
LIMITATIONS = (
    "recorded_pending_task_response_slots_only", "no_response_submission_or_observation_received",
    "prepared_unassigned_not_authorized_or_fulfilled", "whole_reference_packet_metadata_only",
    "binding_digest_not_signature_secret_or_anti_replay", "future_locator_requires_authorized_human_input",
    "source_files_not_reobserved", "upstream_guard_not_independently_verified",
    "internal_hashes_not_producer_authentication", "no_human_legal_customer_or_release_authority",
    "minimization_is_not_anonymization",
)


def fail(code: str) -> None:
    raise InputError("response_slots_invalid_" + code)


def common(schema: str) -> dict:
    if schema not in (SLOTS_SCHEMA, TEMPLATE_SCHEMA, RECEIPT_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "trust_flags": {flag: False for flag in FALSE_FLAGS}}


def _common_row(value: object, schema: str, fields: tuple, maximum: int) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *fields), "slots_closed_model_fields")
    fixed({key: row[key] for key in COMMON_FIELDS}, common(schema), "slots_common_fields")
    fixed(row["limitations"], list(LIMITATIONS), "slots_limitations")
    return row


def task_id(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"F[0-9]{4}", value) is None or not 1 <= int(value[1:]) <= 64:
        fail("original_task_id")
    return value


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "slots_request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "slots_request_schema")
    fixed(row["mode"], "demo", "slots_request_mode")
    identifier(row["request_reference"], "slots_request_reference")
    sha256(row["source_phase40_queue_sha256"], "slots_source_queue_sha256")
    sha256(row["source_phase40_manifest_sha256"], "slots_source_manifest_sha256")
    ids = row["selected_task_ids"]
    if type(ids) is not list or not 1 <= len(ids) <= MAX_SELECTED_TASKS:
        fail("selected_task_ids")
    for value in ids:
        task_id(value)
    if len(set(ids)) != len(ids):
        fail("duplicate_selected_task_id")
    return copy.deepcopy(row)


def submission_contract() -> dict:
    """Future field/type definitions only; no submitted values or parser."""
    return {"task_id": "string", "binding_digest": "sha256", "reported_presence": "present_or_missing",
            "observation_recorded_at": "timestamp_string", "observation_method": "string",
            "source_locator_description": "string", "evidence_sha256_if_available": "sha256_or_null"}


def _slot_task(slot: dict) -> dict:
    return validate_task_record({
        "task_id": slot["task_id"], "reference_id": slot["reference_id"], "candidate_id": slot["candidate_id"],
        "file_id": slot["file_id"], "recorded_source_file_presence": "missing",
        "followup_kind": slot["followup_kind"], "task_status": slot["task_status"],
        "fulfillment_status": slot["fulfillment_status"],
    })


def slot_counts(response_slots: object) -> dict:
    json_bytes(response_slots, maximum=MAX_SLOTS_BYTES)
    if type(response_slots) is not list or not 1 <= len(response_slots) <= MAX_SELECTED_TASKS:
        fail("response_slot_list")
    ids, digests, triples, references = [], [], [], set()
    for slot in response_slots:
        closed(slot, SLOT_FIELDS, "response_slot_fields")
        task = _slot_task(slot)
        sha256(slot["binding_digest"], "slot_binding_digest")
        fixed(slot["slot_status"], "awaiting_external_response", "slot_status")
        fixed(slot["submission"], None, "slot_submission_must_be_null")
        fixed(slot["submission_contract"], submission_contract(), "slot_future_field_definitions")
        ids.append(task["task_id"])
        digests.append(slot["binding_digest"])
        triples.append((task["reference_id"], task["candidate_id"], task["file_id"]))
        references.add(task["reference_id"])
    if (len(set(ids)) != len(ids) or len(set(digests)) != len(digests)
            or len(set(triples)) != len(triples)):
        fail("duplicate_task_or_binding")
    fixed(ids, sorted(ids), "original_queue_task_order")
    count = len(response_slots)
    return {"selected_task_count": count, "selected_reference_count": len(references),
            "response_slot_count": count, "unsubmitted_slot_count": count,
            "submitted_response_count": 0, "assigned_task_count": 0, "observed_task_count": 0}


def validate_slots(value: object) -> dict:
    row = _common_row(value, SLOTS_SCHEMA, ("source_phase40_queue_sha256", "source_phase40_manifest_sha256",
                      "request", "reference_packets", "response_slots", "counts", "limitations"), MAX_SLOTS_BYTES)
    request = validate_request(row["request"])
    for key in ("source_phase40_queue_sha256", "source_phase40_manifest_sha256"):
        fixed(row[key], request[key], "slots_request_source_binding")
    packets = owner_reference_packets(row["reference_packets"])
    counts = slot_counts(row["response_slots"])
    fixed(row["counts"], counts, "slots_exact_counts")
    fixed([slot["task_id"] for slot in row["response_slots"]], sorted(request["selected_task_ids"]),
          "slots_complete_selected_tasks")
    fixed([packet["reference_id"] for packet in packets],
          sorted({slot["reference_id"] for slot in row["response_slots"]}), "slots_only_task_reference_packets")
    by_reference = {packet["reference_id"]: packet for packet in packets}
    for slot in row["response_slots"]:
        task = _slot_task(slot)
        fixed(slot["binding_digest"], derive_task_binding(row["source_phase40_queue_sha256"], task),
              "slots_actual_shown_task_binding")
        packet = by_reference[task["reference_id"]]
        matching = [projection for projection in packet["projections"]
                    if projection["candidate_id"] == task["candidate_id"] and projection["file_id"] == task["file_id"]]
        if len(matching) != 1 or matching[0]["source_file_presence"] != "missing":
            fail("slot_missing_projection_binding")
        triple = {key: task[key] for key in ("reference_id", "candidate_id", "file_id")}
        if triple not in packet["supporting_projection_bindings"]:
            fail("slot_real_supporting_binding")
    return copy.deepcopy(row)


def validate_template(value: object) -> dict:
    row = _common_row(value, TEMPLATE_SCHEMA, ("source_phase40_queue_sha256", "source_phase40_manifest_sha256",
                      "slots_sha256", "request_reference", "template_entries", "counts", "limitations"), MAX_TEMPLATE_BYTES)
    for key in ("source_phase40_queue_sha256", "source_phase40_manifest_sha256", "slots_sha256"):
        sha256(row[key], "template_digest")
    identifier(row["request_reference"], "template_request_reference")
    entries = row["template_entries"]
    if type(entries) is not list or not 1 <= len(entries) <= MAX_SELECTED_TASKS:
        fail("template_entries")
    ids, digests = [], []
    for entry in entries:
        closed(entry, ("task_id", "binding_digest", "required_fields", "response_status", "response"), "template_entry_fields")
        ids.append(task_id(entry["task_id"]))
        digests.append(sha256(entry["binding_digest"], "template_binding_digest"))
        fixed(entry["required_fields"], submission_contract(), "template_future_field_definitions")
        fixed(entry["response_status"], "unsubmitted", "template_unsubmitted_status")
        fixed(entry["response"], None, "template_response_must_be_null")
    if len(set(ids)) != len(ids) or len(set(digests)) != len(digests):
        fail("duplicate_template_task_or_binding")
    fixed(ids, sorted(ids), "template_original_task_order")
    counts = closed(row["counts"], COUNT_FIELDS, "template_count_fields")
    for key in COUNT_FIELDS:
        integer(counts[key], "template_count", MAX_SELECTED_TASKS)
    if not 1 <= counts["selected_reference_count"] <= len(entries):
        fail("template_reference_count")
    expected = {"selected_task_count": len(entries), "selected_reference_count": counts["selected_reference_count"],
                "response_slot_count": len(entries), "unsubmitted_slot_count": len(entries),
                "submitted_response_count": 0, "assigned_task_count": 0, "observed_task_count": 0}
    fixed(counts, expected, "template_unsubmitted_counts")
    return copy.deepcopy(row)


def template_from_slots(slots: object) -> dict:
    slots = validate_slots(slots)
    return validate_template({
        **common(TEMPLATE_SCHEMA), "source_phase40_queue_sha256": slots["source_phase40_queue_sha256"],
        "source_phase40_manifest_sha256": slots["source_phase40_manifest_sha256"],
        "slots_sha256": hashlib.sha256(json_bytes(slots, maximum=MAX_SLOTS_BYTES)).hexdigest(),
        "request_reference": slots["request"]["request_reference"],
        "template_entries": [{"task_id": slot["task_id"], "binding_digest": slot["binding_digest"],
                              "required_fields": submission_contract(), "response_status": "unsubmitted", "response": None}
                             for slot in slots["response_slots"]],
        "counts": copy.deepcopy(slots["counts"]), "limitations": list(LIMITATIONS),
    })


def validate_source_artifacts(value: object) -> list:
    if type(value) is not list or len(value) != len(SOURCE_NAMES):
        fail("five_actual_Phase40_sources")
    for item, name in zip(value, SOURCE_NAMES):
        row = closed(item, ("name", "bytes", "sha256", "schema_version"), "slot_source_artifact_fields")
        fixed(row["name"], name, "slot_source_artifact_name")
        fixed(row["schema_version"], SOURCE_SCHEMAS[name], "slot_source_artifact_schema")
        if integer(row["bytes"], "slot_source_artifact_bytes", SOURCE_LIMITS[name]) == 0:
            fail("empty_source_artifact")
        sha256(row["sha256"], "slot_source_artifact_sha256")
    return copy.deepcopy(value)


def _source_seven(value: object, handoff: bool) -> dict:
    row = closed(value, SOURCE_COUNT_FIELDS, "original_Phase40_count_fields")
    for key in SOURCE_COUNT_FIELDS:
        integer(row[key], "original_Phase40_count", 8 if key == "selected_reference_count" else 64)
    projections, references = row["selected_projection_count"], row["selected_reference_count"]
    if (projections != row["recorded_present_projection_count"] + row["recorded_missing_projection_count"]
            or row["pending_task_count"] != row["recorded_missing_projection_count"]
            or row["distinct_candidate_count"] != projections or row["distinct_file_count"] > projections
            or references > projections or (projections > 0 and row["distinct_file_count"] == 0)
            or (not references and any(row.values())) or (references and not projections)
            or (handoff and references > row["pending_task_count"])):
        fail("original_Phase40_count_relations")
    return copy.deepcopy(row)


def validate_source_counts(value: object) -> dict:
    row = closed(value, ("queue_counts", "handoff_counts"), "original_Phase40_nested_counts")
    queue, handoff = _source_seven(row["queue_counts"], False), _source_seven(row["handoff_counts"], True)
    if (any(handoff[key] > queue[key] for key in SOURCE_COUNT_FIELDS)
            or handoff["pending_task_count"] != queue["pending_task_count"]
            or handoff["recorded_missing_projection_count"] != queue["recorded_missing_projection_count"]):
        fail("original_queue_handoff_count_correspondence")
    return {"queue_counts": queue, "handoff_counts": handoff}


def validate_receipt(value: object) -> dict:
    row = _common_row(value, RECEIPT_SCHEMA, ("source_artifacts", "source_phase40_queue_sha256",
                      "source_phase40_manifest_sha256", "source_counts", "selected_task_count",
                      "content_scope", "limitations"), MAX_RECEIPT_BYTES)
    artifacts = validate_source_artifacts(row["source_artifacts"])
    fixed(row["source_phase40_queue_sha256"], artifacts[0]["sha256"], "actual_Phase40_queue_identity")
    fixed(row["source_phase40_manifest_sha256"], artifacts[-1]["sha256"], "actual_Phase40_manifest_identity")
    source = validate_source_counts(row["source_counts"])
    selected = integer(row["selected_task_count"], "receipt_selected_task_count", MAX_SELECTED_TASKS)
    if selected == 0 or selected > source["queue_counts"]["pending_task_count"]:
        fail("receipt_selected_task_scope")
    fixed(row["content_scope"], CONTENT_SCOPE, "slot_source_content_scope")
    return copy.deepcopy(row)


def validate_relationships(slots: object, template: object, receipt: object) -> tuple[dict, dict, dict]:
    slots, template, receipt = validate_slots(slots), validate_template(template), validate_receipt(receipt)
    fixed(template, template_from_slots(slots), "slots_template_full_correspondence")
    for key in ("source_phase40_queue_sha256", "source_phase40_manifest_sha256"):
        fixed(slots[key], receipt[key], "current_Phase40_source_relation")
    fixed(receipt["selected_task_count"], slots["counts"]["selected_task_count"], "receipt_selected_task_count")
    projections = [projection for packet in slots["reference_packets"] for projection in packet["projections"]]
    selected = {"selected_reference_count": len(slots["reference_packets"]), "selected_projection_count": len(projections),
                "recorded_present_projection_count": sum(p["source_file_presence"] == "present" for p in projections),
                "recorded_missing_projection_count": sum(p["source_file_presence"] == "missing" for p in projections),
                "distinct_file_count": len({p["file_id"] for p in projections}),
                "distinct_candidate_count": len({p["candidate_id"] for p in projections})}
    for source_counts in receipt["source_counts"].values():
        if any(count > source_counts[key] for key, count in selected.items()):
            fail("selected_whole_packets_exceed_source_count_scope")
    return slots, template, receipt
