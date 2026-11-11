"""Observed candidate identities and F metadata remain separate evidence."""
from __future__ import annotations

from copy import deepcopy

from .candidate_contracts import COVERAGE_SCHEMA, InputError, common
from .path_context import LIMITATIONS


def build_projection(evidence: dict, triage: dict) -> dict:
    context = evidence["source_context"]["parent_context"]["phase24_context"]
    roots = {row["root_id"]: row for row in context["source_roots"]}
    files = {(row["root_id"], row["path"]): row for row in context["files"]}
    rows = []
    for candidate in evidence["candidates"]:
        root_id, pin, path = (candidate["candidate_root_id"], candidate["candidate_pinned_commit"],
                              candidate["candidate_relative_path"])
        catalog_status, identity_status, component_status = "scope_classification_unknown", "not_compared", "scope_classification_unknown"
        catalog_ref, component_ids = None, []
        if candidate["read_status"] == "present_and_hashed":
            if root_id not in roots or roots[root_id]["pinned_commit"] != pin:
                raise InputError("module_candidate_inventory_source_pin_mismatch")
            source = files.get((root_id, path))
            if source is None:
                catalog_status, identity_status, component_status = "not_listed_in_global_f_catalog", "not_in_catalog", "not_referenced_by_component"
            else:
                catalog_ref, catalog_status = source["file_id"], "listed_in_global_f_catalog"
                identity_status = ("matched" if source["bytes"] == candidate["observed_byte_size"]
                                   and source["sha256"] == candidate["observed_sha256"] else "mismatch")
                component_ids = [row["component_id"] for row in context["components"]
                                 if source["file_id"] in row["source_file_refs"]]
                component_status = "referenced_by_component" if component_ids else "not_referenced_by_component"
        rows.append({"candidate_id": candidate["candidate_id"], "reference_id": candidate["reference_id"],
                     "file_id": candidate["file_id"], "root_id": root_id, "pinned_commit": pin, "path": path,
                     "read_status": candidate["read_status"], "observed_byte_size": candidate["observed_byte_size"],
                     "observed_sha256": candidate["observed_sha256"], "phase24_source_reference": catalog_ref,
                     "phase24_catalog_status": catalog_status, "phase24_identity_status": identity_status,
                     "component_source_status": component_status, "referencing_component_ids": component_ids,
                     "component_ownership_status": "component_ownership_unresolved",
                     "compiler_resolution_verified": False, "component_ownership_verified": False, "resolved_file": False})
    deltas = evidence["source_context"]["parent_context"]["phase28_deltas"]
    counts = {"candidate_count": len(rows),
              "examined_candidate_count": sum(row["read_status"] != "read_not_performed" for row in rows),
              "unique_observed_file_count": len(evidence["candidate_files"]),
              "global_f_catalog_count": len(context["files"]),
              "component_referenced_file_count": len({ref for c in context["components"] for ref in c["source_file_refs"]}),
              "listed_candidate_count": sum(row["phase24_catalog_status"] == "listed_in_global_f_catalog" for row in rows),
              "not_listed_candidate_count": sum(row["phase24_catalog_status"] == "not_listed_in_global_f_catalog" for row in rows),
              "scope_unknown_candidate_count": sum(row["phase24_catalog_status"] == "scope_classification_unknown" for row in rows),
              "identity_matched_candidate_count": sum(row["phase24_identity_status"] == "matched" for row in rows),
              "identity_mismatched_candidate_count": sum(row["phase24_identity_status"] == "mismatch" for row in rows),
              "not_compared_candidate_count": sum(row["phase24_identity_status"] == "not_compared" for row in rows),
              "unapplied_phase28_delta_count": len(deltas),
              "source_dependency_record_count": context["source_dependency_record_count"],
              "source_ambiguous_dependency_record_count": context["source_ambiguous_dependency_record_count"],
              "source_definite_owner_count": context["source_definite_owner_count"]}
    return {**common(COVERAGE_SCHEMA, evidence["source_reference"]), "candidates": rows, "counts": counts,
            "phase28_delta_boundary": {"proposals": deepcopy(deltas), "proposal_count": len(deltas),
                                       "application_authorized": False, "application_performed": False,
                                       "phase24_inventory_modified": False},
            "license_boundary_counts": deepcopy(context["license_boundary_counts"]), "limitations": list(LIMITATIONS)}


__all__ = ("build_projection",)
