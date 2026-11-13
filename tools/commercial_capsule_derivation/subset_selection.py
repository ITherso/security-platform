"""Select complete closed reference results without changing their contents."""
from __future__ import annotations

from capsule_contracts import reference_ids, validate_capsule, validate_result
from derivation_contracts import InputError


def select_results(source: dict, selected_ids: list[str]) -> list[dict]:
    """Return independently copied whole results in explicit request order."""
    source = validate_capsule(source)
    selected_ids = list(reference_ids(selected_ids))
    indexed = {row["reference_id"]: row for row in source["results"]}
    if len(selected_ids) >= len(source["requested_reference_ids"]):
        raise InputError("derivation_proper_reference_subset_required")
    if any(ref not in indexed for ref in selected_ids):
        raise InputError("derivation_selected_reference_not_in_source")
    # The owning validator closes all five result fields and all eleven
    # projection fields, then returns a deep copy of the selected result only.
    return [validate_result(indexed[ref]) for ref in selected_ids]


__all__ = ("select_results",)
