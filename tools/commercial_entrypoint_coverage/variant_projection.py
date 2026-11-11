"""Project existing selections onto source evidence without inventing ownership."""
from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from collections import Counter

from .coverage_contracts import FALSE_FLAGS, LIMITATIONS, VARIANTS_SCHEMA, common
from .source_coverage import status_counts


def build_variants(coverage: dict, delta: dict) -> dict:
    proposals_by_target = {row["target_reference"]: [] for row in coverage["coverage"]}
    for proposal in delta["proposals"]:
        for target in proposal["source_target_references"]:
            proposals_by_target[target].append(proposal["proposal_reference"])
    variants = []
    for selection in coverage["source_context"]["variant_selections"]:
        selected = set(selection["selected_component_ids"])
        projections = []
        proposal_refs = set()
        for row in coverage["coverage"]:
            if (row["manifest_ownership_status"] == "definite_ownership"
                    and row["established_component_id"] in selected):
                relationship = "definite_source_metadata_scope"
            elif selected.intersection(row["candidate_component_ids"]):
                relationship = "candidate_scope_relevant_ownership_unresolved"
            else:
                relationship = "no_selected_component_relation_established"
            references = (sorted(proposals_by_target[row["target_reference"]])
                          if relationship != "no_selected_component_relation_established" else [])
            proposal_refs.update(references)
            projections.append({"target_reference": row["target_reference"],
                                "coverage_reference": row["coverage_reference"],
                                "source_file_reference": row["source_file_reference"],
                                "phase24_coverage_status": row["phase24_coverage_status"],
                                "component_ownership_status": row["component_ownership_status"],
                                "relationship": relationship, "proposal_references": references})
        relations = Counter(row["relationship"] for row in projections)
        variants.append({**deepcopy(selection), "target_projections": projections,
                         "proposal_references": sorted(proposal_refs), "demo_only": True,
                         **{flag: False for flag in FALSE_FLAGS},
                         "counts": {"target_reference_count": len(projections),
                                    "definite_source_metadata_target_count": relations["definite_source_metadata_scope"],
                                    "ownership_unresolved_candidate_target_count": relations["candidate_scope_relevant_ownership_unresolved"],
                                    "unattributed_target_count": relations["no_selected_component_relation_established"],
                                    "proposal_reference_count": len(proposal_refs),
                                    "by_coverage_status": status_counts(projections)}})
    comparisons = []
    for left, right in combinations(variants, 2):
        left_components, right_components = set(left["selected_component_ids"]), set(right["selected_component_ids"])
        left_targets = {row["target_reference"] for row in left["target_projections"]
                        if row["relationship"] != "no_selected_component_relation_established"}
        right_targets = {row["target_reference"] for row in right["target_projections"]
                         if row["relationship"] != "no_selected_component_relation_established"}
        left_proposals, right_proposals = set(left["proposal_references"]), set(right["proposal_references"])
        comparisons.append({"left": left["variant_id"], "right": right["variant_id"],
                            "shared_component_ids": sorted(left_components & right_components),
                            "only_left_component_ids": sorted(left_components - right_components),
                            "only_right_component_ids": sorted(right_components - left_components),
                            "shared_target_references": sorted(left_targets & right_targets),
                            "only_left_target_references": sorted(left_targets - right_targets),
                            "only_right_target_references": sorted(right_targets - left_targets),
                            "shared_proposal_references": sorted(left_proposals & right_proposals),
                            "only_left_proposal_references": sorted(left_proposals - right_proposals),
                            "only_right_proposal_references": sorted(right_proposals - left_proposals)})
    return {**common(VARIANTS_SCHEMA, coverage["source_reference"]), "variants": variants,
            "comparisons": comparisons,
            "counts": {"variant_count": len(variants), "global_target_count": len(coverage["coverage"]),
                       "global_proposal_count": len(delta["proposals"]),
                       "variant_target_reference_count": sum(len(row["target_projections"]) for row in variants)},
            "limitations": list(LIMITATIONS)}


__all__ = ("build_variants",)
