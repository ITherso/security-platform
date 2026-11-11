"""Unapplied repository-level proposals, one per observed source identity."""
from __future__ import annotations

from .coverage_contracts import (APPLICATION_PRECONDITIONS, DELTA_SCHEMA, InputError,
                                 LIMITATIONS, common, record_digest)


def proposal_reference(root_id: str, pinned_commit: str, path: str,
                       observed_byte_size: int, observed_sha256: str) -> str:
    return "proposal-" + record_digest({"root_id": root_id, "pinned_commit": pinned_commit, "path": path,
                                        "observed_byte_size": observed_byte_size, "observed_sha256": observed_sha256})


def build_delta(coverage: dict) -> dict:
    observations = {row["source_file_reference"]: row for row in coverage["source_files"]}
    groups = {}
    for row in coverage["coverage"]:
        if row["phase24_coverage_status"] != "source_present_inventory_gap":
            continue
        observation = observations.get(row["source_file_reference"])
        if (observation is None or observation["read_status"] != "present_and_hashed"
                or observation["regular_file"] is not True or row["allowlist_status"] != "matched"
                or row["source_evidence_status"] != "source_hash_observed"
                or row["phase24_catalog_status"] != "not_listed_in_global_f_catalog"
                or row["phase24_source_reference"] is not None or row["declared_relative_path"] is None
                or row["observed_sha256"] is None or row["observed_byte_size"] is None):
            raise InputError("entrypoint_unsupported_scope_delta_evidence")
        identity = (row["root_id"], row["pinned_commit"], row["normalized_relative_path"],
                    row["observed_byte_size"], row["observed_sha256"])
        groups.setdefault(identity, []).append(row)
    proposals = []
    for (root_id, pin, path, size, sha), rows in sorted(groups.items()):
        if len(proposals) >= 64:
            raise InputError("entrypoint_scope_delta_limit")
        source_ids = {row["source_file_reference"] for row in rows}
        if len(source_ids) != 1:
            raise InputError("entrypoint_scope_delta_source_alias")
        source_id = next(iter(source_ids))
        targets = sorted({row["target_reference"] for row in rows})
        manifests = sorted({row["manifest_reference"] for row in rows})
        proposals.append({"proposal_reference": proposal_reference(root_id, pin, path, size, sha),
                          "source_target_reference": targets[0] if len(targets) == 1 else None,
                          "source_target_references": targets, "manifest_references": manifests,
                          "source_file_reference": source_id, "root_id": root_id, "pinned_commit": pin,
                          "path": path, "observed_byte_size": size, "observed_sha256": sha,
                          "current_phase24_coverage": "source_present_inventory_gap",
                          "proposed_scope_action": "propose_selected_source_inclusion",
                          "proposal_level": "repository_source_coverage", "proposed_component_id": None,
                          "supporting_evidence": {"coverage_references": sorted({row["coverage_reference"] for row in rows}),
                                                  "manifest_references": manifests, "source_file_reference": source_id,
                                                  "source_hash_observed": True, "explicit_allowlist": True},
                          "ownership_limitation": ("component_ownership_unresolved" if any(
                              row["component_ownership_status"] == "component_ownership_unresolved" for row in rows)
                              else "scope_inclusion_does_not_verify_component_ownership"),
                          "application_preconditions": list(APPLICATION_PRECONDITIONS),
                          "application_authorized": False, "application_performed": False,
                          "phase24_inventory_modified": False, "component_ownership_verified": False})
    return {**common(DELTA_SCHEMA, coverage["source_reference"]), "proposals": proposals,
            "counts": {"unique_proposal_count": len(proposals),
                       "proposal_target_reference_count": sum(len(row["source_target_references"]) for row in proposals),
                       "proposal_source_file_count": len({row["source_file_reference"] for row in proposals}),
                       "application_authorized_count": 0, "application_performed_count": 0},
            "limitations": list(LIMITATIONS)}


__all__ = ("build_delta", "proposal_reference")
