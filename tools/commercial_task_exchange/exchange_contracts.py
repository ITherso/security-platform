"""Closed portable task-exchange v1 wire protocol, standard library only.

This local protocol validates minimal recorded metadata correspondence. It is
not a source loader, general JSON framework, producer proof or authority token.
"""
from __future__ import annotations

import copy
import json
import re

REQUEST_SCHEMA = "termivar-offline-task-exchange-request/v1"
PORTABLE_REQUEST_SCHEMA = "termivar-offline-portable-task-request/v1"
RESPONSE_CONTRACT_SCHEMA = "termivar-offline-portable-response-contract/v1"
CAPSULE_SCHEMA = "termivar-offline-task-exchange-capsule/v1"
INDEX_SCHEMA = "termivar-offline-task-exchange-index/v1"
RECEIPT_SCHEMA = "termivar-offline-task-exchange-source-receipt/v1"
MANIFEST_SCHEMA = "termivar-offline-task-exchange-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-task-exchange-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — PORTABLE TASK REQUEST ONLY — NO TASK DISPATCH OR RESPONSE AUTHORIZED"
FALSE_FLAGS = (
    "source_inventory_updated", "scope_delta_applied", "component_ownership_verified",
    "dependency_closure_verified", "build_verified", "runtime_verified", "producer_verified",
    "human_review_verified", "license_review_completed", "redistribution_authorized",
    "release_authorized", "production_ready", "module_closure_verified",
    "compiler_resolution_verified", "reference_context_revalidated",
    "independent_observation_verified", "source_files_reobserved", "upstream_guard_independently_verified",
)
MAX_REQUEST_BYTES = 32 * 1024
MAX_CAPSULE_BYTES = MAX_EXPANDED_BYTES = MAX_INDEX_BYTES = MAX_SUMMARY_BYTES = 128 * 1024
MAX_RECEIPT_BYTES = MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
MAX_PORTABLE_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_CONTRACT_BYTES = MAX_CAPSULE_MANIFEST_BYTES = 32 * 1024
MAX_CAPSULE_README_BYTES = 4 * 1024
MAX_STRING = 512
MAX_DEPTH = 12
MAX_NODES = 20000
MAX_TASKS = 8
SOURCE_NAMES = ("deferred-intake-register.json", "intake-classification.json",
                "intake-source-receipt.json", "intake-summary.md", "manifest.json")
SOURCE_LIMITS = dict(zip(SOURCE_NAMES, (262144, 131072, 65536, 131072, 65536)))
SOURCE_SCHEMAS = dict(zip(SOURCE_NAMES, (
    "termivar-offline-deferred-intake-register/v1",
    "termivar-offline-deferred-intake-classification/v1",
    "termivar-offline-deferred-intake-source-receipt/v1", None,
    "termivar-offline-deferred-intake-manifest/v1",
)))
COMMON_FIELDS = ("schema_version", "demo_label", "demo_only", "trust_flags")
REQUEST_FIELDS = ("schema_version", "mode", "request_reference", "source_phase42_register_sha256",
                  "source_phase42_manifest_sha256", "selected_task_ids")
TASK_FIELDS = ("task_id", "reference_id", "candidate_id", "file_id", "binding_digest",
               "slot_status", "response_status", "candidate_present", "observation_verified", "task_completed")
COUNT_FIELDS = ("selected_task_count", "unsubmitted_request_count", "response_field_definition_count",
                "submitted_response_count", "verified_observation_count", "completed_task_count")
