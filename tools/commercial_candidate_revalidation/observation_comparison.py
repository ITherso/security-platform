"""Pure historical/current comparison; never read files or refresh old rows."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import re

from .revalidation_contracts import InputError, LEDGER_SCHEMA, common, record_digest


COMPARISON_STATUSES = ("bytes_reobserved_equal", "bytes_changed", "previously_present_now_missing",
                       "previously_missing_now_present", "absence_reobserved", "not_revalidated",
                       "revalidation_inconclusive")
CHANGED_STATUSES = frozenset(("bytes_changed", "previously_present_now_missing", "previously_missing_now_present"))
UNKNOWN_STATUSES = frozenset(("not_revalidated", "revalidation_inconclusive"))
LIMITATIONS = (
    "selected_prior_allowlist_subset_only", "historical_observations_are_not_current_fallback",
    "byte_equality_is_not_physical_identity", "historical_physical_identity_not_recorded",
    "reference_context_not_revalidated", "no_rust_module_resolution_or_source_discovery",
    "phase24_membership_and_phase28_delta_not_refreshed", "reuse_guard_applies_only_to_this_tool",
    "instant_observation_without_ttl", "inspector_checks_recorded_metadata_only",
)


def _index(rows: list[dict], key: str) -> dict:
    result = {}
    for row in rows:
        if row[key] in result:
            raise InputError("candidate_revalidation_duplicate_primary_identity")
        result[row[key]] = row
    return result


def historical_identifier(artifact_sha256: str, observation: dict) -> str:
    return "historical-observation-" + record_digest({"baseline_artifact_sha256": artifact_sha256,
                                                      "observation": observation})


def comparison_identifier(historical_id: str, current_id: str | None) -> str:
    return "observation-comparison-" + record_digest({"historical_observation_id": historical_id,
                                                      "current_observation_id": current_id})


def _present_metadata(size: object, sha: object) -> bool:
    return (type(size) is int and size >= 0 and type(sha) is str
            and re.fullmatch(r"[0-9a-f]{64}", sha) is not None)


def compare_observations(historical: dict, current: dict | None) -> dict:
    """Compare typed observations, never interpret I/O exceptions as changes."""
    old = historical["observation"]
    file_id = historical["file_id"]
    if old["file_id"] != file_id or historical["candidate_ids"] != old["candidate_ids"]:
        raise InputError("candidate_revalidation_historical_identity_mismatch")
    old_status = old["read_status"]
    if old_status not in ("present_and_hashed", "declared_file_missing"):
        raise InputError("candidate_revalidation_historical_status_unsupported")
    reasons, equal = [], None
    if current is None:
        status = "not_revalidated"
        reasons.append("file_not_selected_for_revalidation")
    else:
        if (current["file_id"] != file_id
                or any(current[key] != old[key] for key in ("root_id", "pinned_commit", "path", "candidate_ids"))
                or current["baseline_sha256"] != old["observed_sha256"]):
            raise InputError("candidate_revalidation_observation_source_mismatch")
        now_status = current["read_status"]
        if now_status == "present_and_hashed":
            if (current["source_file_presence"] != "present" or current["regular_file"] is not True
                    or current["read_stability"] != "stable_bounded_read"
                    or not _present_metadata(current["current_observed_byte_size"], current["current_observed_sha256"])):
                raise InputError("candidate_revalidation_current_present_metadata_invalid")
        elif now_status == "declared_file_missing":
            if (current["source_file_presence"] != "missing" or current["read_stability"] != "safe_absence_observed"
                    or any(current[key] is not None for key in
                           ("regular_file", "current_observed_byte_size", "current_observed_sha256"))):
                raise InputError("candidate_revalidation_current_absence_metadata_invalid")
        else:
            raise InputError("candidate_revalidation_current_status_unsupported")
        if current["physical_identity"] != "not_exported":
            raise InputError("candidate_revalidation_physical_identity_claim_rejected")
        if old_status == "present_and_hashed" and (old["observed_byte_size"] is None or old["observed_sha256"] is None):
            status = "revalidation_inconclusive"
            reasons.append("historical_byte_metadata_unavailable")
        elif old_status == "present_and_hashed":
            if (old["source_file_presence"] != "present" or old["regular_file"] is not True
                    or not _present_metadata(old["observed_byte_size"], old["observed_sha256"])):
                raise InputError("candidate_revalidation_historical_present_metadata_invalid")
            if now_status == "declared_file_missing":
                status = "previously_present_now_missing"
                reasons.append("previously_present_path_absence_observed")
            else:
                equal = (old["observed_byte_size"] == current["current_observed_byte_size"]
                         and old["observed_sha256"] == current["current_observed_sha256"])
                status = "bytes_reobserved_equal" if equal else "bytes_changed"
                reasons.append("identical_size_and_sha256_reobserved" if equal else "size_or_sha256_changed_between_observations")
        else:
            if (old["source_file_presence"] != "missing" or any(old[key] is not None for key in
                    ("regular_file", "observed_byte_size", "observed_sha256"))):
                raise InputError("candidate_revalidation_historical_absence_metadata_invalid")
            status = "absence_reobserved" if now_status == "declared_file_missing" else "previously_missing_now_present"
            reasons.append("absence_safely_reobserved" if now_status == "declared_file_missing"
                           else "previously_absent_path_now_present")
    reasons.extend(("historical_physical_identity_not_recorded", "reference_context_not_revalidated"))
    current_id = None if current is None else current["observation_id"]
    return {"comparison_id": comparison_identifier(historical["observation_id"], current_id),
            "file_id": file_id, "historical_observation_id": historical["observation_id"],
            "current_observation_id": current_id, "candidate_ids": deepcopy(historical["candidate_ids"]),
            "reference_ids": deepcopy(historical["reference_ids"]), "comparison_status": status,
            "bytes_equal": equal, "identity_comparison": "not_comparable",
            "historical_physical_identity": "not_recorded", "reason_codes": reasons,
            "reference_context_revalidated": False, "compiler_resolution_verified": False, "resolved_file": False}


def build_ledger(reference: dict, baseline_evidence: dict, review_scope: dict,
                  current_observations: list[dict]) -> dict:
    candidates = _index(baseline_evidence["candidates"], "candidate_id")
    historical_files = _index(baseline_evidence["candidate_files"], "file_id")
    current = _index(current_observations, "file_id")
    selected = _index(review_scope["selected_files"], "file_id")
    if set(current) != set(selected) or not set(current).issubset(historical_files):
        raise InputError("candidate_revalidation_current_selection_mismatch")
    histories, comparisons = [], []
    artifact_sha = reference["baseline_sources"]["evidence"]["sha256"]
    for file_id in sorted(historical_files):
        old = historical_files[file_id]
        relation_ids = []
        for cid in old["candidate_ids"]:
            candidate = candidates.get(cid)
            if (candidate is None or candidate["file_id"] != file_id
                    or candidate["allowlist_status"] != "allowlisted"):
                raise InputError("candidate_revalidation_historical_candidate_not_bound")
            relation_ids.append(candidate["reference_id"])
        historical = {"observation_id": historical_identifier(artifact_sha, old),
                      "baseline_artifact_sha256": artifact_sha, "file_id": file_id,
                      "candidate_ids": deepcopy(old["candidate_ids"]), "reference_ids": sorted(set(relation_ids)),
                      "observation": deepcopy(old), "historical_physical_identity": "not_recorded"}
        histories.append(historical)
        comparisons.append(compare_observations(historical, current.get(file_id)))
    categories = Counter(row["comparison_status"] for row in comparisons)
    counts = {"historical_file_count": len(histories), "selected_file_count": len(selected),
              "current_observation_count": len(current_observations),
              "current_present_file_count": sum(row["read_status"] == "present_and_hashed" for row in current_observations),
              "current_missing_file_count": sum(row["read_status"] == "declared_file_missing" for row in current_observations),
              "current_observed_bytes": sum(row["current_observed_byte_size"] or 0 for row in current_observations),
              "not_revalidated_file_count": categories["not_revalidated"],
              "baseline_candidate_count": len(baseline_evidence["candidates"]),
              "baseline_external_reference_count": sum(row["reference_kind"] == "external_module_declaration"
                                                        for row in baseline_evidence["source_context"]["references"]),
              "comparison_count": len(comparisons),
              "by_comparison_status": [{"status": status, "file_count": categories[status]} for status in COMPARISON_STATUSES]}
    return {**common(LEDGER_SCHEMA, reference), "baseline_evidence": deepcopy(baseline_evidence),
            "review_scope": deepcopy(review_scope), "current_observations": deepcopy(current_observations),
            "historical_observations": histories, "comparisons": comparisons,
            "counts": counts, "limitations": list(LIMITATIONS)}


def rebuild_ledger(ledger: dict) -> dict:
    return build_ledger(ledger["source_reference"], ledger["baseline_evidence"], ledger["review_scope"],
                        ledger["current_observations"])


__all__ = ("build_ledger", "rebuild_ledger", "compare_observations", "historical_identifier",
           "comparison_identifier", "COMPARISON_STATUSES", "CHANGED_STATUSES", "UNKNOWN_STATUSES", "LIMITATIONS")
