"""Pure exact selected-result correspondence between two valid capsules."""
from __future__ import annotations

from capsule_contracts import FALSE_FLAGS, fixed, validate_capsule
from derivation_contracts import InputError, validate_request
from subset_selection import select_results


def assert_monotonic_disclosure(source: dict, derived: dict, request: dict) -> None:
    """Require a proper subset with unchanged disclosure and metadata.

    This compares already recorded capsule contents. It does not verify the
    original sources, producer identity or the request's ZIP hash from models.
    Actual archive-byte binding belongs to the immutable adapter and builder.
    """
    source = validate_capsule(source)
    derived = validate_capsule(derived)
    request = validate_request(request)
    selected_ids = request["selected_reference_ids"]
    expected_results = select_results(source, selected_ids)
    if request["derivation_reference"] == source["capsule_reference"]:
        raise InputError("derivation_distinct_capsule_reference_required")
    fixed(derived["capsule_reference"], request["derivation_reference"], "derived_reference")
    fixed(derived["requested_reference_ids"], selected_ids, "derived_selected_reference_order")
    # Typed canonical equality covers the entire five-field result, all eleven
    # projection fields, list order, null versus zero and every fixed limit.
    fixed(derived["results"], expected_results, "derived_selected_results_exact")
    for key in ("schema_version", "source_bindings", "demo_label", "demo_only",
                *FALSE_FLAGS, "inspection_constraints", "limitations"):
        fixed(derived[key], source[key], "derived_preserved_source_boundary")
    # Owning validation has already rederived each capsule's separate counts.
    # Omitted reference IDs and their metadata never become comparison output.


__all__ = ("assert_monotonic_disclosure",)
