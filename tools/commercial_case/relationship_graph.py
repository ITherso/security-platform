"""Finite relationship graph; content consistency never establishes a run."""
from __future__ import annotations

from .artifact_reader import ValidatedArtifacts
from .case_contracts import CaseEvidence, InputError, RELATIONSHIP_DEFINITIONS, Relationship


_LIMITATIONS = {
    "plan_files": ("selected_plan_preflight_catalog_entries_only", "plan_summary_not_read"),
    "assessment_file": ("selected_json_entry_and_summary_only", "html_payload_not_read", "full_bundle_not_verified"),
    "intake_files": ("selected_handoff_mapping_payload_entries",),
    "observation_binding": ("pointer_fingerprint_disposition_metadata_only", "producer_not_verified"),
    "review_packet_files": ("packet_and_empty_template_entries_only", "worksheet_payload_not_read"),
    "review_binding": ("empty_overlay_is_not_human_review", "human_review_not_verified"),
    "reconciliation_files": ("selected_reconciled_input_entry_only", "reconciliation_markdown_not_read"),
    "reconciliation_binding": ("existing_payload_metadata_relation_only", "no_phase19_builder_execution_proof"),
    "traceability_files": ("execution_binding_not_established", "traceability_summary_not_read"),
    "handoff_files": ("selected_markdown_entries_only", "handoff_html_payload_not_read", "same_input_bytes_only", "historical_builder_stage_preserved"),
    "plan_execution": ("no_trusted_run_link", "capability_overlap_not_execution"),
}


def build_relationship_graph(artifacts: ValidatedArtifacts) -> CaseEvidence:
    """Only a successfully validated source set can reach this bounded graph."""
    if type(artifacts) is not ValidatedArtifacts or len(artifacts.artifacts) != 20:
        raise InputError("case_invalid_validated_artifacts")
    relationships = tuple(Relationship(
        relation_id, kind,
        "not_established" if relation_id == "plan_execution" else "content_consistent",
        roles, _LIMITATIONS[relation_id],
    ) for relation_id, (kind, roles) in RELATIONSHIP_DEFINITIONS.items())
    return CaseEvidence(artifacts.artifacts, relationships, artifacts.observations, artifacts.facts)


__all__ = ("build_relationship_graph",)
