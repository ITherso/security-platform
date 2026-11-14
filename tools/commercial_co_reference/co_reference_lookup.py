"""Return complete permitted packets for source-bound shared references."""
from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from co_reference_contracts import (
    LIMITATIONS, LOOKUP_SCHEMA, common, fixed, lookup_counts, lookup_from_join,
    validate_lookup,
)
from co_reference_join import (
    ValidatedCoReferenceJoin, build_co_reference_join, read_co_reference_join,
)

if TYPE_CHECKING:
    from phase37_adapter import ValidatedPhase37Source


def build_co_reference_lookup(validated_index: ValidatedPhase37Source,
                              validated_join: ValidatedCoReferenceJoin) -> dict:
    """Rebind the join to the actual immutable source group before disclosure."""
    from phase37_adapter import read_source
    from index_contracts import MAX_INDEX_BYTES as SOURCE_MAX_INDEX_BYTES
    from index_contracts import json_bytes as source_json_bytes
    from disclosed_file_index import ValidatedFileIndex
    from reverse_lookup import lookup_disclosed_files

    join = read_co_reference_join(validated_join)
    expected_join = read_co_reference_join(
        build_co_reference_join(validated_index, join["requested_file_ids"]))
    fixed(join, expected_join, "co_reference_lookup_actual_source_join")
    index, _source_artifacts = read_source(validated_index)
    owner_snapshot = ValidatedFileIndex(source_json_bytes(index, maximum=SOURCE_MAX_INDEX_BYTES))
    owner_lookup = lookup_disclosed_files(owner_snapshot, join["requested_file_ids"])
    shared_reference_ids = {reference_id for pair in join["pair_results"]
                            for reference_id in pair["shared_reference_ids"]}
    results = [
        {"reference_id": result["reference_id"],
         "disclosure_status": result["disclosure_status"],
         "matched_file_ids": list(result["matched_file_ids"]),
         "projections": deepcopy(result["projections"])}
        for result in owner_lookup["reference_results"]
        if result["reference_id"] in shared_reference_ids
    ]
    lookup = {
        **common(LOOKUP_SCHEMA),
        "source_index_sha256": join["source_index_sha256"],
        "source_manifest_sha256": join["source_manifest_sha256"],
        "requested_file_ids": list(join["requested_file_ids"]),
        "results": results,
        "counts": lookup_counts(results),
        "limitations": list(LIMITATIONS),
    }
    fixed(lookup, lookup_from_join(join), "co_reference_lookup_complete_shared_packets")
    return validate_lookup(lookup)


__all__ = ("build_co_reference_lookup",)
