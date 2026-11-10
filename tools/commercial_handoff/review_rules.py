"""Pure, demo-only selection rules for separate internal and client models.

These rules inspect supplied metadata, not human identities, source bytes or
technical findings. Meeting the selection conditions never authorizes release.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .schema import HandoffInput, Observation, ReviewDecision, SourceArtifact


@dataclass(frozen=True, slots=True)
class ObservationReview:
    observation: Observation
    source_or_none: SourceArtifact | None
    decision_or_none: ReviewDecision | None
    blockers: tuple[str, ...]
    selected_for_draft: bool


@dataclass(frozen=True, slots=True)
class InternalSummary:
    document: HandoffInput
    observation_reviews: tuple[ObservationReview, ...]
    delivery_blockers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClientItem:
    observation_id: str
    safe_summary: str
    source_disposition: str
    review_status: str
    source_artifact_id: str
    observation_ref: str
    source_json_pointer: str


@dataclass(frozen=True, slots=True)
class ClientSource:
    artifact_id: str
    contract: str
    sha256: str
    byte_length: int
    completion_status: str


@dataclass(frozen=True, slots=True)
class ClientDraft:
    case_id: str
    scope_summary: str
    selected_items: tuple[ClientItem, ...]
    source_references: tuple[ClientSource, ...]
    incomplete_review: bool


_ASSESSMENT_CONTRACT = "venom-rendered-assessment/v1"
_ELIGIBLE_REVIEW_STATUSES = frozenset(("informational_only", "reviewed_for_delivery"))
_MISSING_REVIEWER_SENTINELS = frozenset((
    "not_provided", "not_verified", "pending_decision", "not_assigned",
))
_ALWAYS_BLOCKED = (
    "demo_only_not_for_delivery",
    "human_review_not_verified",
    "release_not_authorized",
)


def _source_identity(
    observation: Observation, source: SourceArtifact | None,
) -> tuple[str, str, str] | None:
    """Bind duplicate detection to declared bytes, including artifact aliases.

    The hash is supplied metadata: this function neither opens a source file nor
    verifies its bytes. Incomplete references are already selection blockers.
    """
    if (source is None or observation.observation_ref is None
            or observation.source_json_pointer is None):
        return None
    return (source.sha256, observation.observation_ref, observation.source_json_pointer)


def _reviewer_missing(value: str | None) -> bool:
    return value is None or not value.strip() or value.strip().casefold() in _MISSING_REVIEWER_SENTINELS


def build_models(document: HandoffInput) -> tuple[InternalSummary, ClientDraft]:
    """Build models from the validated, immutable input without I/O or effects.

    ``ClientDraft.incomplete_review`` always remains true: actual human review
    cannot be verified by this tool, even when every declared row qualifies for
    the draft. It is independent of source assessment completion and selection.
    Imported ``confirmed`` labels are retained as labels, never re-evaluated.
    """
    sources = {source.artifact_id: source for source in document.source_artifacts}
    decisions = {decision.decision_id: decision for decision in document.review_decisions}
    observation_ids = {observation.observation_id for observation in document.observations}

    identities = tuple(
        _source_identity(observation, sources.get(observation.source_artifact))
        for observation in document.observations
    )
    identity_counts = Counter(identity for identity in identities if identity is not None)
    observation_reviews: list[ObservationReview] = []
    client_items: list[ClientItem] = []
    selected_source_ids: set[str] = set()
    bound_decision_ids: set[str] = set()

    for observation, identity in zip(document.observations, identities):
        source = sources.get(observation.source_artifact)
        decision = decisions.get(observation.decision_ref)
        blockers: list[str] = []

        if observation.source_artifact is None:
            blockers.append("source_artifact_missing")
        elif source is None:
            blockers.append("source_artifact_unknown")
        else:
            if source.contract != _ASSESSMENT_CONTRACT:
                blockers.append("source_contract_not_assessment")
            if source.completion_status != "complete":
                blockers.append("source_assessment_not_complete")

        if observation.observation_ref is None:
            blockers.append("observation_reference_missing")
        if observation.source_json_pointer is None:
            blockers.append("source_json_pointer_missing")
        if identity is not None and identity_counts[identity] > 1:
            blockers.append("duplicate_source_observation")

        if observation.decision_ref is None:
            blockers.append("decision_reference_missing")
        elif decision is None:
            blockers.append("decision_reference_unknown")
        else:
            if decision.observation_id != observation.observation_id:
                blockers.append("decision_observation_mismatch")
            else:
                bound_decision_ids.add(decision.decision_id)
            if decision.review_status != observation.review_status:
                blockers.append("decision_review_status_mismatch")
            if decision.client_inclusion != observation.client_inclusion:
                blockers.append("decision_client_inclusion_mismatch")
            if _reviewer_missing(decision.reviewer_ref):
                blockers.append("reviewer_reference_missing")
            if decision.reviewed_at is None:
                blockers.append("review_timestamp_missing")

        if observation.scope_status != "in_scope":
            blockers.append("scope_not_in_scope")
        if observation.client_inclusion != "include_with_limits":
            blockers.append("client_inclusion_not_selected")
        if observation.review_status not in _ELIGIBLE_REVIEW_STATUSES:
            blockers.append("review_status_not_eligible")
        if observation.safe_summary is None or not observation.safe_summary.strip():
            blockers.append("safe_summary_missing")

        # Required values are narrowed again at the explicit client boundary;
        # never serialize the internal observation or its decision wholesale.
        selected = (not blockers and source is not None
            and observation.safe_summary is not None
            and observation.observation_ref is not None
            and observation.source_json_pointer is not None)
        if selected:
            client_items.append(ClientItem(
                observation_id=observation.observation_id,
                safe_summary=observation.safe_summary,
                source_disposition=observation.source_disposition,
                review_status=observation.review_status,
                source_artifact_id=source.artifact_id,
                observation_ref=observation.observation_ref,
                source_json_pointer=observation.source_json_pointer,
            ))
            selected_source_ids.add(source.artifact_id)

        observation_reviews.append(ObservationReview(
            observation=observation,
            source_or_none=source,
            decision_or_none=decision,
            blockers=tuple(blockers),
            selected_for_draft=selected,
        ))

    delivery_blockers = list(_ALWAYS_BLOCKED)
    # The v1 schema accepts no verified authorization state. Constraints are
    # internal declarations, not proof that a data/operational gate is cleared.
    delivery_blockers.append("authorization_not_verified")
    if document.delivery_constraints:
        delivery_blockers.append("delivery_constraints_unresolved")
    if any(review.blockers for review in observation_reviews):
        delivery_blockers.append("observation_selection_blocked")
    if any(decision.observation_id not in observation_ids
            for decision in document.review_decisions):
        delivery_blockers.append("orphan_review_decision")
    if any(decision.decision_id not in bound_decision_ids
            for decision in document.review_decisions):
        delivery_blockers.append("unused_review_decision")

    client_sources = tuple(
        ClientSource(
            artifact_id=source.artifact_id,
            contract=source.contract,
            sha256=source.sha256,
            byte_length=source.byte_length,
            completion_status=source.completion_status,
        )
        for source in document.source_artifacts
        if source.artifact_id in selected_source_ids
    )
    return (
        InternalSummary(
            document=document,
            observation_reviews=tuple(observation_reviews),
            delivery_blockers=tuple(delivery_blockers),
        ),
        ClientDraft(
            case_id=document.case_id,
            scope_summary=document.scope_summary,
            selected_items=tuple(client_items),
            source_references=client_sources,
            incomplete_review=True,
        ),
    )
