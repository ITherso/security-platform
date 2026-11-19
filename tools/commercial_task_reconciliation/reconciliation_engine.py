"""Deterministic offline reconciliation of one untrusted capsule; memory only.

Order: container inventory -> member interpretation -> unchanged Phase43
recipient reader -> local identity reconciliation -> eligibility. The engine
opens no paths, reads no clock and produces the same report for the same
capsule bytes, request and local reference snapshot.
"""
from __future__ import annotations

import hashlib

from exchange_contracts import TASK_FIELDS, InputError
from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request
from capsule_claims import ENVELOPE_FIELDS, IDENTITY_FIELDS, interpret_contents, owner_code
from capsule_zip_inventory import inventory_capsule
from identity_reconciliation import reconcile_identities
from local_task_records import LocalReference
from reconciliation_contracts import (
    MAX_FINDINGS, LIFECYCLE_FOR_STATUS, REPORT_SCHEMA, INBOX_SCHEMA, STRUCTURAL_CATEGORIES, Category, Comparison, Compatibility,
    Correspondence, Eligibility, FactOrigin, FieldState, ManualReview, ManualReviewRequirement, RepresentedState,
    Severity, common, expect, fail, uses_phase42, uses_phase43, validate_inbox, validate_report, validate_request,
)
from reconciliation_findings import finding, ordered

_ZIP_REQUEST = "task-request.json"


def owner_reader_verdict(capsule: bytes) -> tuple[str, str | None, dict | None, list | None]:
    """Run the unchanged Phase43 recipient reader on the exact bytes."""
    try:
        envelope, _contract, artifacts = read_portable_task_request(inspect_task_exchange_capsule(capsule))
    except InputError as error:
        return Compatibility.INCOMPATIBLE.value, owner_code(error), None, None
    return Compatibility.COMPATIBLE.value, None, envelope, artifacts


def derive_eligibility(compatibility: str, findings: list, comparisons: list) -> dict:
    structural = [item["finding_id"] for item in findings
                  if item["severity"] == Severity.BLOCKING and item["category"] in STRUCTURAL_CATEGORIES]
    results = {row["result"] for row in comparisons}
    if compatibility != Compatibility.COMPATIBLE or structural:
        status, basis = Eligibility.STRUCTURAL_REJECTION, structural
    elif Comparison.MISMATCH in results:
        status = Eligibility.IDENTITY_MISMATCH
        basis = [item["finding_id"] for item in findings
                 if item["category"] in (Category.LOCAL_IDENTITY, Category.LOCAL_DISCLOSURE)]
    elif results & {Comparison.UNAVAILABLE, Comparison.NOT_COMPARABLE} or not comparisons:
        status = Eligibility.LOCAL_RECONCILIATION_UNAVAILABLE
        basis = [item["finding_id"] for item in findings if item["category"] == Category.LOCAL_AVAILABILITY]
    else:
        status = Eligibility.STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW
        basis = [item["finding_id"] for item in findings if item["rule"] == "MANUAL_REVIEW_REQUIRED"]
    if not basis:
        fail("eligibility_without_basis")
    return {"status": status.value,
            "manual_review": (ManualReview.ELIGIBLE_FOR_MANUAL_REVIEW
                              if status == Eligibility.STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW
                              else ManualReview.NOT_ELIGIBLE).value,
            "manual_review_requirement": ManualReviewRequirement.REQUIRED.value,
            "basis_finding_ids": sorted(set(basis))}


def _identity_rows(tasks: list) -> list:
    return [{"position": position, **{key: task[key] for key in IDENTITY_FIELDS}} for position, task in enumerate(tasks)]


def _task_fields(claims: dict) -> list:
    result = []
    for task in claims["tasks"]:
        fields = {}
        for record in task["fields"]:
            key = record["path"].rsplit(".", 1)[1]
            fields[key] = (record["state"], record["value"] if record["state"] == FieldState.VALID else None)
        result.append({"position": task["position"], "fields": fields})
    return result


def _task_outcome(rows: list, task_ref: str) -> str:
    results = {row["result"] for row in rows if row["subject"] == "task:" + task_ref}
    if Comparison.MISMATCH in results:
        return Comparison.MISMATCH.value
    if results & {Comparison.UNAVAILABLE, Comparison.NOT_COMPARABLE} or not results:
        return Comparison.UNAVAILABLE.value
    return Comparison.MATCH.value


