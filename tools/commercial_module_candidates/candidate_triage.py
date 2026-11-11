"""Disjoint primary triage with overlapping factual states and no resolver."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from .candidate_contracts import TRIAGE_SCHEMA, common
from .path_context import LIMITATIONS


TRIAGE_STATUSES = ("candidate_present_unresolved", "candidate_missing", "candidate_not_allowlisted",
                   "candidate_set_ambiguous", "path_context_unresolved", "not_examined")
NEXT_VALIDATION = ("explicit_candidate_relation_review_required", "unexamined_alternatives_remain_unknown",
                   "compiler_module_resolution_not_performed", "condition_feature_target_evaluation_not_performed")


def build_triage(evidence: dict) -> dict:
    selected = {row["reference"]["reference_id"]: row for row in evidence["review_scope"]["selected_references"]}
    by_reference = {}
    for row in evidence["candidates"]:
        by_reference.setdefault(row["reference_id"], []).append(row)
    rows = []
    for ref in evidence["source_context"]["references"]:
        if ref["reference_kind"] != "external_module_declaration":
            continue
        choice = selected.get(ref["reference_id"])
        candidates = by_reference.get(ref["reference_id"], [])
        present = sum(row["candidate_status"] == "candidate_present_unresolved" for row in candidates)
        missing = sum(row["candidate_status"] == "candidate_missing" for row in candidates)
        not_allowed = sum(row["candidate_status"] == "candidate_not_allowlisted" for row in candidates)
        examined = sum(row["read_status"] != "read_not_performed" for row in candidates)
        uncertain = sum(row["path_context"]["status"] in ("context_ambiguous", "unsupported_path_context") for row in candidates)
        active = set()
        if present:
            active.add("candidate_present_unresolved")
        if missing:
            active.add("candidate_missing")
        if not_allowed:
            active.add("candidate_not_allowlisted")
        if present > 1:
            active.add("candidate_set_ambiguous")
        if uncertain:
            active.add("path_context_unresolved")
        if examined == 0:
            active.add("not_examined")
        if choice is None or not candidates:
            primary = "not_examined"
        elif present > 1:
            primary = "candidate_set_ambiguous"
        elif uncertain:
            primary = "path_context_unresolved"
        elif present:
            primary = "candidate_present_unresolved"
        elif not_allowed:
            primary = "candidate_not_allowlisted"
        elif missing:
            primary = "candidate_missing"
        else:
            primary = "not_examined"
        rows.append({"reference": deepcopy(ref), "selected": choice is not None,
                     "inspection_scope": "not_selected" if choice is None else choice["inspection_scope"],
                     "candidate_ids": [row["candidate_id"] for row in candidates],
                     "candidate_file_ids": sorted({row["file_id"] for row in candidates if row["file_id"] is not None}),
                     "condition_ids": deepcopy(ref["condition_ids"]), "primary_status": primary,
                     "statuses": [status for status in TRIAGE_STATUSES if status in active],
                     "counts": {"declared_candidate_count": len(candidates),
                                "allowlisted_candidate_count": sum(row["allowlist_status"] == "allowlisted" for row in candidates),
                                "examined_candidate_count": examined, "present_candidate_count": present,
                                "missing_candidate_count": missing, "not_allowlisted_candidate_count": not_allowed,
                                "unexamined_candidate_count": len(candidates) - examined,
                                "path_context_unresolved_candidate_count": uncertain},
                     "alternatives_exhaustive": False, "unexamined_alternatives": "not_exhaustively_enumerated",
                     "condition_evaluation": "not_performed", "compiler_resolution_verified": False,
                     "resolved_file": False, "next_validation": list(NEXT_VALIDATION)})
    primary = Counter(row["primary_status"] for row in rows)
    secondary = Counter(status for row in rows for status in row["statuses"])
    counts = {"external_reference_count": len(rows), "selected_reference_count": len(selected),
              "unselected_reference_count": sum(not row["selected"] for row in rows),
              "examined_reference_count": sum(row["counts"]["examined_candidate_count"] > 0 for row in rows),
              "not_examined_reference_count": sum(row["counts"]["examined_candidate_count"] == 0 for row in rows),
              "candidate_relation_count": len(evidence["candidates"]),
              "unique_observed_file_count": len(evidence["candidate_files"]),
              "by_primary_status": [{"status": status, "reference_count": primary[status]} for status in TRIAGE_STATUSES],
              "by_status": [{"status": status, "reference_count": secondary[status]} for status in TRIAGE_STATUSES]}
    return {**common(TRIAGE_SCHEMA, evidence["source_reference"]), "references": rows,
            "counts": counts, "limitations": list(LIMITATIONS)}


__all__ = ("build_triage", "TRIAGE_STATUSES", "NEXT_VALIDATION")
