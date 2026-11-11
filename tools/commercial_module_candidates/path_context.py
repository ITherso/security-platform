"""Candidate provenance is not Rust path resolution or source ownership."""
from __future__ import annotations


PATH_CONTEXT_STATUSES = ("supported_static_path_context", "explicit_operator_candidate",
                         "context_ambiguous", "unsupported_path_context")
LIMITATIONS = (
    "explicit_selected_candidates_only", "candidate_presence_is_not_rust_module_resolution",
    "operator_selection_is_not_literal_source_path_evidence", "unexamined_alternatives_remain_unknown",
    "feature_and_target_conditions_not_evaluated", "no_recursive_source_discovery_or_lexing",
    "global_f_catalog_is_not_component_ownership", "phase28_scope_delta_remains_unapplied",
    "observed_hash_is_not_git_or_producer_attestation",
    "inspector_checks_projected_metadata_not_original_files",
)


def evaluate_path_context(reference: dict, parent_source: dict, candidate: dict) -> dict:
    """Never manufacture a path from a module name or trust a scope proof label."""
    reasons = []
    if reference["reference_kind"] != "external_module_declaration":
        status, reasons = "unsupported_path_context", ["reference_not_external_module"]
    elif (candidate["root_id"] != parent_source["root_id"]
          or candidate["pinned_commit"] != parent_source["pinned_commit"]):
        status, reasons = "unsupported_path_context", ["source_root_or_commit_mismatch"]
    elif reference["lexical_scope"] or reference["parent_inline_reference"] is not None:
        status, reasons = "context_ambiguous", ["inline_module_base_not_established"]
    elif reference["context_reliability"] != "lexically_bounded":
        status, reasons = "context_ambiguous", ["lexical_context_not_supported"]
    elif reference["interpretation_status"] != "observed_static_reference":
        status, reasons = "context_ambiguous", ["reference_interpretation_not_supported"]
    elif candidate["origin"] == "explicit_operator_candidate":
        status, reasons = "explicit_operator_candidate", ["operator_candidate_not_compiler_resolution"]
    elif candidate["origin"] == "context_ambiguous":
        status, reasons = "context_ambiguous", ["declared_context_ambiguous"]
    elif candidate["origin"] == "supported_static_path_context":
        # The selected v1 form is an ordinary external mod with no literal
        # path. A caller's label and filename resemblance cannot add evidence.
        status, reasons = "unsupported_path_context", ["literal_source_path_evidence_missing"]
    else:
        status, reasons = "unsupported_path_context", ["declared_context_unsupported"]
    if reference["condition_ids"]:
        reasons.append("condition_evaluation_not_performed")
    return {"status": status, "reason_codes": reasons, "condition_evaluation": "not_performed",
            "compiler_resolution_verified": False}


__all__ = ("evaluate_path_context", "PATH_CONTEXT_STATUSES", "LIMITATIONS")