def reconcile_capsule(capsule: bytes, request: dict, local: LocalReference) -> tuple[dict, dict]:
    """Return the validated (report, inbox) pair for one capsule."""
    if type(capsule) is not bytes:
        fail("capsule_bytes")
    request = validate_request(request)
    if type(local) is not LocalReference:
        fail("local_reference_type")
    record = local.record()
    expect(record["mode"], request["local_reference_mode"], "local_reference_mode_matches_request")
    if uses_phase42(record["mode"]):
        expect(record["phase42"]["register_sha256"], request["expected_local_phase42_register_sha256"],
               "local_phase42_register_pin")
    if uses_phase43(record["mode"]):
        expect(record["phase43"]["index_sha256"], request["expected_local_phase43_index_sha256"],
               "local_phase43_index_pin")

    capsule_identity = {"bytes": len(capsule), "sha256": hashlib.sha256(capsule).hexdigest()}
    inventory = inventory_capsule(capsule)
    claims = interpret_contents(inventory["contents"])
    compatibility, rejection, envelope, artifacts = owner_reader_verdict(capsule)
    findings = list(inventory["findings"]) + list(claims["findings"])
    represented_tasks, represented_state = [], RepresentedState.NOT_ESTABLISHED
    claimed_vs_represented = Correspondence.NOT_COMPARABLE
    if compatibility == Compatibility.INCOMPATIBLE:
        findings.append(finding("OWNER_READER_REJECTED", "capsule",
                                "the Phase43 recipient reader rejected the capsule with " + rejection))
    else:
        represented_tasks = _identity_rows(envelope["tasks"])
        represented_state = RepresentedState.ESTABLISHED_BY_PHASE43_OWNER_READER
        declared_source = claims["source_declaration"]
        same = (claims["declared_tasks"] == represented_tasks and set(envelope) == set(ENVELOPE_FIELDS)
                and claims["owner_member_envelope"] == envelope
                and declared_source == {key: envelope[key] for key in declared_source})
        claimed_vs_represented = Correspondence.MATCH if same else Correspondence.MISMATCH
        diagnostic_blocking = any(item["severity"] == Severity.BLOCKING and item["category"] in STRUCTURAL_CATEGORIES
                                  for item in findings)
        if diagnostic_blocking or not same:
            findings.append(finding("DIAGNOSTIC_OWNER_DISAGREEMENT", "capsule",
                                    "the Phase43 reader accepted the capsule but Phase44 diagnostics did not agree"))
    structurally_valid = compatibility == Compatibility.COMPATIBLE and not any(
        item["severity"] == Severity.BLOCKING and item["category"] in STRUCTURAL_CATEGORIES for item in findings)
    if structurally_valid:
        member_sha256 = {item["name"]: item["sha256"] for item in artifacts}
    else:
        member_sha256 = {}
    reconciliation, more = reconcile_identities(structurally_valid, _task_fields(claims),
                                                envelope if structurally_valid else None,
                                                capsule_identity["sha256"], member_sha256, record)
    findings += more
    findings.append(finding("MANUAL_REVIEW_REQUIRED", "capsule",
                            "valid structure and matching hashes do not authenticate the producer or authorize use"))
    findings = ordered(findings)
    if len(findings) > MAX_FINDINGS:
        # Keep the most severe findings and record the truncation itself, so a
        # rejection report is always produced instead of no report at all.
        dropped = len(findings) - (MAX_FINDINGS - 1)
        findings = ordered(findings[:MAX_FINDINGS - 1] + [finding(
            "FINDINGS_TRUNCATED", "capsule", str(dropped) + " lower-ranked findings were not listed")])
    eligibility = derive_eligibility(compatibility, findings, reconciliation["comparisons"])
    local_reference = {"mode": record["mode"], "phase42": None, "phase43": None}
    if record["phase42"] is not None:
        local_reference["phase42"] = {key: record["phase42"][key] for key in ("register_sha256", "manifest_sha256")}
    if record["phase43"] is not None:
        local_reference["phase43"] = {key: record["phase43"][key] for key in ("index_sha256", "capsule_sha256",
                                                                               "manifest_sha256")}
    report = validate_report({
        **common(REPORT_SCHEMA), "request_reference": request["request_reference"], "capsule": capsule_identity,
        "archive": inventory["archive"], "members": inventory["members"],
        "required_members": inventory["required_members"], "member_contents": claims["member_contents"],
        "manifest_correspondence": claims["manifest_correspondence"],
        "phase43_reader": {"compatibility": compatibility, "owner_rejection_code": rejection},
        "envelope_fields": claims["envelope_fields"], "envelope_unexpected_fields": claims["envelope_unexpected_fields"],
        "tasks": claims["tasks"], "task_declaration": claims["task_declaration"],
        "field_presence_summary": claims["field_presence_summary"],
        "capsule_identity": {"declared_schema": claims["declared_schema"], "declared_tasks": claims["declared_tasks"],
                             "source_declaration": claims["source_declaration"],
                             "represented_state": represented_state.value, "represented_tasks": represented_tasks,
                             "claimed_vs_represented": claimed_vs_represented.value},
        "local_reference": local_reference, "local_reconciliation": reconciliation,
        "findings": findings, "eligibility": eligibility,
    })
    status = Eligibility(eligibility["status"])
    admitted = []
    if status != Eligibility.STRUCTURAL_REJECTION:
        for task in envelope["tasks"]:
            admitted.append({**{key: task[key] for key in TASK_FIELDS},
                             "fact_origin": FactOrigin.CAPSULE_DECLARED_STRUCTURALLY_VALID_NOT_AUTHENTICATED.value,
                             "local_reconciliation": _task_outcome(reconciliation["comparisons"], task["task_id"])})
    inbox = validate_inbox({
        **common(INBOX_SCHEMA), "request_reference": request["request_reference"], "capsule": capsule_identity,
        "lifecycle_stage": LIFECYCLE_FOR_STATUS[status].value, "eligibility_status": status.value,
        "manual_review": eligibility["manual_review"], "manual_review_requirement": eligibility["manual_review_requirement"],
        "admitted_task_count": len(admitted), "admitted_tasks": admitted,
    })
    return report, inbox


__all__ = ("derive_eligibility", "owner_reader_verdict", "reconcile_capsule")
