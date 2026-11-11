"""Pure observations about bindings; byte differences are not legal conflicts."""
from __future__ import annotations

from .evidence_contracts import CONFLICTS_SCHEMA, CONFLICT_CATEGORIES, common, validate_ledger


def build_conflicts(ledger: dict) -> dict:
    ledger = validate_ledger(ledger)
    evidence = {row["evidence_id"]: row for row in ledger["evidence_sources"]}
    records = {row["source_key"]: row for row in ledger["records"]}
    grouped = {row["source_key"]: [] for row in ledger["source_subjects"]}
    for binding in ledger["bindings"]:
        grouped[binding["source_key"]].append(binding)
    conflicts = []

    def add(category, source_key, selected):
        conflicts.append({
            "category": category, "source_key": source_key,
            "evidence_refs": list(dict.fromkeys(row["evidence_id"] for row in selected)),
            "request_refs": [row["request_id"] for row in selected],
            "human_review_required": True,
        })

    for subject in ledger["source_subjects"]:
        key = subject["source_key"]
        bindings = grouped[key]
        # A repeated request for one evidence ref is not a second content source.
        present = list(dict.fromkeys(row["evidence_id"] for row in bindings
                                     if evidence[row["evidence_id"]]["file_present"]))
        hashes = {}
        for ref in present:
            hashes.setdefault(evidence[ref]["sha256"], []).append(ref)
        repeated_refs = {ref for refs in hashes.values() if len(refs) > 1 for ref in refs}
        if repeated_refs:
            add("duplicate_content", key,
                [row for row in bindings if row["evidence_id"] in repeated_refs])
        if len(hashes) > 1:
            add("different_content", key, [row for row in bindings if row["evidence_id"] in present])
        if len(records[key]["observed_license_labels"]) > 1:
            add("conflicting_license_declarations", key,
                [row for row in bindings if row["status"] == "binding_confirmed_within_source"])
        for category, predicate in (
            ("ambiguous_binding", lambda row: row["status"] == "binding_ambiguous"),
            ("source_not_verified", lambda row: row["status"] == "source_not_verified"),
            ("evidence_missing", lambda row: row["status"] == "evidence_missing"),
            ("evidence_hash_mismatch", lambda row: "evidence_hash_mismatch" in row["reason_codes"]),
            ("unsupported_evidence", lambda row: row["status"] == "evidence_unsupported"),
            ("source_selector_mismatch", lambda row: "source_selector_mismatch" in row["reason_codes"]),
        ):
            selected = [row for row in bindings if predicate(row)]
            if selected:
                add(category, key, selected)
    by_category = [{"category": category, "record_count": sum(
        row["category"] == category for row in conflicts)} for category in CONFLICT_CATEGORIES
        if any(row["category"] == category for row in conflicts)]
    return {
        **common(CONFLICTS_SCHEMA, ledger["composition_reference"]), "conflicts": conflicts,
        "counts": {"conflict_count": len(conflicts), "by_category": by_category},
    }


__all__ = ("build_conflicts",)
