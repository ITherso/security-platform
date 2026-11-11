"""Preserve every license subject and open source blocker across each variant."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from commercial_composition.composition_contracts import BLOCKER_CODES
from commercial_license_review.conflict_analysis import build_conflicts as source_conflicts
from commercial_license_review.evidence_contracts import (
    LEDGER_SCHEMA as SOURCE_LEDGER_SCHEMA, RECORD_FIELDS, SUBJECT_FIELDS,
    common as source_common,
)
from .variant_contracts import (
    BLOCKER_RELATIONS, InputError, LICENSES_SCHEMA, LICENSE_RELATIONS, common,
)


def _old_reference(reference: dict) -> dict:
    return {"candidate_reference": reference["composition_candidate_reference"],
            "source_commits": deepcopy(reference["source_commits"]),
            **{role: {name: reference["composition_sources"][role][name] for name in ("bytes", "sha256")}
               for role in ("inventory", "dependencies", "constraints", "summary", "manifest")}}


def _source_ledger(records: list[dict], evidence: list[dict], bindings: list[dict], reference: dict) -> dict:
    states = Counter(row["evidence_status"] for row in records)
    return {**source_common(SOURCE_LEDGER_SCHEMA, _old_reference(reference)),
            "source_subjects": [{name: deepcopy(row[name]) for name in SUBJECT_FIELDS} for row in records],
            "records": [{name: deepcopy(row[name]) for name in RECORD_FIELDS} for row in records],
            "evidence_sources": deepcopy(evidence), "bindings": deepcopy(bindings),
            "counts": {"source_record_count": len(records), "base_unknown_license_count": sum(
                row["base_declared_license"] is None or row["base_evidence_level"] == "conflicting_declarations"
                for row in records), "evidence_file_count": sum(row["file_present"] for row in evidence),
                "binding_request_count": len(bindings),
                **{field: states[status] for field, status in (
                    ("evidence_present_record_count", "evidence_present"),
                    ("missing_evidence_record_count", "evidence_missing"),
                    ("ambiguous_record_count", "binding_ambiguous"),
                    ("conflicting_record_count", "binding_conflict"),
                    ("unsupported_record_count", "evidence_unsupported"),
                    ("unverified_source_record_count", "source_not_verified"))}}}


def _unknown(row: dict) -> bool:
    return row["base_declared_license"] is None or row["base_evidence_level"] == "conflicting_declarations"


def _relation(row: dict, variant: dict, dependency_by_key: dict) -> str:
    if row["subject_type"] == "component":
        return "selected_component" if row["subject_id"] in variant["selected_component_ids"] else "not_selected_component"
    dependency = dependency_by_key.get(row["source_key"])
    if dependency is None or dependency["dependency_id"] != row["subject_id"]:
        raise InputError("variant_license_dependency_reference_missing")
    matches = [item for item in dependency["exposures"] if item["variant_id"] == variant["variant_id"]]
    if len(matches) != 1:
        raise InputError("variant_license_dependency_exposure_missing")
    classification = matches[0]["classification"]
    if classification == "excluded_context_record":
        return "excluded_context"
    if classification in ("explicit_component_link", "declared_source_scope", "shared_or_ambiguous_scope"):
        return "related_dependency_scope"
    return "unattributed_dependency"


def _blocker_rows(counter: Counter) -> list[dict]:
    return [{"code": code, "record_count": counter[code]} for code in BLOCKER_CODES]


def _variant_summary(records: list[dict], variant_id: str, candidate_codes: list[str]) -> dict:
    relation_records = {relation: [] for relation in LICENSE_RELATIONS}
    for row in records:
        matches = [item for item in row["variant_relations"] if item["variant_id"] == variant_id]
        if len(matches) != 1:
            raise InputError("variant_license_relation_missing")
        relation_records[matches[0]["relation"]].append(row)
    license_counts, blocker_counts = [], {}
    for relation in LICENSE_RELATIONS:
        selected = relation_records[relation]
        states = Counter(row["evidence_status"] for row in selected)
        license_counts.append({
            "relation": relation, "record_count": len(selected),
            "unknown_license_count": sum(_unknown(row) for row in selected),
            "evidence_present_record_count": states["evidence_present"],
            "missing_evidence_record_count": states["evidence_missing"],
            "human_review_required_record_count": sum(row["human_review_required"] for row in selected),
            "ambiguous_record_count": states["binding_ambiguous"],
            "conflicting_record_count": states["binding_conflict"],
            "unsupported_record_count": states["evidence_unsupported"],
            "unverified_source_record_count": states["source_not_verified"],
        })
        blocker_counts[relation] = Counter(code for row in selected for code in row["source_blocker_codes"])
    blocker_counts["candidate_scope_unassigned"] = Counter(candidate_codes)
    total = Counter()
    by_relation = []
    for relation in BLOCKER_RELATIONS:
        counter = blocker_counts[relation]
        total.update(counter)
        by_relation.append({"relation": relation, "blocker_count": sum(counter.values()),
                            "by_code": _blocker_rows(counter)})
    return {"variant_id": variant_id,
            "license_summary": {"global_source_record_count": len(records),
                                "global_unknown_license_count": sum(_unknown(row) for row in records),
                                "by_relation": license_counts},
            "open_blockers": {"source_blocker_count": sum(total.values()),
                              "by_code": _blocker_rows(total), "by_relation": by_relation}}


def _project(records: list[dict], evidence: list[dict], bindings: list[dict], candidate_codes: list[str],
             dependencies: dict, variants: list[dict], reference: dict, candidate_reference: str) -> dict:
    dependency_by_key = {row["license_source_key"]: row for row in dependencies["records"]}
    projected, keys = [], set()
    for row in records:
        if row["source_key"] in keys:
            raise InputError("variant_license_duplicate_source_key")
        keys.add(row["source_key"])
        original = {name: deepcopy(row[name]) for name in dict.fromkeys((*SUBJECT_FIELDS, *RECORD_FIELDS))}
        projected.append({**original, "queue_groups": deepcopy(row["queue_groups"]),
                          "next_human_action": row["next_human_action"],
                          "source_blocker_codes": deepcopy(row["source_blocker_codes"]),
                          "variant_relations": [{"variant_id": variant["variant_id"],
                                                 "relation": _relation(row, variant, dependency_by_key)}
                                                for variant in variants]})
    original_ledger = _source_ledger(projected, evidence, bindings, reference)
    conflicts = source_conflicts(original_ledger)
    states = Counter(row["evidence_status"] for row in projected)
    blocker_count = len(candidate_codes) + sum(len(row["source_blocker_codes"]) for row in projected)
    return {**common(LICENSES_SCHEMA, candidate_reference), "source_reference": deepcopy(reference),
            "records": projected, "evidence_catalog": deepcopy(evidence), "bindings": deepcopy(bindings),
            "conflict_summary": deepcopy(conflicts["counts"]), "candidate_blocker_codes": list(candidate_codes),
            "variants": [_variant_summary(projected, variant["variant_id"], candidate_codes) for variant in variants],
            "counts": {"source_license_record_count": len(projected),
                       "component_license_record_count": sum(row["subject_type"] == "component" for row in projected),
                       "dependency_license_record_count": sum(row["subject_type"] == "dependency" for row in projected),
                       "base_unknown_license_count": sum(_unknown(row) for row in projected),
                       "evidence_present_record_count": states["evidence_present"],
                       "missing_evidence_record_count": states["evidence_missing"],
                       "human_review_required_record_count": sum(row["human_review_required"] for row in projected),
                       "source_blocker_count": blocker_count, "variant_count": len(variants)}}


def build_readiness(constraints: dict, evidence_ledger: dict, evidence_queue: dict,
                    evidence_conflicts: dict, dependencies: dict, variants: list[dict], source_reference: dict,
                    *, candidate_reference: str) -> dict:
    subjects = {row["source_key"]: row for row in evidence_ledger["source_subjects"]}
    queue = {row["source_key"]: row for row in evidence_queue["records"]}
    subject_codes = {(row["subject_type"], row["subject_id"]): [] for row in subjects.values()}
    candidate_codes = []
    for blocker in constraints["blockers"]:
        if blocker["subject_type"] == "candidate":
            candidate_codes.append(blocker["code"])
        else:
            identity = (blocker["subject_type"], blocker["subject_id"])
            if identity not in subject_codes:
                raise InputError("variant_source_blocker_subject_missing")
            subject_codes[identity].append(blocker["code"])
    records = []
    for record in evidence_ledger["records"]:
        subject = subjects.get(record["source_key"])
        queued = queue.get(record["source_key"])
        if subject is None or queued is None:
            raise InputError("variant_source_license_queue_projection_missing")
        records.append({**deepcopy(subject), **deepcopy(record), "queue_groups": deepcopy(queued["groups"]),
                        "next_human_action": queued["next_human_action"],
                        "source_blocker_codes": subject_codes[(subject["subject_type"], subject["subject_id"])]})
    if len(records) != len(subjects) or len(records) != len(queue):
        raise InputError("variant_source_license_projection_incomplete")
    result = _project(records, evidence_ledger["evidence_sources"], evidence_ledger["bindings"],
                      candidate_codes, dependencies, variants, source_reference, candidate_reference)
    if result["conflict_summary"] != evidence_conflicts["counts"]:
        raise InputError("variant_source_conflict_summary_mismatch")
    return result


def rebuild_readiness(document: dict, dependencies: dict, variants: list[dict]) -> dict:
    """Recompute internal evidence/relation/blocker counts without source I/O."""
    return _project(document["records"], document["evidence_catalog"], document["bindings"],
                    document["candidate_blocker_codes"], dependencies, variants,
                    document["source_reference"], document["candidate_reference"])


__all__ = ("build_readiness", "rebuild_readiness")