SOURCE_INTAKE_COUNT_FIELDS = (
    "selected_task_count", "selected_reference_count", "intake_entry_count", "awaiting_submission_count",
    "candidate_present_count", "structurally_compatible_count", "observation_verified_count", "completed_task_count",
)
SOURCE_SLOT_COUNT_FIELDS = (
    "selected_task_count", "selected_reference_count", "response_slot_count", "unsubmitted_slot_count",
    "submitted_response_count", "assigned_task_count", "observed_task_count",
)
SOURCE_PHASE40_COUNT_FIELDS = (
    "selected_reference_count", "selected_projection_count", "recorded_present_projection_count",
    "recorded_missing_projection_count", "pending_task_count", "distinct_file_count", "distinct_candidate_count",
)
CONTENT_SCOPE = "five_Phase42_artifact_internal_correspondence_only"
LIMITATIONS = (
    "recorded_pending_task_request_only", "portable_structure_not_source_truth",
    "binding_preserved_not_independently_recomputed", "minimal_task_metadata_no_reference_packets",
    "future_field_definitions_not_response_values", "not_dispatched_assigned_or_completed",
    "no_recipient_authentication_or_authorization", "internal_hashes_not_producer_authentication",
    "source_files_not_reobserved", "no_human_legal_customer_or_release_authority",
    "minimization_is_not_anonymization",
)


class InputError(ValueError):
    """The bounded task-exchange v1 structure was not satisfied."""


def fail(code: str) -> None:
    raise InputError("task_exchange_invalid_" + code)


def integer(value: object, code: str, maximum: int = 2**53 - 1) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        fail(code)
    return value


def closed(value: object, fields, code: str) -> dict:
    if (type(value) is not dict or any(type(key) is not str for key in value)
            or set(value) != set(fields)):
        fail(code)
    return value


def _tree(value: object) -> None:
    pending, nodes = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_NODES or depth > MAX_DEPTH:
            fail("tree_limit")
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    fail("key_type")
                pending.extend(((key, depth + 1), (child, depth + 1)))
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            if len(item) > MAX_STRING:
                fail("string_limit")
            item.encode("utf-8", "strict")
        elif type(item) is int:
            integer(item, "safe_integer")
        elif item is not None and type(item) is not bool:
            fail("value_type")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("duplicate_json_key")
        result[key] = value
    return result


def _parse_integer(text: str):
    if len(text) > 16:
        fail("integer_size")
    return integer(int(text), "safe_integer")


def _reject_number(_text: str):
    fail("non_integer_number")


def parse_json(raw: bytes, maximum: int = MAX_EXPANDED_BYTES) -> object:
    integer(maximum, "json_maximum", MAX_TOTAL_INPUT_BYTES)
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        fail("json_bytes")
    try:
        text = raw.decode("utf-8", "strict")
        if text.startswith("\ufeff"):
            fail("utf8_bom")
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_parse_integer,
                           parse_float=_reject_number, parse_constant=_reject_number)
        _tree(value)
        return value
    except InputError:
        raise
    except (UnicodeError, ValueError, RecursionError, TypeError, OverflowError):
        fail("strict_json")


def json_bytes(value: object, maximum: int = MAX_EXPANDED_BYTES) -> bytes:
    integer(maximum, "json_maximum", MAX_TOTAL_INPUT_BYTES)
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


def task_id(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"F[0-9]{4}", value) is None or not 1 <= int(value[1:]) <= 64:
        fail("original_task_id")
    return value


def common(schema: str) -> dict:
    if schema not in (PORTABLE_REQUEST_SCHEMA, RESPONSE_CONTRACT_SCHEMA, CAPSULE_SCHEMA,
                      INDEX_SCHEMA, RECEIPT_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema, "demo_label": DEMO_LABEL, "demo_only": True,
            "trust_flags": {flag: False for flag in FALSE_FLAGS}}


def _common_row(value: object, schema: str, fields: tuple, maximum: int) -> dict:
    json_bytes(value, maximum=maximum)
    row = closed(value, (*COMMON_FIELDS, *fields), "closed_model_fields")
    fixed({key: row[key] for key in COMMON_FIELDS}, common(schema), "common_fields")
    fixed(row["limitations"], list(LIMITATIONS), "limitations")
    return row


