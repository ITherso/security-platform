"""Pure exact binding of declared decisions to a validated review packet."""
from __future__ import annotations

from dataclasses import dataclass

from commercial_handoff.input_loader import LoadedInput

from .decision_overlay import (
    AnalystDecision, DecisionOverlay, overlay_to_dict, validate_overlay,
)
from .packet_builder import validate_original_handoff
from .review_contracts import (
    PacketObservation, ReviewError, ReviewPacket, digest, packet_to_dict,
    validate_packet,
)


@dataclass(frozen=True, slots=True)
class BoundDecision:
    decision: AnalystDecision
    observation: PacketObservation


def bind_decisions(
    packet: ReviewPacket,
    original: LoadedInput,
    overlay: DecisionOverlay,
    *,
    packet_digest: str,
) -> tuple[BoundDecision, ...]:
    """Match actual file identity and every immutable observation field.

    The CLI must supply packet_digest from its captured packet bytes, after
    checking the explicit packet manifest. This function performs no reads or
    signature, producer, reviewer, authority or security-claim verification.
    """
    if type(packet) is not ReviewPacket or type(original) is not LoadedInput:
        raise ReviewError("invalid_review_binding_model")
    # Revalidate frozen instances as well: construction is not wire validation.
    packet = validate_packet(packet_to_dict(packet))
    overlay = validate_overlay(overlay_to_dict(overlay))
    expected_packet_digest = digest(packet_digest)
    if overlay.review_packet_digest != expected_packet_digest:
        raise ReviewError("overlay_packet_digest_mismatch")
    if overlay.source_assessment_digest != packet.source_assessment.sha256:
        raise ReviewError("overlay_source_digest_mismatch")
    # Also checks unchanged original byte identity and a fresh Phase17 baseline;
    # pre-existing decisions/narrative/status changes are conflicts, not merged.
    validate_original_handoff(packet, original)
    observations = {row.observation_id: row for row in packet.observations}
    result = []
    for decision in overlay.decisions:
        observation = observations.get(decision.observation_id)
        if observation is None:
            raise ReviewError("unknown_decision_observation")
        claimed = (
            decision.observation_key, decision.source_assessment_sha256,
            decision.source_json_pointer, decision.fingerprint,
            decision.capability_id, decision.source_disposition,
        )
        actual = (
            observation.observation_key, observation.source_assessment_sha256,
            observation.source_json_pointer, observation.fingerprint,
            observation.capability_id, observation.source_disposition,
        )
        if claimed != actual:
            raise ReviewError("decision_source_binding_mismatch")
        result.append(BoundDecision(decision, observation))
    return tuple(result)
