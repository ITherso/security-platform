"""Closed derivation request/ledger contracts; reuse the Phase33 wire parser.

This is metadata correspondence, not an evaluator or source/producer proof.
"""
from __future__ import annotations

import copy

from capsule_contracts import (
    InputError, FALSE_FLAGS, MAX_ZIP_BYTES, MAX_MEMBER_BYTES,
    closed, integer, identifier, sha256, reference_ids, fixed,
    parse_json, json_bytes, validate_capsule,
)

REQUEST_SCHEMA = "termivar-offline-capsule-derivation-request/v1"
LEDGER_SCHEMA = "termivar-offline-capsule-derivation-ledger/v1"
MANIFEST_SCHEMA = "termivar-offline-capsule-derivation-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-capsule-derivation-inspection/v1"
DEMO_LABEL = "OFFLINE DEMONSTRATION — CAPSULE SUBSET ONLY — NO ORIGINAL SOURCE OR PRODUCER VERIFICATION"
MAX_REQUEST_BYTES = 32 * 1024
MAX_LEDGER_BYTES = 64 * 1024
MAX_SUMMARY_BYTES = 128 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_TOTAL_INPUT_BYTES = 1024 * 1024
DERIVATION_CONSTRAINTS = {
    "max_request_bytes": MAX_REQUEST_BYTES,
    "max_source_zip_bytes": MAX_ZIP_BYTES,
    "max_derived_zip_bytes": MAX_ZIP_BYTES,
    "max_ledger_bytes": MAX_LEDGER_BYTES,
    "max_summary_bytes": MAX_SUMMARY_BYTES,
    "max_total_input_bytes": MAX_TOTAL_INPUT_BYTES,
    "max_selected_references": 8,
    "preserve_selected_results_exactly": True,
    "require_proper_reference_subset": True,
}
REQUEST_FIELDS = ("schema_version", "mode", "derivation_reference", "source_capsule_sha256",
                  "selected_reference_ids", "derivation_constraints")
COMMON_FIELDS = ("schema_version", "derivation_reference", "demo_label", "demo_only", *FALSE_FLAGS)
COUNT_FIELDS = ("requested_reference_count", "provided_reference_count", "withheld_reference_count",
                "unavailable_reference_count", "projection_count", "unique_candidate_count",
                "unique_file_count", "present_projection_count", "absence_projection_count")
SUBSET_RELATION = "strict_reference_subset_with_exact_selected_results"
LIMITATIONS = (
    "source_and_derived_capsule_correspondence_only",
    "source_files_not_reobserved", "original_phase31_32_artifacts_not_read",
    "upstream_guard_not_independently_verified", "no_current_freshness_or_future_validity",
    "hashes_are_not_producer_signatures_or_attestation",
    "no_user_authority_compiler_ownership_or_release_proof",
    "omitted_reference_metadata_not_exported", "minimization_is_not_anonymization",
)


def fail(code: str) -> None:
    raise InputError("capsule_derivation_invalid_" + code)


def validate_request(value: object) -> dict:
    json_bytes(value, maximum=MAX_REQUEST_BYTES)
    row = closed(value, REQUEST_FIELDS, "derivation_request_fields")
    fixed(row["schema_version"], REQUEST_SCHEMA, "derivation_request_schema")
    fixed(row["mode"], "demo", "derivation_request_mode")
    identifier(row["derivation_reference"], "derivation_reference")
    sha256(row["source_capsule_sha256"], "source_capsule_sha256")
    reference_ids(row["selected_reference_ids"])
    fixed(row["derivation_constraints"], DERIVATION_CONSTRAINTS, "derivation_constraints")
    return copy.deepcopy(row)


def common(schema: str, derivation_reference: str) -> dict:
    if schema not in (LEDGER_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA):
        fail("schema")
    return {"schema_version": schema,
            "derivation_reference": identifier(derivation_reference, "derivation_reference"),
            "demo_label": DEMO_LABEL, "demo_only": True,
            **{flag: False for flag in FALSE_FLAGS}}


