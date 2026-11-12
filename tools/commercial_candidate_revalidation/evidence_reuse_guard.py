"""A real metadata gate: rederive from primary observations, never old success."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from .revalidation_contracts import (InputError, LEDGER_SCHEMA, REUSE_SCHEMA, common, fixed, validate_common,
                                     validate_reference, validate_baseline_evidence, validate_review_scope,
                                     validate_current_observations)
from .observation_comparison import (build_ledger, compare_observations, COMPARISON_STATUSES, LIMITATIONS)
from .reference_impact import build_reference_impact


REUSE_STATUSES = ("fresh_candidate_byte_metadata_only", "fresh_absence_metadata_only", "blocked")


def _decide_file(historical: dict, current: dict | None) -> dict:
    # Deliberately ignore any caller-supplied comparison/status cache.
    comparison = compare_observations(historical, current)
    status, projection = comparison["comparison_status"], None
    if status == "bytes_reobserved_equal":
        reuse_status = "fresh_candidate_byte_metadata_only"
    elif status == "absence_reobserved":
        reuse_status = "fresh_absence_metadata_only"
    else:
        reuse_status = "blocked"
    allowed = reuse_status != "blocked"
    if allowed:
        if current is None:
            raise InputError("candidate_revalidation_projection_without_current_observation")
        projection = {"projection_kind": reuse_status, "current_observation_id": current["observation_id"],
                      "file_id": current["file_id"], "root_id": current["root_id"],
                      "pinned_commit": current["pinned_commit"], "path": current["path"],
                      "source_file_presence": current["source_file_presence"],
                      "current_observed_byte_size": current["current_observed_byte_size"],
                      "current_observed_sha256": current["current_observed_sha256"],
                      "read_stability": current["read_stability"], "reference_context_revalidated": False,
                      "compiler_resolution_verified": False, "module_closure_verified": False,
                      "component_ownership_verified": False, "resolved_file": False}
    reasons = ["current_candidate_byte_metadata_only" if status == "bytes_reobserved_equal" else
               "current_safe_absence_metadata_only" if status == "absence_reobserved" else
               "historical_observation_reuse_blocked", "reference_context_not_revalidated",
               "physical_identity_not_comparable", "no_historical_success_fallback"]
    return {"file_id": historical["file_id"], "historical_observation_id": historical["observation_id"],
            "current_observation_id": None if current is None else current["observation_id"],
            "candidate_ids": deepcopy(historical["candidate_ids"]), "reference_ids": deepcopy(historical["reference_ids"]),
            "comparison_status": status, "reuse_allowed": allowed, "reuse_status": reuse_status,
            "projection": projection, "reason_codes": reasons, "identity_comparison": "not_comparable",
            "reference_context_revalidated": False, "compiler_resolution_verified": False, "resolved_file": False}


def _validated_decisions(ledger: dict) -> tuple[dict, list[dict]]:
    # Primitive validation only: the full Phase31 validator itself calls this
    # builder. The nested old Phase30 validator never imports Phase31 code.
    row = validate_common(ledger, LEDGER_SCHEMA, ("baseline_evidence", "review_scope", "current_observations",
                                                "historical_observations", "comparisons", "counts", "limitations"))
    reference = validate_reference(row["source_reference"])
    baseline = validate_baseline_evidence(row["baseline_evidence"], reference)
    review = validate_review_scope(row["review_scope"], baseline)
    currents = validate_current_observations(row["current_observations"], review, baseline)
    rebuilt = build_ledger(reference, baseline, review, currents)
    # Reject a malformed or contradictory declared ledger rather than accepting
    # its derived status as authority. This is still no call to the full validator.
    fixed(row, rebuilt, "reuse_guard_ledger_projection")
    by_file = {current["file_id"]: current for current in currents}
    return rebuilt, [_decide_file(historical, by_file.get(historical["file_id"]))
                     for historical in rebuilt["historical_observations"]]


def get_reusable_projection(ledger: dict, file_id: str) -> dict | None:
    """The public consumer path; blocked files return None, never baseline data."""
    _rebuilt, decisions = _validated_decisions(ledger)
    decision = next((row for row in decisions if row["file_id"] == file_id), None)
    if decision is None:
        raise InputError("candidate_revalidation_unknown_reuse_file")
    return deepcopy(decision["projection"])


def build_reuse(ledger: dict) -> dict:
    rebuilt, decisions = _validated_decisions(ledger)
    by_file = {row["file_id"]: row for row in decisions}
    candidates = []
    for candidate in rebuilt["baseline_evidence"]["candidates"]:
        file_id = candidate["file_id"]
        decision = by_file.get(file_id)
        if decision is None:
            if file_id is not None or candidate["allowlist_status"] != "not_allowlisted":
                raise InputError("candidate_revalidation_candidate_file_not_bound")
            history_id, current_id, status, allowed, reuse_status, projection = None, None, "not_revalidated", False, "blocked", None
            reasons = ["candidate_not_previously_allowlisted", "no_historical_observation_available",
                       "reference_context_not_revalidated", "no_historical_success_fallback"]
        else:
            if candidate["candidate_id"] not in decision["candidate_ids"]:
                raise InputError("candidate_revalidation_candidate_decision_not_bound")
            history_id, current_id = decision["historical_observation_id"], decision["current_observation_id"]
            status, allowed, reuse_status = decision["comparison_status"], decision["reuse_allowed"], decision["reuse_status"]
            projection, reasons = deepcopy(decision["projection"]), deepcopy(decision["reason_codes"])
        candidates.append({"candidate_id": candidate["candidate_id"], "reference_id": candidate["reference_id"],
                           "file_id": file_id, "baseline_allowlist_status": candidate["allowlist_status"],
                           "baseline_candidate_status": candidate["candidate_status"],
                           "historical_observation_id": history_id, "current_observation_id": current_id,
                           "comparison_status": status, "reuse_allowed": allowed, "reuse_status": reuse_status,
                           "projection": projection, "reason_codes": reasons,
                           "path_context": deepcopy(candidate["path_context"]), "condition_ids": deepcopy(candidate["condition_ids"]),
                           "alternatives_exhaustive": False, "reference_context_revalidated": False,
                           "compiler_resolution_verified": False, "resolved_file": False})
    impacts = build_reference_impact(rebuilt, decisions)
    comparisons = Counter(row["comparison_status"] for row in decisions)
    statuses = Counter(row["reuse_status"] for row in decisions)
    impact_counts = Counter(row["impact_status"] for row in impacts)
    counts = {"historical_file_count": len(decisions),
              "revalidated_file_count": len(rebuilt["current_observations"]),
              "not_revalidated_file_count": comparisons["not_revalidated"],
              "reusable_file_count": sum(row["reuse_allowed"] for row in decisions),
              "blocked_file_count": sum(not row["reuse_allowed"] for row in decisions),
              "fresh_byte_projection_file_count": statuses["fresh_candidate_byte_metadata_only"],
              "fresh_absence_projection_file_count": statuses["fresh_absence_metadata_only"],
              "candidate_count": len(candidates), "reusable_candidate_count": sum(row["reuse_allowed"] for row in candidates),
              "blocked_candidate_count": sum(not row["reuse_allowed"] for row in candidates),
              "reference_count": len(impacts), "references_with_change_count": impact_counts["candidate_change_observed"],
              "references_with_blocked_reuse_count": sum(bool(row["blocked_candidate_ids"]) for row in impacts),
              "references_reobserved_with_context_unverified_count": impact_counts["candidate_observations_reobserved"],
              "outside_scope_reference_count": impact_counts["outside_scope"],
              "by_comparison_status": [{"status": status, "file_count": comparisons[status]} for status in COMPARISON_STATUSES],
              "by_reuse_status": [{"status": status, "file_count": statuses[status]} for status in REUSE_STATUSES]}
    return {**common(REUSE_SCHEMA, rebuilt["source_reference"]), "files": decisions, "candidates": candidates,
            "reference_impact": impacts, "counts": counts, "limitations": list(LIMITATIONS)}


__all__ = ("build_reuse", "get_reusable_projection", "REUSE_STATUSES")