def _task_ids(value: object) -> list:
    if type(value) is not list or not 1 <= len(value) <= MAX_TASKS:
        fail("task_ids")
    for value_id in value:
        task_id(value_id)
    if len(set(value)) != len(value):
        fail("duplicate_task_id")
    return copy.deepcopy(value)


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "request_schema")
    fixed(row["mode"], "demo", "request_mode")
    identifier(row["request_reference"], "request_reference")
    sha256(row["source_phase42_register_sha256"], "source_register_sha256")
    sha256(row["source_phase42_manifest_sha256"], "source_manifest_sha256")
    _task_ids(row["selected_task_ids"])
    return copy.deepcopy(row)


def response_field_definitions() -> dict:
    return {"task_id": "string", "binding_digest": "sha256", "reported_presence": "present_or_missing",
            "observation_recorded_at": "timestamp_string", "observation_method": "string",
            "source_locator_description": "string", "evidence_sha256_if_available": "sha256_or_null"}


def validate_response_contract(value: object) -> dict:
    row = _common_row(value, RESPONSE_CONTRACT_SCHEMA, ("field_definitions", "limitations"), MAX_RESPONSE_CONTRACT_BYTES)
    fixed(row["field_definitions"], response_field_definitions(), "future_response_definitions")
    return copy.deepcopy(row)


def build_response_contract() -> dict:
    return validate_response_contract({**common(RESPONSE_CONTRACT_SCHEMA),
                                      "field_definitions": response_field_definitions(),
                                      "limitations": list(LIMITATIONS)})


def _counts_for_task_count(count: int) -> dict:
    if integer(count, "task_count", MAX_TASKS) == 0:
        fail("empty_task_count")
    return {"selected_task_count": count, "unsubmitted_request_count": count,
            "response_field_definition_count": len(response_field_definitions()),
            "submitted_response_count": 0, "verified_observation_count": 0, "completed_task_count": 0}


def exchange_counts(tasks: object) -> dict:
    json_bytes(tasks, maximum=MAX_PORTABLE_REQUEST_BYTES)
    if type(tasks) is not list or not 1 <= len(tasks) <= MAX_TASKS:
        fail("portable_task_list")
    ids, digests, triples = [], [], []
    for item in tasks:
        closed(item, TASK_FIELDS, "portable_task_fields")
        ids.append(task_id(item["task_id"]))
        digest_id(item["reference_id"], "rust-ref-", "portable_reference_id")
        identifier(item["candidate_id"], "portable_candidate_id")
        digest_id(item["file_id"], "candidate-file-", "portable_file_id")
        digests.append(sha256(item["binding_digest"], "inherited_binding_digest"))
        fixed(item["slot_status"], "awaiting_external_response", "portable_slot_status")
        fixed(item["response_status"], "unsubmitted", "portable_response_status")
        for key in ("candidate_present", "observation_verified", "task_completed"):
            fixed(item[key], False, "portable_unverified_pending_state")
        triples.append((item["reference_id"], item["candidate_id"], item["file_id"]))
    if len(set(ids)) != len(ids) or len(set(digests)) != len(digests) or len(set(triples)) != len(triples):
        fail("duplicate_task_or_binding")
    fixed(ids, sorted(ids), "original_task_order")
    return _counts_for_task_count(len(tasks))


def validate_portable_request(value: object) -> dict:
    row = _common_row(value, PORTABLE_REQUEST_SCHEMA, ("source_phase42_register_sha256",
                      "source_phase42_manifest_sha256", "request_reference", "tasks", "counts", "limitations"),
                      MAX_PORTABLE_REQUEST_BYTES)
    sha256(row["source_phase42_register_sha256"], "portable_source_register")
    sha256(row["source_phase42_manifest_sha256"], "portable_source_manifest")
    identifier(row["request_reference"], "portable_request_reference")
    fixed(row["counts"], exchange_counts(row["tasks"]), "portable_counts")
    return copy.deepcopy(row)


