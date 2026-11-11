"""Pure, reproducible open constraints derived only from inventory/ledger metadata."""
from __future__ import annotations

from .composition_contracts import CONSTRAINTS_SCHEMA, InputError, common


BLOCKER_CODES = (
    "license_review_required", "dependency_license_unknown",
    "third_party_provenance_incomplete", "binary_source_binding_missing",
    "build_acceptance_not_performed", "runtime_acceptance_not_performed",
    "data_handling_pending", "release_authority_missing",
)


def build_constraints(inventory: dict, ledger: dict) -> dict:
    """No source reads, dependency resolution, legal decisions, or accepted artifacts."""
    reference = inventory["candidate_reference"]
    if ledger["candidate_reference"] != reference:
        raise InputError("composition_constraint_candidate_mismatch")
    files = {(row["root_id"], row["path"]): row["file_id"] for row in inventory["files"]}
    manifests = {row["manifest_id"]: row for row in ledger["manifest_records"]}
    evidence = {(row["subject_type"], row["subject_id"]): row for row in ledger["license_evidence"]}
    blockers = []

    def add(code, kind, subject, refs, reason, next_decision):
        blockers.append({"code": code, "subject_type": kind, "subject_id": subject,
                         "source_file_refs": list(dict.fromkeys(refs)), "reason_code": reason,
                         "next_decision": next_decision, "status": "open"})

    for row in ledger["license_evidence"]:
        if row["human_review_required"] is not True or row["redistribution_authorized"] is not False:
            raise InputError("composition_license_authority_must_remain_pending")
        add("license_review_required", row["subject_type"], row["subject_id"], row["source_file_refs"],
            "local_evidence_is_not_redistribution_review", "obtain_authorized_license_review")
    for row in ledger["dependencies"]:
        manifest = manifests[row["manifest_id"]]
        refs = [files[(manifest["root_id"], manifest["path"])]]
        license_row = evidence[("dependency", row["dependency_id"])]
        if license_row["declared_license"] is None or license_row["evidence_level"] == "conflicting_declarations":
            add("dependency_license_unknown", "dependency", row["dependency_id"], refs,
                "dependency_license_not_established_by_selected_metadata", "collect_scoped_dependency_license_evidence")
        if (row["local_package_artifact"] == "not_selected_or_verified"
                and row["source_type"] != "workspace"):
            reason = ("lock_identity_is_not_local_package_provenance" if row["relation"] == "lock_record"
                      else "declaration_is_not_resolved_package_provenance")
            add("third_party_provenance_incomplete", "dependency", row["dependency_id"], refs,
                reason, "review_dependency_provenance_and_distribution_scope")
    if inventory["actual_distributable_artifacts"] != []:
        raise InputError("composition_phase_does_not_accept_distributable_artifacts")
    for component in inventory["components"]:
        add("binary_source_binding_missing", "component", component["component_id"],
            component["source_file_refs"], "proposed_sources_have_no_accepted_binary_binding",
            "define_and_independently_accept_distributable_binding")
    for code, flag, reason, decision in (
        ("build_acceptance_not_performed", "build_verified", "source_inventory_is_not_build_acceptance", "perform_separately_authorized_build_acceptance"),
        ("runtime_acceptance_not_performed", "runtime_verified", "source_inventory_is_not_runtime_acceptance", "perform_separately_authorized_runtime_acceptance"),
        ("release_authority_missing", "release_authorized", "no_release_authority_is_established", "obtain_explicit_release_authority"),
    ):
        if inventory[flag] is not False or ledger[flag] is not False:
            raise InputError("composition_authority_flags_must_remain_false")
        add(code, "candidate", reference, [], reason, decision)
    add("data_handling_pending", "candidate", reference, [],
        "selected_metadata_has_no_data_handling_clearance", "confirm_metadata_handling_and_distribution_scope")
    counts = []
    for code in BLOCKER_CODES:
        subjects = {(row["subject_type"], row["subject_id"]) for row in blockers if row["code"] == code}
        if subjects:
            counts.append({"code": code, "affected_subject_count": len(subjects)})
    return {**common(CONSTRAINTS_SCHEMA, reference), "blockers": blockers,
            "counts": {"blocker_count": len(blockers), "by_code": counts}}


__all__ = ("BLOCKER_CODES", "build_constraints")
