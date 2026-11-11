"""Bind explicit evidence to exact old records, without changing Phase24."""
from __future__ import annotations

from copy import deepcopy

from .evidence_contracts import (
    InputError, LEDGER_SCHEMA, MAX_BINDING_REQUESTS, MAX_EVIDENCE_SOURCES,
    MAX_RECORDS, common, record_digest,
)


_STATUS_ORDER = (
    "binding_conflict", "binding_ambiguous", "evidence_unsupported",
    "source_not_verified", "evidence_present", "evidence_missing",
)
_FORMAT_BY_KIND = {
    "first_party_license_file": "license_header_observed",
    "dependency_license_file": "license_header_observed",
    "package_metadata": "metadata_declaration_observed",
    "source_manifest_declaration": "metadata_declaration_observed",
}


def _binding(subject: dict, source: dict, request: dict, manifest_refs: set[str]) -> dict:
    status, reason, matched = "binding_ambiguous", "source_file_reference_not_matched", None
    labels = list(source["observed_license_labels"])
    selector_matches = (
        request["subject_type"] == subject["subject_type"]
        and request["subject_id"] == subject["subject_id"]
        and request["source_record_sha256"] == subject["source_record_sha256"]
    )
    references = [ref for ref in source["baseline_file_refs"]
                  if ref in subject["base_source_file_refs"]]
    if len(references) == 1:
        matched = references[0]
    if not selector_matches:
        status, reason = "binding_conflict", "source_selector_mismatch"
        matched = None
    elif not source["file_present"] or source["kind"] == "missing_evidence":
        status, reason = "evidence_missing", "explicit_evidence_missing"
        matched = None
    elif source["integrity_status"] == "expected_hash_mismatch":
        status, reason = "binding_conflict", "evidence_hash_mismatch"
        matched = None
    elif source["kind"] == "unverified_external_evidence":
        status, reason = "source_not_verified", "external_source_not_verified"
    elif (source["kind"] == "first_party_license_file" and subject["subject_type"] != "component"
          or source["kind"] == "dependency_license_file" and subject["subject_type"] != "dependency"):
        status, reason = "evidence_unsupported", "evidence_type_subject_mismatch"
    elif source["format_status"] not in ("license_header_observed", "metadata_declaration_observed") or not labels:
        status, reason = "evidence_unsupported", "evidence_format_unsupported"
    elif _FORMAT_BY_KIND.get(source["kind"]) != source["format_status"]:
        status, reason = "evidence_unsupported", "evidence_kind_format_mismatch"
    elif not references:
        status, reason = "binding_ambiguous", "source_file_reference_not_matched"
    elif len(references) != 1:
        status, reason = "binding_ambiguous", "source_file_reference_ambiguous"
        matched = None
    elif (subject["subject_type"] == "dependency"
          and (source["kind"] in ("package_metadata", "source_manifest_declaration")
               or matched in manifest_refs)):
        # The old dependency L-row refers to its declaring manifest/lock.
        # A project's own MIT metadata is not that dependency's license.
        status, reason = "binding_ambiguous", "dependency_metadata_identity_not_established"
    else:
        status, reason = "binding_confirmed_within_source", "source_file_binding_confirmed"
    return {
        "request_id": request["request_id"], "evidence_id": source["evidence_id"],
        "source_key": subject["source_key"], "status": status, "reason_codes": [reason],
        "matched_source_file_ref": matched, "observed_license_labels": labels,
    }


def _record(subject: dict, bindings: list[dict]) -> dict:
    labels = list(dict.fromkeys(label for binding in bindings
                               if binding["status"] == "binding_confirmed_within_source"
                               for label in binding["observed_license_labels"]))
    reasons = list(dict.fromkeys(reason for binding in bindings for reason in binding["reason_codes"]))
    states = {"evidence_present" if binding["status"] == "binding_confirmed_within_source"
              else binding["status"] for binding in bindings}
    if len(labels) > 1:
        # Literal declaration disagreement, never an SPDX compatibility verdict.
        states.add("binding_conflict")
        reasons.append("conflicting_license_declarations")
    if not states:
        states.add("evidence_missing")
        reasons.append("evidence_not_selected_for_record")
    status = next(value for value in _STATUS_ORDER if value in states)
    review = ("conflicting_evidence" if status == "binding_conflict" else
              "review_required" if status == "evidence_present" else "insufficient_evidence")
    return {
        "source_key": subject["source_key"],
        "evidence_refs": list(dict.fromkeys(binding["evidence_id"] for binding in bindings)),
        "request_refs": [binding["request_id"] for binding in bindings],
        "evidence_status": status, "review_status": review,
        "observed_license_labels": labels, "reason_codes": list(dict.fromkeys(reasons)),
        "human_review_required": True, "phase24_license_review_required": True,
    }


