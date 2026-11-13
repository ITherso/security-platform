"""Pure capsule creation from owner-validated, immutable Phase32 metadata."""
from __future__ import annotations

from typing import TYPE_CHECKING

from capsule_contracts import (
    CAPSULE_SCHEMA, GLOBAL_LIMITATIONS, InputError, common, result_counts,
    validate_capsule, validate_request,
)
from disclosure_allowlist import project_result

if TYPE_CHECKING:
    from phase32_adapter import ValidatedPhase32Snapshot


def create_capsule(validated_snapshot: ValidatedPhase32Snapshot,
                   request: dict) -> dict:
    """Project only explicitly requested recorded results, never source files.

    No mutable approval marker is accepted. Snapshot reading revalidates its
    exact immutable bytes through the real Phase32 owners. Request bindings and
    every requested ID are checked before constructing any disclosure result.
    """
    from phase32_adapter import read_validated_snapshot

    request = validate_request(request)
    response, _selection, source_bindings = read_validated_snapshot(validated_snapshot)
    for role in ("response", "selection"):
        if (request["source_" + role + "_sha256"]
                != source_bindings["sources"][role]["sha256"]):
            raise InputError("capsule_request_source_digest_mismatch")

    indexed = {}
    for row in response["results"]:
        reference_id = row["reference_id"]
        if reference_id in indexed:
            raise InputError("capsule_duplicate_source_reference")
        indexed[reference_id] = row
    requested_ids = request["requested_reference_ids"]
    if any(reference_id not in indexed for reference_id in requested_ids):
        raise InputError("capsule_unknown_requested_reference")

    results = [project_result(indexed[reference_id]) for reference_id in requested_ids]
    capsule = {
        **common(CAPSULE_SCHEMA, request["capsule_reference"], source_bindings),
        "requested_reference_ids": list(requested_ids),
        "results": results,
        "counts": result_counts(results),
        "inspection_constraints": dict(request["inspection_constraints"]),
        "limitations": list(GLOBAL_LIMITATIONS),
    }
    return validate_capsule(capsule)


__all__ = ("create_capsule",)
