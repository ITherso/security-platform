"""Explicit metadata-only projection for a standalone offline desk document."""
from __future__ import annotations

from commercial_review import DEMO_LABEL
from commercial_review.review_contracts import check_json_budget

from . import VIEW_CONTRACT
from .desk_contracts import (
    DeskSources, finalize_draft, load_desk_sources, render_overlay, validate_desk_sources,
)


__all__ = ("build_projection", "load_desk_sources", "finalize_draft", "render_overlay")


def build_projection(sources: DeskSources) -> dict:
    """Use the existing packet validators, then copy only the view allowlist.

    No source model, manifest, template, free scope/provenance or evidence text
    is serialized wholesale. Category is absent because Phase18 supplies none.
    """
    packet = validate_desk_sources(sources)
    result = {
        "schema_version": VIEW_CONTRACT,
        "review_packet_digest": sources.packet_file.sha256,
        "source_assessment_digest": packet.source_assessment.sha256,
        "demo_label": DEMO_LABEL,
        "source": {
            "profile": packet.source_assessment.profile,
            "status": packet.source_assessment.status,
            "item_count": packet.source_assessment.item_count,
            "manifest_status": packet.manifest_limitation.status,
            "source_verification": packet.source_verification,
        },
        "observations": [{
            "observation_id": item.observation_id,
            "observation_key": item.observation_key,
            "source_json_pointer": item.source_json_pointer,
            "fingerprint": item.fingerprint,
            "capability_id": item.capability_id,
            "source_disposition": item.source_disposition,
            "review_status": item.review_status,
            "scope_status": item.scope_status,
            "client_inclusion": item.client_inclusion,
        } for item in packet.observations],
        "review_requirements": list(packet.review_requirements),
        "delivery_blockers": list(packet.delivery_blockers),
        "demo_only": True,
        "human_review_verified": False,
        "producer_verified": False,
        "release_authorized": False,
    }
    check_json_budget(result)
    return result