def derive_records(subjects: list[dict], bindings: list[dict]) -> list[dict]:
    """Pure aggregate reused by validators; no validation/import recursion or I/O."""
    grouped = {subject["source_key"]: [] for subject in subjects}
    if len(grouped) != len(subjects):
        raise InputError("license_evidence_duplicate_source_key")
    for binding in bindings:
        if binding["source_key"] not in grouped:
            raise InputError("license_evidence_unknown_bound_source_key")
        grouped[binding["source_key"]].append(binding)
    return [_record(subject, grouped[subject["source_key"]]) for subject in subjects]


def build_ledger(base, subjects: list[dict], evidence: list[dict], requests: list[dict]) -> dict:
    """Keep every original L-row and derive a separate source-bound overlay."""
    old = base.dependencies["license_evidence"]
    if not 1 <= len(old) <= MAX_RECORDS or len(subjects) != len(old):
        raise InputError("license_evidence_complete_source_inventory_required")
    by_license = {}
    primary = {("component", row["component_id"]): row for row in base.inventory["components"]}
    primary.update({("dependency", row["dependency_id"]): row for row in base.dependencies["dependencies"]})
    for subject, original in zip(subjects, old):
        identity = (original["subject_type"], original["subject_id"])
        if (subject["source_license_id"] != original["evidence_id"]
                or (subject["subject_type"], subject["subject_id"]) != identity
                or subject["base_declared_license"] != original["declared_license"]
                or subject["base_evidence_level"] != original["evidence_level"]
                or subject["base_source_file_refs"] != original["source_file_refs"]
                or subject["source_record_sha256"] != record_digest(primary[identity])
                or subject["license_record_sha256"] != record_digest(original)):
            raise InputError("license_evidence_source_subject_mismatch")
        if subject["source_license_id"] in by_license:
            raise InputError("license_evidence_duplicate_source_subject")
        by_license[subject["source_license_id"]] = subject
    if len(evidence) > MAX_EVIDENCE_SOURCES or len(requests) > MAX_BINDING_REQUESTS:
        raise InputError("license_evidence_selection_limit")
    by_evidence = {row["evidence_id"]: row for row in evidence}
    if len(by_evidence) != len(evidence):
        raise InputError("license_evidence_duplicate_evidence_reference")
    paths = {(row["root_id"], row["path"]): row["file_id"] for row in base.inventory["files"]}
    manifest_refs = {paths[(row["root_id"], row["path"])]
                     for row in base.inventory["dependency_manifest_refs"]}
    bindings, request_ids = [], set()
    for request in requests:
        if request["request_id"] in request_ids:
            raise InputError("license_evidence_duplicate_binding_request")
        request_ids.add(request["request_id"])
        if request["source_license_id"] not in by_license or request["evidence_id"] not in by_evidence:
            raise InputError("license_evidence_unknown_binding_reference")
        bindings.append(_binding(by_license[request["source_license_id"]],
                                 by_evidence[request["evidence_id"]], request, manifest_refs))
    records = derive_records(subjects, bindings)
    states = [row["evidence_status"] for row in records]
    return {
        **common(LEDGER_SCHEMA, base.reference),
        "source_subjects": deepcopy(subjects), "evidence_sources": deepcopy(evidence),
        "bindings": bindings, "records": records,
        "counts": {
            "source_record_count": len(records),
            "base_unknown_license_count": sum(row["base_declared_license"] is None
                or row["base_evidence_level"] == "conflicting_declarations" for row in subjects),
            "evidence_file_count": sum(row["file_present"] for row in evidence),
            "binding_request_count": len(bindings),
            "evidence_present_record_count": states.count("evidence_present"),
            "missing_evidence_record_count": states.count("evidence_missing"),
            "ambiguous_record_count": states.count("binding_ambiguous"),
            "conflicting_record_count": states.count("binding_conflict"),
            "unsupported_record_count": states.count("evidence_unsupported"),
            "unverified_source_record_count": states.count("source_not_verified"),
        },
    }


__all__ = ("build_ledger", "derive_records")