def validate_identity(value: object) -> dict:
    row = closed(value, ("bytes", "sha256", "capsule_reference"), "capsule_byte_identity_fields")
    if integer(row["bytes"], "capsule_bytes", MAX_ZIP_BYTES) == 0:
        fail("empty_capsule")
    sha256(row["sha256"], "capsule_sha256")
    identifier(row["capsule_reference"], "capsule_reference")
    return copy.deepcopy(row)


def _counts(value: object) -> dict:
    row = closed(value, COUNT_FIELDS, "capsule_counts_fields")
    for key in COUNT_FIELDS:
        integer(row[key], "capsule_count", 64)
    refs, projections = row["requested_reference_count"], row["projection_count"]
    if (not 1 <= refs <= 8
            or refs != sum(row[k] for k in ("provided_reference_count", "withheld_reference_count", "unavailable_reference_count"))
            or projections != row["present_projection_count"] + row["absence_projection_count"]
            or row["unique_candidate_count"] != projections
            or not 0 <= row["unique_file_count"] <= projections
            or (projections > 0 and row["unique_file_count"] == 0)
            or row["provided_reference_count"] > projections
            or (row["provided_reference_count"] == 0 and projections > 0)):
        fail("counts")
    return row


def validate_ledger(value: object) -> dict:
    json_bytes(value, maximum=MAX_LEDGER_BYTES)
    row = closed(value, (*COMMON_FIELDS, "request", "source_capsule", "derived_capsule",
                         "source_counts", "derived_counts", "subset_relation", "limitations"), "derivation_ledger_fields")
    fixed({k: row[k] for k in COMMON_FIELDS}, common(LEDGER_SCHEMA, row["derivation_reference"]), "derivation_ledger_common")
    request = validate_request(row["request"])
    fixed(request["derivation_reference"], row["derivation_reference"], "request_ledger_reference")
    source = validate_identity(row["source_capsule"])
    derived = validate_identity(row["derived_capsule"])
    fixed(source["sha256"], request["source_capsule_sha256"], "source_request_hash")
    fixed(derived["capsule_reference"], request["derivation_reference"], "derived_capsule_reference")
    if source["capsule_reference"] == derived["capsule_reference"] or source["sha256"] == derived["sha256"]:
        fail("distinct_capsule_identities")
    source_counts, derived_counts = _counts(row["source_counts"]), _counts(row["derived_counts"])
    if (derived_counts["requested_reference_count"] != len(request["selected_reference_ids"])
            or derived_counts["requested_reference_count"] >= source_counts["requested_reference_count"]
            or any(derived_counts[k] > source_counts[k] for k in COUNT_FIELDS)):
        fail("strict_subset_counts")
    fixed(row["subset_relation"], SUBSET_RELATION, "subset_relation")
    fixed(row["limitations"], list(LIMITATIONS), "derivation_limitations")
    return copy.deepcopy(row)


def make_ledger(request: dict, source_model: dict, derived_model: dict,
                source_identity: dict, derived_identity: dict) -> dict:
    # Lazy import permits a single closed protocol layer without a module cycle.
    from disclosure_integrity import assert_monotonic_disclosure

    request = validate_request(request)
    source_model, derived_model = validate_capsule(source_model), validate_capsule(derived_model)
    assert_monotonic_disclosure(source_model, derived_model, request)
    source_identity, derived_identity = validate_identity(source_identity), validate_identity(derived_identity)
    fixed(source_identity["capsule_reference"], source_model["capsule_reference"], "source_model_identity")
    fixed(derived_identity["capsule_reference"], derived_model["capsule_reference"], "derived_model_identity")
    return validate_ledger({
        **common(LEDGER_SCHEMA, request["derivation_reference"]),
        "request": request, "source_capsule": source_identity, "derived_capsule": derived_identity,
        "source_counts": copy.deepcopy(source_model["counts"]),
        "derived_counts": copy.deepcopy(derived_model["counts"]),
        "subset_relation": SUBSET_RELATION, "limitations": list(LIMITATIONS),
    })
