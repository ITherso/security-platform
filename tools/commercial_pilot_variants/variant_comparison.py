"""Compare explicit source choices and metadata states, never executable packages."""
from __future__ import annotations

from copy import deepcopy

from .component_selection import VARIANT_FIELDS, project_variants
from .variant_contracts import (
    ANALYSIS_SCHEMA, FALSE_FLAGS, InputError, MAX_COMPARISON_PAIRS, SCOPE_LIMITATIONS, common,
)


def _comparisons(pairs: list[dict], variants: list[dict], dependencies: dict) -> list[dict]:
    by_id = {row["variant_id"]: row for row in variants}
    result, seen = [], set()
    if len(pairs) > MAX_COMPARISON_PAIRS:
        raise InputError("variant_comparison_pair_limit")
    for pair in pairs:
        left_id, right_id = pair["left"], pair["right"]
        if (left_id not in by_id or right_id not in by_id or left_id == right_id
                or frozenset((left_id, right_id)) in seen):
            raise InputError("variant_comparison_pair_invalid")
        seen.add(frozenset((left_id, right_id)))
        left, right = by_id[left_id], by_id[right_id]
        only_left = [identity for identity in left["selected_component_ids"] if identity not in right["selected_component_ids"]]
        only_right = [identity for identity in right["selected_component_ids"] if identity not in left["selected_component_ids"]]
        shared = [identity for identity in left["selected_component_ids"] if identity in right["selected_component_ids"]]
        changes = []
        for dependency in dependencies["records"]:
            exposure = {row["variant_id"]: row["classification"] for row in dependency["exposures"]}
            if exposure[left_id] != exposure[right_id]:
                changes.append({"dependency_id": dependency["dependency_id"],
                                "left_classification": exposure[left_id], "right_classification": exposure[right_id]})
        result.append({"left": left_id, "right": right_id, "source_reference_ref": "/source_reference",
                       "only_left_component_ids": only_left, "only_right_component_ids": only_right,
                       "shared_component_ids": shared,
                       "component_counts": {"only_left": len(only_left), "only_right": len(only_right), "shared": len(shared)},
                       "dependency_classification_changes": changes,
                       "dependency_classification_change_count": len(changes),
                       "license_summary_left": deepcopy(left["license_summary"]),
                       "license_summary_right": deepcopy(right["license_summary"])})
    return result


def build_analysis(scope: dict, components: list[dict], manifests: list[dict], dependencies: dict,
                   licenses: dict, source_reference: dict) -> dict:
    selections = project_variants(scope["variants"], components)
    if (dependencies["source_reference"] != source_reference or licenses["source_reference"] != source_reference
            or dependencies["candidate_reference"] != scope["candidate_reference"]
            or licenses["candidate_reference"] != scope["candidate_reference"]):
        raise InputError("variant_projection_source_reference_mismatch")
    exposure_counts = {row["variant_id"]: row["classifications"] for row in dependencies["counts"]["by_variant"]}
    readiness = {row["variant_id"]: row for row in licenses["variants"]}
    variants = []
    for selection in selections:
        identity = selection["variant_id"]
        if identity not in exposure_counts or identity not in readiness:
            raise InputError("variant_projection_summary_missing")
        variants.append({**selection, "source_reference_ref": "/source_reference", "demo_only": True,
                         **{flag: False for flag in FALSE_FLAGS},
                         "dependency_exposure_counts": deepcopy(exposure_counts[identity]),
                         "license_summary": deepcopy(readiness[identity]["license_summary"]),
                         "open_blockers": deepcopy(readiness[identity]["open_blockers"])})
    return {**common(ANALYSIS_SCHEMA, scope["candidate_reference"]),
            "source_reference": deepcopy(source_reference),
            "source_counts": {"component_count": len(components),
                              "dependency_record_count": len(dependencies["records"]),
                              "license_record_count": len(licenses["records"]),
                              "base_unknown_license_count": licenses["counts"]["base_unknown_license_count"],
                              "evidence_present_record_count": licenses["counts"]["evidence_present_record_count"],
                              "missing_evidence_record_count": licenses["counts"]["missing_evidence_record_count"]},
            "component_catalog": deepcopy(components), "manifest_catalog": deepcopy(manifests),
            "variants": variants, "comparison_pairs": deepcopy(scope["comparison_pairs"]),
            "comparisons": _comparisons(scope["comparison_pairs"], variants, dependencies),
            "scope_limitations": list(SCOPE_LIMITATIONS)}


def rebuild_analysis(analysis: dict, dependencies: dict, licenses: dict) -> dict:
    scope = {"candidate_reference": analysis["candidate_reference"],
             "variants": [{name: deepcopy(row[name]) for name in VARIANT_FIELDS} for row in analysis["variants"]],
             "comparison_pairs": deepcopy(analysis["comparison_pairs"])}
    return build_analysis(scope, analysis["component_catalog"], analysis["manifest_catalog"],
                          dependencies, licenses, analysis["source_reference"])


__all__ = ("build_analysis", "rebuild_analysis")
