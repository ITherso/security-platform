"""Minimize an owner-validated, permitted upstream projection.

This helper does not determine reuse permission. Its caller must first apply
the complete reference-level decision and use the owning Phase31 getter.
"""
from __future__ import annotations

from .consumer_contracts import (
    PROJECTION_LIMITATIONS, closed, digest_id, fail, identifier,
    validate_projection,
)


_UPSTREAM_PROJECTION_FIELDS = (
    "projection_kind", "current_observation_id", "file_id", "root_id",
    "pinned_commit", "path", "source_file_presence", "current_observed_byte_size",
    "current_observed_sha256", "read_stability", "reference_context_revalidated",
    "compiler_resolution_verified", "module_closure_verified",
    "component_ownership_verified", "resolved_file",
)
_UPSTREAM_COMPARISON_FIELDS = (
    "comparison_id", "file_id", "historical_observation_id", "current_observation_id",
    "candidate_ids", "reference_ids", "comparison_status", "bytes_equal",
    "identity_comparison", "historical_physical_identity", "reason_codes",
    "reference_context_revalidated", "compiler_resolution_verified", "resolved_file",
)


def project_metadata(reference_id: str, candidate_id: str,
                     upstream_projection: dict, comparison: dict) -> dict:
    """Return eleven fields only; never copy a source path or baseline model."""
    digest_id(reference_id, "rust-ref-", "reference_id")
    identifier(candidate_id, "candidate_id")
    projection = closed(upstream_projection, _UPSTREAM_PROJECTION_FIELDS, "upstream_projection_fields")
    comparison = closed(comparison, _UPSTREAM_COMPARISON_FIELDS, "upstream_comparison_fields")
    if (projection["file_id"] != comparison["file_id"]
            or projection["current_observation_id"] != comparison["current_observation_id"]
            or type(comparison["candidate_ids"]) is not list
            or type(comparison["reference_ids"]) is not list
            or candidate_id not in comparison["candidate_ids"]
            or reference_id not in comparison["reference_ids"]):
        fail("upstream_projection_comparison_binding")
    if (any(projection[key] is not False for key in
            ("reference_context_revalidated", "compiler_resolution_verified",
             "module_closure_verified", "component_ownership_verified", "resolved_file"))
            or any(comparison[key] is not False for key in
                   ("reference_context_revalidated", "compiler_resolution_verified", "resolved_file"))
            or comparison["identity_comparison"] != "not_comparable"
            or comparison["historical_physical_identity"] != "not_recorded"):
        fail("upstream_projection_trust_boundary")
    kind = projection["projection_kind"]
    if kind == "fresh_candidate_byte_metadata_only":
        if (comparison["comparison_status"] != "bytes_reobserved_equal"
                or comparison["bytes_equal"] is not True
                or projection["read_stability"] != "stable_bounded_read"):
            fail("upstream_byte_projection_binding")
    elif kind == "fresh_absence_metadata_only":
        if (comparison["comparison_status"] != "absence_reobserved"
                or comparison["bytes_equal"] is not None
                or projection["read_stability"] != "safe_absence_observed"):
            fail("upstream_absence_projection_binding")
    else:
        fail("upstream_projection_kind")
    # Construct the closed output explicitly. Source locator, historical,
    # physical-identity and stability fields are deliberately not transferred.
    result = {
        "reference_id": reference_id,
        "candidate_id": candidate_id,
        "file_id": projection["file_id"],
        "upstream_projection_kind": kind,
        "source_file_presence": projection["source_file_presence"],
        "observed_byte_size": projection["current_observed_byte_size"],
        "observed_sha256": projection["current_observed_sha256"],
        "phase31_current_observation_id": projection["current_observation_id"],
        "phase31_comparison_id": comparison["comparison_id"],
        "upstream_comparison_status": comparison["comparison_status"],
        "interpretation_limitations": list(PROJECTION_LIMITATIONS),
    }
    return validate_projection(result, reference_id)


__all__ = ("project_metadata",)
