"""Derive bounded stage states; content consistency never grants authority."""
from __future__ import annotations

from .case_contracts import CaseEvidence, InputError, StageStatus


_STAGES = (
    ("scope_planning", ("plan", "preflight", "catalog", "plan_manifest"),
     "artifact_present", ("authorization_missing", "plan_not_executable")),
    ("assessment_reported", ("assessment", "assessment_manifest"),
     "artifact_present", ("independent_synthetic_assessment", "producer_not_verified")),
    ("observation_intake", ("handoff_input", "source_mapping", "intake_manifest"),
     "content_consistent", ("metadata_binding_only", "not_human_review")),
    ("analyst_review", ("review_packet", "review_packet_manifest", "overlay_template",
                        "decision_overlay", "reconciled_handoff", "reconciliation_manifest"),
     "human_review_pending", ("empty_overlay_is_not_review", "client_inclusion_pending")),
    ("client_handoff", ("handoff_internal_markdown", "handoff_client_markdown", "handoff_manifest"),
     "delivery_not_authorized", ("prior_phase18_builder_artifacts", "same_input_bytes_only",
                                 "handoff_html_not_read")),
    ("traceability", ("traceability_ledger", "traceability_manifest"),
     "relationship_not_established", ("execution_binding_missing", "scope_fulfillment_not_verified")),
)
BLOCKER_CODES = (
    "authorization_missing", "execution_binding_missing", "producer_not_verified",
    "human_review_pending", "data_handling_pending", "delivery_not_authorized",
    "runtime_acceptance_not_performed",
)


def derive_workflow(evidence: CaseEvidence) -> tuple[StageStatus, ...]:
    if type(evidence) is not CaseEvidence:
        raise InputError("case_invalid_evidence")
    artifacts = {item.role: item for item in evidence.artifacts}
    result = []
    for stage, roles, default, limitations in _STAGES:
        if any(role not in artifacts or artifacts[role].status == "artifact_missing" for role in roles):
            status = "artifact_missing"
        elif any(relation.status == "content_inconsistent" and
                 any(role in relation.source_roles for role in roles)
                 for relation in evidence.relationships):
            status = "content_inconsistent"
        else:
            status = default
        result.append(StageStatus(stage, status, roles, limitations))
    return tuple(result)


def derive_blockers(evidence: CaseEvidence) -> tuple[str, ...]:
    if type(evidence) is not CaseEvidence:
        raise InputError("case_invalid_evidence")
    # The closed demo contracts contain no route to establish real authority,
    # producer identity, human approval or runtime acceptance. A successful
    # byte relation cannot close any of these seven separate requirements.
    return BLOCKER_CODES
