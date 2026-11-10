"""Explicit metadata-only provenance mapping; no file, runtime or network I/O."""
from __future__ import annotations

from typing import TYPE_CHECKING

from commercial_handoff.schema import InputError

from . import ADAPTER_VERSION, INTAKE_CONTRACT
from .assessment_reader import (
    AssessmentSource,
    NativeItem,
    MAX_ASSESSMENT_ITEMS,
    SUPPORTED_CAPABILITIES,
    SUPPORTED_CATEGORIES,
)

if TYPE_CHECKING:
    from .provenance import ManifestCheck


def _mapped_items(assessment: AssessmentSource) -> tuple[NativeItem, ...]:
    """Require the reader's closed DTO and unambiguous source order.

    Native wire validation belongs to read_assessment. These boundary checks do
    not authenticate a DTO or re-evaluate the source's security claims.
    """
    if type(assessment) is not AssessmentSource or type(assessment.items) is not tuple:
        raise InputError("invalid_assessment_model")
    if (
        assessment.schema != "venom-rendered-assessment/v1"
        or assessment.source_schema != "venom-assessment-run/v1"
        or assessment.run_schema != "venom-run/v1"
        or assessment.profile_schema != "venom.scan-profile/v1"
        or assessment.profile != "web-review"
        or assessment.status != "complete"
    ):
        raise InputError("unsupported_assessment_model")
    if len(assessment.items) > MAX_ASSESSMENT_ITEMS:
        raise InputError("source_observation_limit")
    for index, item in enumerate(assessment.items):
        if type(item) is not NativeItem or type(item.index) is not int or item.index != index:
            raise InputError("invalid_source_item_order")
        if item.capability_id not in SUPPORTED_CAPABILITIES:
            raise InputError("unsupported_source_capability")
        if item.category not in SUPPORTED_CATEGORIES:
            raise InputError("unsupported_source_category")
    return assessment.items


def _manifest_mapping(check: ManifestCheck) -> dict:
    # This closed result has already been built by the explicit manifest reader.
    # Do not serialize a dataclass or copy any producer/free-form manifest data.
    if (type(check.provided) is not bool or check.html_payload_read is not False
            or check.producer_verified is not False or check.full_bundle_verified is not False):
        raise InputError("invalid_manifest_check")
    if check.provided:
        if (check.status != "partial_json_entry_match" or check.sha256 is None
                or check.byte_length is None or check.json_entry_matches is not True
                or check.summary_matches is not True):
            raise InputError("invalid_manifest_check")
    elif (check.status != "not_provided" or check.sha256 is not None
            or check.byte_length is not None or check.json_entry_matches is not None
            or check.summary_matches is not None):
        raise InputError("invalid_manifest_check")
    return {
        "provided": check.provided,
        "sha256": check.sha256,
        "byte_length": check.byte_length,
        "status": check.status,
        "json_entry_matches": check.json_entry_matches,
        "summary_matches": check.summary_matches,
        "html_payload_read": False,
        "full_bundle_verified": False,
        "producer_verified": False,
    }


def build_source_mapping(assessment: AssessmentSource, manifest_check: ManifestCheck) -> dict:
    """Return a closed mapping of all accepted items without merging or omission.

    A mapping identifies declared source metadata, not reviewed findings. The
    source identity is the exact assessment byte SHA, pointer and fingerprint.
    Omitted class names contain no original values or referenced locations.
    """
    items = _mapped_items(assessment)
    observations = []
    for item in items:
        observations.append({
            "handoff_observation_id": f"OBS-{item.index + 1:02d}",
            "source_assessment_sha256": assessment.sha256,
            "source_json_pointer": f"/items/{item.index}",
            "fingerprint": item.fingerprint,
            "capability_id": item.capability_id,
            "disposition": item.disposition,
            "claim_basis": item.claim_basis,
            "category": item.category,
            "subject_reference": item.subject_reference,
            "evidence_count": item.evidence_count,
            "evidence_references": list(item.evidence_references),
            "control_evidence_references": list(item.control_evidence_references),
            "candidate_evidence_references": list(item.candidate_evidence_references),
            "mapping_status": "mapped_metadata_only",
        })
    return {
        "schema_version": INTAKE_CONTRACT,
        "adapter_version": ADAPTER_VERSION,
        "mapping_status": "mapped_metadata_only",
        "source_assessment": {
            "sha256": assessment.sha256,
            "byte_length": assessment.byte_length,
            "schema": assessment.schema,
            "source_schema": assessment.source_schema,
            "run_schema": assessment.run_schema,
            "profile_schema": assessment.profile_schema,
            "profile": assessment.profile,
            "status": assessment.status,
            "subject_count": assessment.subject_count,
            "item_count": assessment.item_count,
        },
        "manifest_check": _manifest_mapping(manifest_check),
        "source_observation_count": len(items),
        "mapped_observation_count": len(observations),
        "automatic_merge_performed": False,
        "fingerprint_reuse_detected": len({item.fingerprint for item in items}) != len(items),
        "native_import_validation_performed": False,
        "fingerprint_limit": "Reported fingerprints are not source authentication. Repeated labels remain separate by exact source byte SHA256 and JSON pointer; native importer uniqueness acceptance is not established.",
        "observations": observations,
        "omitted_field_classes": [
            "item_title",
            "item_redacted_summary",
            "item_remediation",
            "item_cwe",
            "item_severity",
            "item_confidence_ppm",
            "item_verifier_linkage",
        ],
        "demo_only": True,
        "human_review_verified": False,
        "producer_verified": False,
        "release_authorized": False,
    }