def validate_index(value: object) -> dict:
    row = _common_row(value, INDEX_SCHEMA, ("source_phase42_register_sha256", "source_phase42_manifest_sha256",
                      "capsule_sha256", "task_ids", "counts", "limitations"), MAX_INDEX_BYTES)
    for key in ("source_phase42_register_sha256", "source_phase42_manifest_sha256", "capsule_sha256"):
        sha256(row[key], "index_digest")
    ids = _task_ids(row["task_ids"])
    fixed(ids, sorted(ids), "index_original_task_order")
    fixed(row["counts"], _counts_for_task_count(len(ids)), "index_counts")
    return copy.deepcopy(row)


def make_exchange_index(envelope: object, capsule_sha256: str) -> dict:
    envelope = validate_portable_request(envelope)
    sha256(capsule_sha256, "actual_capsule_sha256")
    return validate_index({
        **common(INDEX_SCHEMA), "source_phase42_register_sha256": envelope["source_phase42_register_sha256"],
        "source_phase42_manifest_sha256": envelope["source_phase42_manifest_sha256"],
        "capsule_sha256": capsule_sha256, "task_ids": [task["task_id"] for task in envelope["tasks"]],
        "counts": copy.deepcopy(envelope["counts"]), "limitations": list(LIMITATIONS),
    })


def validate_source_artifacts(value: object) -> list:
    if type(value) is not list or len(value) != len(SOURCE_NAMES):
        fail("five_actual_Phase42_sources")
    for item, name in zip(value, SOURCE_NAMES):
        row = closed(item, ("name", "bytes", "sha256", "schema_version"), "source_artifact_fields")
        fixed(row["name"], name, "source_artifact_name")
        fixed(row["schema_version"], SOURCE_SCHEMAS[name], "source_artifact_schema")
        if integer(row["bytes"], "source_artifact_bytes", SOURCE_LIMITS[name]) == 0:
            fail("empty_source_artifact")
        sha256(row["sha256"], "source_artifact_sha256")
    return copy.deepcopy(value)


def _source_intake_counts(value: object) -> dict:
    row = closed(value, SOURCE_INTAKE_COUNT_FIELDS, "source_Phase42_count_fields")
    for key in SOURCE_INTAKE_COUNT_FIELDS:
        integer(row[key], "source_Phase42_count", MAX_TASKS)
    count = row["selected_task_count"]
    if count == 0 or not 1 <= row["selected_reference_count"] <= count:
        fail("source_Phase42_scope")
    fixed(row, {"selected_task_count": count, "selected_reference_count": row["selected_reference_count"],
                "intake_entry_count": count, "awaiting_submission_count": count,
                "candidate_present_count": 0, "structurally_compatible_count": 0,
                "observation_verified_count": 0, "completed_task_count": 0}, "source_Phase42_deferred_counts")
    return copy.deepcopy(row)


def _source_slot_counts(value: object) -> dict:
    row = closed(value, SOURCE_SLOT_COUNT_FIELDS, "source_Phase41_count_fields")
    for key in SOURCE_SLOT_COUNT_FIELDS:
        integer(row[key], "source_Phase41_count", MAX_TASKS)
    count = row["selected_task_count"]
    if count == 0 or not 1 <= row["selected_reference_count"] <= count:
        fail("source_Phase41_scope")
    fixed(row, {"selected_task_count": count, "selected_reference_count": row["selected_reference_count"],
                "response_slot_count": count, "unsubmitted_slot_count": count,
                "submitted_response_count": 0, "assigned_task_count": 0, "observed_task_count": 0},
          "source_Phase41_unsubmitted_counts")
    return copy.deepcopy(row)


def _source_phase40_counts(value: object, handoff: bool) -> dict:
    row = closed(value, SOURCE_PHASE40_COUNT_FIELDS, "source_Phase40_count_fields")
    for key in SOURCE_PHASE40_COUNT_FIELDS:
        integer(row[key], "source_Phase40_count", 8 if key == "selected_reference_count" else 64)
    projections, references = row["selected_projection_count"], row["selected_reference_count"]
    if (projections != row["recorded_present_projection_count"] + row["recorded_missing_projection_count"]
            or row["pending_task_count"] != row["recorded_missing_projection_count"]
            or row["distinct_candidate_count"] != projections or row["distinct_file_count"] > projections
            or references > projections or (projections > 0 and row["distinct_file_count"] == 0)
            or (not references and any(row.values())) or (references and not projections)
            or (handoff and references > row["pending_task_count"])):
        fail("source_Phase40_count_relations")
    return copy.deepcopy(row)


