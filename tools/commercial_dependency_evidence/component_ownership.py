"""Conservative manifest ownership; source scope is not product ownership."""
from __future__ import annotations

from .evidence_contracts import record_digest


OWNERSHIP_STATUSES = ("definite_ownership", "ambiguous_ownership", "ownership_not_established")
OWNERSHIP_EVIDENCE_CODES = (
    "manifest_file_in_component_source_scope", "package_metadata_present", "unique_primary_manifest_matches_scope",
    "shared_manifest_source_scope", "source_scope_without_primary_manifest", "virtual_workspace_without_package",
    "no_component_source_scope", "source_root_or_commit_mismatch",
)
OWNERSHIP_LIMITATIONS = (
    "source_package_is_not_product_component_identity", "ownership_is_not_runtime_dependency_inclusion",
    "workspace_pool_is_not_component_ownership", "shared_scope_prevents_definite_owner",
    "nonprimary_source_scope_prevents_definite_owner", "source_identity_mismatch_prevents_owner",
)


def ownership_fingerprint(row: dict) -> str:
    return record_digest({name: value for name, value in row.items() if name != "source_fingerprint"})


def build_ownership(manifests: list[dict], components: list[dict]) -> list[dict]:
    result = []
    for manifest in manifests:
        candidates = [row for row in components if manifest["phase24_file_ref"] in row["source_file_refs"]]
        primary = [row for row in candidates if row["manifest_file_ref"] == manifest["phase24_file_ref"]
                   and row["manifest_path"] == manifest["path"] and row["root_id"] == manifest["root_id"]]
        evidence = ["manifest_file_in_component_source_scope"] if candidates else ["no_component_source_scope"]
        limits = ["source_package_is_not_product_component_identity", "ownership_is_not_runtime_dependency_inclusion"]
        owner, status = None, "ownership_not_established"
        if manifest["package_name"] is None:
            evidence.append("virtual_workspace_without_package")
            limits.append("workspace_pool_is_not_component_ownership")
        else:
            evidence.append("package_metadata_present")
            if len(candidates) > 1:
                status = "ambiguous_ownership"
                evidence.append("shared_manifest_source_scope")
                limits.append("shared_scope_prevents_definite_owner")
            elif len(candidates) == 1 and primary == candidates:
                if candidates[0]["pinned_commit"] == manifest["pinned_commit"]:
                    status, owner = "definite_ownership", candidates[0]["component_id"]
                    evidence.append("unique_primary_manifest_matches_scope")
                else:
                    evidence.append("source_root_or_commit_mismatch")
                    limits.append("source_identity_mismatch_prevents_owner")
            elif candidates:
                evidence.append("source_scope_without_primary_manifest")
                limits.append("nonprimary_source_scope_prevents_definite_owner")
        row = {"manifest_id": manifest["manifest_id"], "phase24_file_ref": manifest["phase24_file_ref"],
               "package_name": manifest["package_name"], "component_id": owner,
               "candidate_component_ids": [item["component_id"] for item in candidates],
               "primary_component_ids": [item["component_id"] for item in primary],
               "ownership_source": "phase24_file_scope_and_package_metadata", "ownership_evidence": evidence,
               "ownership_status": status, "limitations": limits}
        row["source_fingerprint"] = ownership_fingerprint(row)
        result.append(row)
    return result


__all__ = ("build_ownership", "ownership_fingerprint")
