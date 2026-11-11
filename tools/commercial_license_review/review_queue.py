"""Keep every source subject in a deterministic read-only review queue."""
from __future__ import annotations

from .evidence_contracts import InputError, QUEUE_SCHEMA, QUEUE_GROUPS, common, validate_ledger


_GROUP_ORDER = QUEUE_GROUPS
_ACTION = {
    "conflicting_evidence": "review_source_conflicts_without_approval",
    "ambiguous_binding": "clarify_source_record_binding",
    "missing_evidence": "provide_scoped_local_evidence",
    "evidence_present_review_pending": "perform_independent_license_review",
    "unsupported_evidence": "provide_supported_evidence_format",
}
_STATUS_GROUP = {
    "binding_conflict": "conflicting_evidence",
    "binding_ambiguous": "ambiguous_binding",
    "source_not_verified": "ambiguous_binding",
    "evidence_missing": "missing_evidence",
    "evidence_unsupported": "unsupported_evidence",
    "evidence_present": "evidence_present_review_pending",
    "binding_confirmed_within_source": "evidence_present_review_pending",
}


def build_queue(ledger: dict, conflicts: dict) -> dict:
    ledger = validate_ledger(ledger)
    if conflicts["composition_reference"] != ledger["composition_reference"]:
        raise InputError("license_review_queue_composition_mismatch")
    states = {row["source_key"]: row for row in ledger["records"]}
    grouped = {row["source_key"]: [] for row in ledger["source_subjects"]}
    for binding in ledger["bindings"]:
        grouped[binding["source_key"]].append(binding)
    events = {row["source_key"]: set() for row in ledger["source_subjects"]}
    for conflict in conflicts["conflicts"]:
        if conflict["source_key"] not in events:
            raise InputError("license_review_queue_unknown_conflict_reference")
        events[conflict["source_key"]].add(conflict["category"])
    records = []
    for subject in ledger["source_subjects"]:
        key = subject["source_key"]
        record = states[key]
        groups = {_STATUS_GROUP[record["evidence_status"]]}
        groups.update(_STATUS_GROUP[binding["status"]] for binding in grouped[key])
        # Neither duplicate_content nor different_content creates a legal or
        # licensing conflict. Only explicit declaration disagreement does so.
        if "conflicting_license_declarations" in events[key]:
            groups.add("conflicting_evidence")
        ordered = [group for group in _GROUP_ORDER if group in groups]
        records.append({
            "source_key": key, "groups": ordered,
            "subject_type": subject["subject_type"], "subject_id": subject["subject_id"],
            "product_scope": subject["product_scope"],
            "evidence_status": record["evidence_status"], "review_status": record["review_status"],
            "next_human_action": _ACTION[ordered[0]],
            "phase24_source_license_id": subject["source_license_id"],
            "human_review_required": True,
        })
    by_group = [{"group": group, "record_count": sum(group in row["groups"] for row in records)}
                for group in _GROUP_ORDER if any(group in row["groups"] for row in records)]
    return {
        **common(QUEUE_SCHEMA, ledger["composition_reference"]), "records": records,
        "counts": {"unique_source_record_count": len(states), "queue_record_count": len(records),
                   "group_membership_count": sum(len(row["groups"]) for row in records),
                   "by_group": by_group},
    }


__all__ = ("build_queue",)
