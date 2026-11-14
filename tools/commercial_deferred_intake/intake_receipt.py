"""Actual five-source identities and four distinct historical count scopes."""
from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from intake_contracts import RECEIPT_SCHEMA, LIMITATIONS, common, fixed, validate_receipt
from task_bound_intake import (
    ValidatedDeferredIntake, build_deferred_intake, read_deferred_intake,
)

if TYPE_CHECKING:
    from phase41_adapter import ValidatedPhase41Source


def make_source_receipt(validated_source: ValidatedPhase41Source,
                         validated_intake: ValidatedDeferredIntake) -> dict:
    """Rebind the whole register to its actual immutable source group."""
    from phase41_adapter import read_source

    intake = read_deferred_intake(validated_intake)
    expected = read_deferred_intake(build_deferred_intake(validated_source, intake["request"]))
    fixed(intake, expected, "deferred_intake_receipt_actual_source_correspondence")
    slots, template, receipt, artifacts = read_source(validated_source)
    return validate_receipt({
        **common(RECEIPT_SCHEMA),
        "source_artifacts": [dict(item) for item in artifacts],
        "source_phase41_slots_sha256": artifacts[0]["sha256"],
        "source_phase41_manifest_sha256": artifacts[-1]["sha256"],
        "source_schema_versions": {item["name"]: item["schema_version"] for item in artifacts},
        "source_counts": {
            "slots_counts": dict(slots["counts"]),
            "template_counts": dict(template["counts"]),
            "phase40_counts": deepcopy(receipt["source_counts"]),
        },
        "content_scope": "five_Phase41_artifact_internal_correspondence_only",
        "limitations": list(LIMITATIONS),
    })


__all__ = ("make_source_receipt",)
