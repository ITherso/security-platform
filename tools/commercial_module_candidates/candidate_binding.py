"""Project explicit candidate-to-observation relations; never resolve a module."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from .candidate_contracts import InputError, LEDGER_SCHEMA, common
from .path_context import LIMITATIONS, PATH_CONTEXT_STATUSES, evaluate_path_context


CANDIDATE_STATUSES = ("candidate_present_unresolved", "candidate_missing", "candidate_not_allowlisted")


def _index(rows: list[dict], key: str) -> dict:
    result = {}
    for row in rows:
        if row[key] in result:
            raise InputError("module_candidate_duplicate_primary_reference")
        result[row[key]] = row
    return result


def build_evidence(reference: dict, source_context: dict, review_scope: dict,
                   candidate_files: list[dict]) -> dict:
    sources = _index(source_context["source_files"], "source_file_reference")
    references = _index(source_context["references"], "reference_id")
    selected = {}
    declarations = {}
    for selection in review_scope["selected_references"]:
        ref = selection["reference"]
        if ref["reference_id"] in selected or references.get(ref["reference_id"]) != ref:
            raise InputError("module_candidate_selected_reference_not_source_bound")
        selected[ref["reference_id"]] = selection
        for candidate in selection["candidates"]:
            if candidate["candidate_id"] in declarations:
                raise InputError("module_candidate_duplicate_candidate")
            declarations[candidate["candidate_id"]] = candidate
    allowlist = _index(review_scope["allowed_candidate_files"], "candidate_id")
    files = _index(candidate_files, "file_id")
    by_candidate = {}
    for observation in files.values():
        for candidate_id in observation["candidate_ids"]:
            if candidate_id in by_candidate or candidate_id not in declarations or candidate_id not in allowlist:
                raise InputError("module_candidate_unbound_file_observation")
            by_candidate[candidate_id] = observation
    if set(allowlist) != set(by_candidate):
        raise InputError("module_candidate_incomplete_allowlisted_observations")
    rows = []
    for selection in review_scope["selected_references"]:
        ref = selection["reference"]
        parent = sources.get(ref["source_file_reference"])
        if parent is None or parent["observed_sha256"] != ref["source_sha256"]:
            raise InputError("module_candidate_parent_source_not_bound")
        for candidate in selection["candidates"]:
            candidate_id = candidate["candidate_id"]
            allowed, observation = allowlist.get(candidate_id), by_candidate.get(candidate_id)
            if allowed is not None:
                if (allowed["reference_id"] != ref["reference_id"]
                        or any(candidate[key] != allowed[key] for key in ("candidate_id", "root_id", "pinned_commit", "path"))
                        or any(observation[key] != allowed[key] for key in ("root_id", "pinned_commit", "path"))):
                    raise InputError("module_candidate_observed_relation_not_bound")
                read_status = observation["read_status"]
                if read_status not in ("present_and_hashed", "declared_file_missing"):
                    raise InputError("module_candidate_unsupported_observation_status")
                status = "candidate_present_unresolved" if read_status == "present_and_hashed" else "candidate_missing"
                presence, regular = observation["source_file_presence"], observation["regular_file"]
                size, sha = observation["observed_byte_size"], observation["observed_sha256"]
            else:
                read_status, status, presence = "read_not_performed", "candidate_not_allowlisted", "not_established"
                regular, size, sha = None, None, None
            rows.append({"candidate_id": candidate_id, "reference_id": ref["reference_id"],
                         "parent_source_file_reference": ref["source_file_reference"],
                         "source_sha256": ref["source_sha256"], "module_name": ref["declared_module_name"],
                         "source_position": deepcopy(ref["position"]), "lexical_scope": deepcopy(ref["lexical_scope"]),
                         "condition_ids": deepcopy(ref["condition_ids"]),
                         "candidate_root_id": candidate["root_id"], "candidate_pinned_commit": candidate["pinned_commit"],
                         "candidate_relative_path": candidate["path"], "candidate_origin": candidate["origin"],
                         "path_context": evaluate_path_context(ref, parent, candidate),
                         "allowlist_status": "allowlisted" if allowed is not None else "not_allowlisted",
                         "file_id": None if observation is None else observation["file_id"],
                         "read_status": read_status, "source_file_presence": presence, "regular_file": regular,
                         "observed_byte_size": size, "observed_sha256": sha, "candidate_status": status,
                         "alternatives_exhaustive": False, "resolved_file": False,
                         "compiler_resolution_verified": False, "limitations": list(LIMITATIONS)})
    statuses = Counter(row["candidate_status"] for row in rows)
    contexts = Counter(row["path_context"]["status"] for row in rows)
    external_count = sum(row["reference_kind"] == "external_module_declaration" for row in source_context["references"])
    counts = {"source_reference_count": len(source_context["references"]), "external_reference_count": external_count,
              "selected_reference_count": len(selected), "not_selected_external_reference_count": external_count - len(selected),
              "candidate_count": len(rows), "allowlisted_candidate_count": len(allowlist),
              "examined_candidate_count": sum(row["read_status"] != "read_not_performed" for row in rows),
              "present_candidate_count": statuses["candidate_present_unresolved"],
              "missing_candidate_count": statuses["candidate_missing"],
              "not_allowlisted_candidate_count": statuses["candidate_not_allowlisted"],
              "unique_observed_file_count": len(files),
              "present_file_count": sum(row["read_status"] == "present_and_hashed" for row in candidate_files),
              "missing_file_count": sum(row["read_status"] == "declared_file_missing" for row in candidate_files),
              "observed_file_bytes": sum(row["observed_byte_size"] or 0 for row in candidate_files),
              "ambiguous_path_context_candidate_count": contexts["context_ambiguous"],
              "unsupported_path_context_candidate_count": contexts["unsupported_path_context"],
              "by_candidate_status": [{"status": status, "candidate_count": statuses[status]} for status in CANDIDATE_STATUSES],
              "by_path_context": [{"status": status, "candidate_count": contexts[status]} for status in PATH_CONTEXT_STATUSES]}
    return {**common(LEDGER_SCHEMA, reference), "source_context": deepcopy(source_context),
            "review_scope": deepcopy(review_scope), "candidate_files": deepcopy(candidate_files),
            "candidates": rows, "counts": counts, "limitations": list(LIMITATIONS)}


def rebuild_evidence(evidence: dict) -> dict:
    return build_evidence(evidence["source_reference"], evidence["source_context"], evidence["review_scope"],
                          evidence["candidate_files"])


__all__ = ("build_evidence", "rebuild_evidence", "CANDIDATE_STATUSES")
