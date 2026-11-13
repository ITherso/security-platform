"""Explicit reference and projection DTOs from owning closed capsule records."""
from __future__ import annotations

from capsule_contracts import validate_projection, validate_result


def project_reference(result: dict) -> dict:
    """Represent a recorded disclosure status without positive file metadata."""
    row = validate_result(result)
    return {
        "reference_id": row["reference_id"],
        "disclosure_status": row["status"],
        "projection_count": len(row["projections"]),
        "interpretation_limitations": list(row["limitation_codes"]),
    }


def project_projection(projection: dict, reference_id: str) -> dict:
    """Copy exactly the existing eleven fields, preserving values and nulls."""
    row = validate_projection(projection, reference_id)
    return {
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
    }


__all__ = ("project_reference", "project_projection")
