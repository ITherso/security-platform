"""Pure closed tabular projection from an immutable owning capsule snapshot."""
from __future__ import annotations

from capsule_contracts import reference_ids
from capsule_adapter import ValidatedCapsule, read_capsule
from disclosure_projection import project_projection, project_reference
from tabular_contracts import (
    CSV_ENCODING, DATASET_SCHEMA, GLOBAL_LIMITATIONS, InputError,
    common, dataset_counts, make_scope, validate_dataset,
)


def build_tabular_dataset(validated_capsule: ValidatedCapsule,
                          selected_reference_ids: list[str]) -> dict:
    """Export existing selected disclosure records; perform no source I/O.

    All requested IDs are checked before any reference/projection is produced.
    The actual archive identity comes from the owning immutable-byte snapshot,
    never a caller's approval flag or a positive source observation label.
    """
    selected_ids = list(reference_ids(selected_reference_ids))
    capsule, identity = read_capsule(validated_capsule)
    indexed = {}
    for row in capsule["results"]:
        reference_id = row["reference_id"]
        if reference_id in indexed:
            raise InputError("tabular_duplicate_source_reference")
        indexed[reference_id] = row
    if any(ref not in indexed for ref in selected_ids):
        raise InputError("tabular_export_reference_not_in_source")

    references, projections = [], []
    for reference_id in selected_ids:
        source_result = indexed[reference_id]
        references.append(project_reference(source_result))
        if source_result["status"] == "provided_limited_metadata":
            projections.extend(project_projection(p, reference_id)
                               for p in source_result["projections"])
        elif source_result["projections"]:
            # Owning source validation already rejects this contradiction.
            # Do not silently convert it into an apparently valid empty row.
            raise InputError("tabular_nonprovided_source_projection_rejected")

    dataset = {
        **common(DATASET_SCHEMA),
        "scope": make_scope(identity["sha256"], selected_ids),
        "source_capsule": {
            "bytes": identity["bytes"],
            "sha256": identity["sha256"],
            "capsule_reference": identity["capsule_reference"],
        },
        "reference_records": references,
        "projection_records": projections,
        "counts": dataset_counts(references, projections),
        "csv_encoding": dict(CSV_ENCODING),
        "limitations": list(GLOBAL_LIMITATIONS),
    }
    return validate_dataset(dataset)


__all__ = ("build_tabular_dataset",)
