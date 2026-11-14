"""Pure pairwise joins over an actually validated Phase37 source group."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from itertools import combinations
from typing import TYPE_CHECKING

from co_reference_contracts import (
    JOIN_SCHEMA, LIMITATIONS, MAX_JOIN_BYTES, InputError, common,
    compute_pair_results, fixed, join_counts, json_bytes, parse_json,
    validate_file_ids, validate_join,
)

if TYPE_CHECKING:
    from phase37_adapter import ValidatedPhase37Source


def _validated_join(raw_bytes: bytes) -> dict:
    if type(raw_bytes) is not bytes:
        raise InputError("co_reference_exact_immutable_join_bytes_required")
    return validate_join(parse_json(raw_bytes, maximum=MAX_JOIN_BYTES))


@dataclass(frozen=True, slots=True)
class ValidatedCoReferenceJoin:
    """Closed join bytes; direct construction checks internal wire integrity.

    The constructor does not reopen the recorded Phase37 inputs or establish
    original-source, producer, physical-file or import-history verification.
    """

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_join(self.raw_bytes)


def read_co_reference_join(snapshot: ValidatedCoReferenceJoin) -> dict:
    if type(snapshot) is not ValidatedCoReferenceJoin:
        raise InputError("co_reference_exact_validated_join_required")
    return deepcopy(_validated_join(snapshot.raw_bytes))


def build_co_reference_join(validated_index: ValidatedPhase37Source,
                            requested_file_ids: list[str]) -> ValidatedCoReferenceJoin:
    """Join recorded file sets only after the five-file owner checks succeed."""
    from phase37_adapter import read_source
    from index_contracts import MAX_INDEX_BYTES as SOURCE_MAX_INDEX_BYTES
    from index_contracts import REFERENCE_PACKET_FIELDS
    from index_contracts import json_bytes as source_json_bytes
    from disclosed_file_index import ValidatedFileIndex
    from reverse_lookup import lookup_disclosed_files

    requested_ids = validate_file_ids(requested_file_ids)
    index, source_artifacts = read_source(validated_index)
    owner_snapshot = ValidatedFileIndex(source_json_bytes(index, maximum=SOURCE_MAX_INDEX_BYTES))
    owner_lookup = lookup_disclosed_files(owner_snapshot, requested_ids)
    file_results = [
        {"file_id": result["file_id"], "status": result["status"],
         "visible_reference_ids": list(result["reference_ids"])}
        for result in owner_lookup["file_results"]
    ]
    references_by_file = {result["file_id"]: set(result["visible_reference_ids"])
                          for result in file_results}
    shared_reference_ids = set()
    for left, right in combinations(sorted(requested_ids), 2):
        shared_reference_ids.update(references_by_file[left] & references_by_file[right])
    reference_packets = [
        {key: deepcopy(result[key]) for key in REFERENCE_PACKET_FIELDS}
        for result in owner_lookup["reference_results"]
        if result["reference_id"] in shared_reference_ids
    ]
    fixed([packet["reference_id"] for packet in reference_packets],
          sorted(shared_reference_ids), "co_reference_complete_shared_reference_union")
    pair_results = compute_pair_results(file_results, reference_packets)

    # Independently bind every reported pair triple to the actual validated
    # index's file records, rather than treating an intersection as proof.
    source_files = {record["file_id"]: record for record in index["file_records"]}
    for pair in pair_results:
        expected_bindings = []
        for file_id in (pair["left_file_id"], pair["right_file_id"]):
            for binding in source_files.get(file_id, {}).get("projection_bindings", []):
                if binding["reference_id"] in pair["shared_reference_ids"]:
                    expected_bindings.append(deepcopy(binding))
        expected_bindings.sort(key=lambda binding: (
            binding["reference_id"], binding["candidate_id"], binding["file_id"]))
        for reference_id in pair["shared_reference_ids"]:
            for file_id in (pair["left_file_id"], pair["right_file_id"]):
                if not any(binding["reference_id"] == reference_id
                           and binding["file_id"] == file_id for binding in expected_bindings):
                    raise InputError("co_reference_actual_source_pair_binding_missing")
        fixed(pair["supporting_projection_bindings"], expected_bindings,
              "co_reference_actual_source_pair_bindings")

    join = {
        **common(JOIN_SCHEMA),
        "source_index_sha256": source_artifacts[0]["sha256"],
        "source_manifest_sha256": source_artifacts[-1]["sha256"],
        "source_schema_version": index["schema_version"],
        "source_artifacts": [dict(item) for item in source_artifacts],
        "source_counts": dict(index["counts"]),
        "requested_file_ids": list(requested_ids),
        "file_results": file_results,
        "pair_results": pair_results,
        "reference_packets": reference_packets,
        "counts": join_counts(file_results, pair_results, reference_packets),
        "limitations": list(LIMITATIONS),
    }
    join = validate_join(join)
    return ValidatedCoReferenceJoin(json_bytes(join, maximum=MAX_JOIN_BYTES))


__all__ = ("ValidatedCoReferenceJoin", "read_co_reference_join", "build_co_reference_join")