def validate_source_counts(value: object) -> dict:
    row = closed(value, ("register_counts", "classification_counts", "phase41_counts"), "six_source_count_scopes")
    register = _source_intake_counts(row["register_counts"])
    classification = _source_intake_counts(row["classification_counts"])
    fixed(classification, register, "source_Phase42_register_classification_counts")
    phase41 = closed(row["phase41_counts"], ("slots_counts", "template_counts", "phase40_counts"), "source_Phase41_scopes")
    slots, template = _source_slot_counts(phase41["slots_counts"]), _source_slot_counts(phase41["template_counts"])
    fixed(template, slots, "source_Phase41_slot_template_counts")
    phase40 = closed(phase41["phase40_counts"], ("queue_counts", "handoff_counts"), "source_Phase40_scopes")
    queue, handoff = _source_phase40_counts(phase40["queue_counts"], False), _source_phase40_counts(phase40["handoff_counts"], True)
    if (any(handoff[key] > queue[key] for key in SOURCE_PHASE40_COUNT_FIELDS)
            or handoff["pending_task_count"] != queue["pending_task_count"]
            or handoff["recorded_missing_projection_count"] != queue["recorded_missing_projection_count"]):
        fail("source_Phase40_queue_handoff_counts")
    if any(slots["selected_task_count"] > group["pending_task_count"]
           or slots["selected_reference_count"] > group["selected_reference_count"] for group in (queue, handoff)):
        fail("source_Phase41_scope_exceeds_parent")
    if (register["selected_task_count"] > slots["selected_task_count"]
            or register["selected_reference_count"] > slots["selected_reference_count"]):
        fail("source_Phase42_scope_exceeds_slots")
    return {"register_counts": register, "classification_counts": classification,
            "phase41_counts": {"slots_counts": slots, "template_counts": template,
                               "phase40_counts": {"queue_counts": queue, "handoff_counts": handoff}}}


def validate_receipt(value: object) -> dict:
    row = _common_row(value, RECEIPT_SCHEMA, ("source_artifacts", "source_phase42_register_sha256",
                      "source_phase42_manifest_sha256", "source_schema_versions", "source_counts",
                      "content_scope", "limitations"), MAX_RECEIPT_BYTES)
    artifacts = validate_source_artifacts(row["source_artifacts"])
    fixed(row["source_phase42_register_sha256"], artifacts[0]["sha256"], "actual_Phase42_register_identity")
    fixed(row["source_phase42_manifest_sha256"], artifacts[-1]["sha256"], "actual_Phase42_manifest_identity")
    fixed(row["source_schema_versions"], dict(SOURCE_SCHEMAS), "source_schema_versions")
    validate_source_counts(row["source_counts"])
    fixed(row["content_scope"], CONTENT_SCOPE, "source_content_scope")
    return copy.deepcopy(row)


def validate_relationships(envelope: object, index: object, receipt: object) -> tuple[dict, dict, dict]:
    envelope, index, receipt = validate_portable_request(envelope), validate_index(index), validate_receipt(receipt)
    fixed(index, make_exchange_index(envelope, index["capsule_sha256"]), "portable_index_correspondence")
    for key in ("source_phase42_register_sha256", "source_phase42_manifest_sha256"):
        fixed(envelope[key], receipt[key], "current_Phase42_source_correspondence")
    counts = receipt["source_counts"]["register_counts"]
    if (envelope["counts"]["selected_task_count"] > counts["selected_task_count"]
            or envelope["counts"]["unsubmitted_request_count"] > counts["awaiting_submission_count"]
            or len({task["reference_id"] for task in envelope["tasks"]}) > counts["selected_reference_count"]):
        fail("portable_selection_exceeds_recorded_source_scope")
    return envelope, index, receipt
