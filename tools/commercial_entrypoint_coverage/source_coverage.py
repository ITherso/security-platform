"""Pure observed-file/catalog comparison; catalog presence is not ownership."""
from __future__ import annotations

from copy import deepcopy
from collections import Counter

from .coverage_contracts import (COVERAGE_SCHEMA, COVERAGE_STATUSES, InputError,
                                 LIMITATIONS, common, record_digest)


def coverage_reference(target: str) -> str:
    return "coverage-" + record_digest({"target_reference": target})


def _index(rows: list[dict], key: str, label: str) -> dict:
    result = {}
    for row in rows:
        if row[key] in result:
            raise InputError("entrypoint_duplicate_" + label)
        result[row[key]] = row
    return result


def status_counts(rows: list[dict]) -> list[dict]:
    counts = Counter(row["phase24_coverage_status"] for row in rows)
    return [{"status": status, "target_count": counts[status]} for status in COVERAGE_STATUSES]


def build_coverage(reference: dict, context: dict, manifests: list[dict], targets: list[dict],
                   source_files: list[dict]) -> dict:
    roots = _index(context["source_roots"], "root_id", "source_root")
    manifest_by = _index(manifests, "manifest_id", "source_manifest")
    target_by = _index(targets, "target_reference", "target")
    owner_by = _index(context["ownership"], "manifest_id", "manifest_ownership")
    observations = _index(source_files, "source_file_reference", "source_file")
    files_by_path = {}
    for row in context["files"]:
        key = (row["root_id"], row["path"])
        if key in files_by_path:
            raise InputError("entrypoint_duplicate_catalog_path")
        files_by_path[key] = row
    source_identities, observation_by_target = set(), {}
    for observation in observations.values():
        identity = (observation["root_id"], observation["pinned_commit"], observation["path"])
        if identity in source_identities:
            raise InputError("entrypoint_duplicate_source_observation")
        source_identities.add(identity)
        if observation["read_status"] not in ("present_and_hashed", "declared_file_missing"):
            raise InputError("entrypoint_unsupported_observation_status")
        for allowed in observation["allowlist_entries"]:
            target = target_by.get(allowed["target_reference"])
            if (target is None or target["manifest_reference"] != allowed["manifest_reference"]
                    or target["root_id"] != observation["root_id"]
                    or target["pinned_commit"] != observation["pinned_commit"]
                    or target["normalized_relative_path"] != observation["path"]
                    or any(allowed[key] != observation[key] for key in
                           ("source_file_reference", "root_id", "pinned_commit", "path"))
                    or allowed["target_reference"] in observation_by_target):
                raise InputError("entrypoint_observation_target_binding_mismatch")
            observation_by_target[allowed["target_reference"]] = observation
    rows = []
    for target in targets:
        manifest = manifest_by.get(target["manifest_reference"])
        root = roots.get(target["root_id"])
        owner = owner_by.get(target["manifest_reference"])
        if (manifest is None or root is None or owner is None
                or root["pinned_commit"] != target["pinned_commit"]
                or reference["source_commits"][target["root_id"]] != target["pinned_commit"]
                or any(target[key] != manifest[value] for key, value in
                       (("root_id", "root_id"), ("pinned_commit", "pinned_commit"), ("manifest_sha256", "sha256")))):
            raise InputError("entrypoint_coverage_source_identity_mismatch")
        path = target["normalized_relative_path"]
        observation = observation_by_target.get(target["target_reference"])
        catalog = None if path is None else files_by_path.get((target["root_id"], path))
        catalog_status = ("scope_classification_unknown" if path is None else
                          "listed_in_global_f_catalog" if catalog is not None else "not_listed_in_global_f_catalog")
        component_ids = ([] if catalog is None else [row["component_id"] for row in context["components"]
                                                    if catalog["file_id"] in row["source_file_refs"]])
        component_status = ("scope_classification_unknown" if path is None else
                            "referenced_by_component" if component_ids else "not_referenced_by_component")
        presence, size, sha = "not_established", None, None
        allowlist = "not_applicable" if path is None else "not_allowlisted"
        identity_status = "not_compared" if catalog is not None or path is None else "not_in_catalog"
        status, evidence = "entrypoint_not_established", "entrypoint_not_established"
        if path is not None:
            status, evidence = "source_read_not_performed", "read_not_performed"
        if observation is not None:
            allowlist = "matched"
            presence = observation["source_file_presence"]
            size, sha = observation["observed_byte_size"], observation["observed_sha256"]
            if observation["read_status"] == "declared_file_missing":
                status, evidence = "declared_target_file_missing", "source_file_missing"
            else:
                evidence = "source_hash_observed"
                if catalog is None:
                    status = "source_present_inventory_gap"
                elif catalog["bytes"] != size or catalog["sha256"] != sha:
                    status, identity_status = "source_identity_mismatch", "mismatch"
                else:
                    identity_status = "matched"
                    candidates = set(owner["candidate_component_ids"])
                    # This is bounded F-reference coverage, never an owner or
                    # global selected/excluded classification for the file.
                    if candidates.intersection(component_ids):
                        status = "covered_by_selected_source"
                    elif candidates and component_ids:
                        status = "present_outside_selected_scope"
                    else:
                        status = "scope_classification_unknown"
        established = owner["ownership_status"] == "definite_ownership"
        rows.append({"coverage_reference": coverage_reference(target["target_reference"]),
                     "target_reference": target["target_reference"], "manifest_reference": target["manifest_reference"],
                     "root_id": target["root_id"], "pinned_commit": target["pinned_commit"],
                     "target_kind": target["target_kind"], "declared_target_name": target["declared_target_name"],
                     "declared_relative_path": target["declared_relative_path"], "normalized_relative_path": path,
                     "source_file_reference": None if observation is None else observation["source_file_reference"],
                     "allowlist_status": allowlist, "source_file_presence": presence,
                     "observed_byte_size": size, "observed_sha256": sha,
                     "phase24_source_reference": None if catalog is None else catalog["file_id"],
                     "phase24_catalog_status": catalog_status, "phase24_identity_status": identity_status,
                     "component_source_status": component_status, "referencing_component_ids": component_ids,
                     "phase24_manifest_contexts": [deepcopy(row) for row in context["dependency_manifest_refs"]
                                                   if row["root_id"] == target["root_id"] and row["path"] == path],
                     "phase24_coverage_status": status,
                     "component_ownership_status": "component_ownership_established" if established else "component_ownership_unresolved",
                     "manifest_ownership_status": owner["ownership_status"],
                     "candidate_component_ids": deepcopy(owner["candidate_component_ids"]),
                     "established_component_id": owner["component_id"] if established else None,
                     "source_evidence_status": evidence, "limitations": list(LIMITATIONS)})
    referenced = {ref for component in context["components"] for ref in component["source_file_refs"]}
    counts = {"manifest_count": len(manifests), "target_count": len(targets),
              "explicit_path_target_count": sum(target["target_path_declared"] for target in targets),
              "source_file_observation_count": len(source_files),
              "present_and_hashed_source_file_count": sum(row["read_status"] == "present_and_hashed" for row in source_files),
              "missing_source_file_count": sum(row["read_status"] == "declared_file_missing" for row in source_files),
              "observed_source_bytes": sum(row["observed_byte_size"] or 0 for row in source_files),
              "global_f_catalog_count": len(context["files"]), "component_referenced_file_count": len(referenced),
              "unresolved_ownership_target_count": sum(row["component_ownership_status"] == "component_ownership_unresolved" for row in rows),
              "by_coverage_status": status_counts(rows)}
    return {**common(COVERAGE_SCHEMA, reference), "source_context": deepcopy(context),
            "manifests": deepcopy(manifests), "targets": deepcopy(targets), "source_files": deepcopy(source_files),
            "coverage": rows, "counts": counts, "limitations": list(LIMITATIONS)}


def rebuild_coverage(coverage: dict) -> dict:
    return build_coverage(coverage["source_reference"], coverage["source_context"], coverage["manifests"],
                          coverage["targets"], coverage["source_files"])


__all__ = ("build_coverage", "rebuild_coverage", "coverage_reference", "status_counts")
