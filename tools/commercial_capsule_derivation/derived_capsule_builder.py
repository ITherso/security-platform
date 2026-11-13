"""Pure Phase33-format subset construction from an immutable capsule."""
from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from capsule_contracts import CAPSULE_SCHEMA, common, result_counts, validate_capsule
from derivation_contracts import InputError, validate_request
from disclosure_integrity import assert_monotonic_disclosure
from subset_selection import select_results

if TYPE_CHECKING:
    from phase33_adapter import ValidatedSourceCapsule


def derive_reference_subset(validated_source_capsule: ValidatedSourceCapsule,
                            request: dict) -> dict:
    """Preserve selected whole results; update only identity and subset counts."""
    from phase33_adapter import read_validated_source

    request = validate_request(request)
    source, identity = read_validated_source(validated_source_capsule)
    if request["source_capsule_sha256"] != identity["sha256"]:
        raise InputError("derivation_source_capsule_digest_mismatch")
    results = select_results(source, request["selected_reference_ids"])
    derived = {
        **common(CAPSULE_SCHEMA, request["derivation_reference"], source["source_bindings"]),
        "requested_reference_ids": list(request["selected_reference_ids"]),
        "results": results,
        "counts": result_counts(results),
        "inspection_constraints": deepcopy(source["inspection_constraints"]),
        "limitations": list(source["limitations"]),
    }
    derived = validate_capsule(derived)
    assert_monotonic_disclosure(source, derived, request)
    return derived


__all__ = ("derive_reference_subset",)
