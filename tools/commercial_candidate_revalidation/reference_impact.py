"""Propagate explicit old file relations without inventing unaffected sources."""
from __future__ import annotations

from copy import deepcopy

from .revalidation_contracts import InputError
from .observation_comparison import COMPARISON_STATUSES, CHANGED_STATUSES, UNKNOWN_STATUSES


def build_reference_impact(ledger: dict, file_decisions: list[dict]) -> list[dict]:
    baseline = ledger["baseline_evidence"]
    decisions = {row["file_id"]: row for row in file_decisions}
    if len(decisions) != len(file_decisions):
        raise InputError("candidate_revalidation_duplicate_file_decision")
    selected = {row["file_id"] for row in ledger["review_scope"]["selected_files"]}
    by_reference = {}
    for candidate in baseline["candidates"]:
        by_reference.setdefault(candidate["reference_id"], []).append(candidate)
    rows = []
    for ref in baseline["source_context"]["references"]:
        if ref["reference_kind"] != "external_module_declaration":
            continue
        candidates = by_reference.get(ref["reference_id"], [])
        candidate_ids, file_ids, current_ids, statuses = [], set(), set(), set()
        reusable, blocked, changed, unknown = [], [], [], []
        for candidate in candidates:
            cid, file_id = candidate["candidate_id"], candidate["file_id"]
            candidate_ids.append(cid)
            decision = decisions.get(file_id)
            if decision is None:
                if file_id is not None or candidate["allowlist_status"] != "not_allowlisted":
                    raise InputError("candidate_revalidation_impact_file_not_bound")
                blocked.append(cid)
                unknown.append(cid)
                statuses.add("not_revalidated")
                continue
            if cid not in decision["candidate_ids"] or ref["reference_id"] not in decision["reference_ids"]:
                raise InputError("candidate_revalidation_impact_relation_not_bound")
            file_ids.add(file_id)
            if decision["current_observation_id"] is not None:
                current_ids.add(decision["current_observation_id"])
            status = decision["comparison_status"]
            statuses.add(status)
            (reusable if decision["reuse_allowed"] else blocked).append(cid)
            if status in CHANGED_STATUSES:
                changed.append(cid)
            if status in UNKNOWN_STATUSES:
                unknown.append(cid)
        impact = ("outside_scope" if not candidates else "candidate_change_observed" if changed else
                  "candidate_reuse_blocked" if blocked else "candidate_observations_reobserved")
        rows.append({"reference": deepcopy(ref), "candidate_ids": candidate_ids, "file_ids": sorted(file_ids),
                     "selected_file_ids": sorted(file_ids & selected), "current_observation_ids": sorted(current_ids),
                     "comparison_statuses": [status for status in COMPARISON_STATUSES if status in statuses],
                     "reusable_candidate_ids": reusable, "blocked_candidate_ids": blocked,
                     "changed_candidate_ids": changed, "unknown_candidate_ids": unknown, "impact_status": impact,
                     "counts": {"candidate_count": len(candidates), "baseline_file_count": len(file_ids),
                                "selected_file_count": len(file_ids & selected), "current_observation_count": len(current_ids),
                                "reusable_candidate_count": len(reusable), "blocked_candidate_count": len(blocked),
                                "changed_candidate_count": len(changed), "unknown_candidate_count": len(unknown)},
                     "reference_context_revalidated": False, "compiler_resolution_verified": False, "resolved_file": False})
    return rows


__all__ = ("build_reference_impact",)
