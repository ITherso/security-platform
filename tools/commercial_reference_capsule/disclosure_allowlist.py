"""Construct the capsule disclosure DTO from explicit permitted fields only."""
from __future__ import annotations

from capsule_contracts import InputError, validate_result


def project_result(result: dict) -> dict:
    """Preserve a recorded whole-reference decision without adding authority.

    Full Phase32 ownership validation belongs to the assembly adapter. This
    function validates the closed transferable result shape and explicitly
    copies its fields; it does not recompute the upstream guard.
    """
    source = validate_result(result)
    if (source["status"] != "provided_limited_metadata"
            and source["projections"]):
        raise InputError("capsule_nonprovided_projection_rejected")

    projections = []
    for row in source["projections"]:
        projections.append({
            "reference_id": row["reference_id"],
            "candidate_id": row["candidate_id"],
            "file_id": row["file_id"],
            "upstream_projection_kind": row["upstream_projection_kind"],
            "source_file_presence": row["source_file_presence"],
            "observed_byte_size": row["observed_byte_size"],
            "observed_sha256": row["observed_sha256"],
            "phase31_current_observation_id": row["phase31_current_observation_id"],
            "phase31_comparison_id": row["phase31_comparison_id"],
            "upstream_comparison_status": row["upstream_comparison_status"],
            "interpretation_limitations": list(row["interpretation_limitations"]),
        })
    projected = {
        "reference_id": source["reference_id"],
        "status": source["status"],
        "upstream_reference_decision": source["upstream_reference_decision"],
        "projections": projections,
        "limitation_codes": list(source["limitation_codes"]),
    }
    return validate_result(projected)


__all__ = ("project_result",)
