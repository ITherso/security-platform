"""Pure ALL-OF matching of recorded projections in an owner-validated source."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from cohort_contracts import (
    LIMITATIONS, MAX_QUERY_BYTES, WITNESSES_SCHEMA, InputError,
    cohort_counts, common, fixed, json_bytes, parse_json, query_from_witnesses,
    validate_query, validate_request, validate_witnesses,
)

if TYPE_CHECKING:
    from phase38_adapter import ValidatedCoReferenceSource


def _validated_query(raw_bytes: bytes) -> dict:
    if type(raw_bytes) is not bytes:
        raise InputError("cohort_exact_immutable_query_bytes_required")
    return validate_query(parse_json(raw_bytes, maximum=MAX_QUERY_BYTES))


@dataclass(frozen=True, slots=True)
class ValidatedCohortQuery:
    """Exact query bytes; direct construction checks the closed query wire.

    This constructor does not reopen the recorded Phase38 inputs, establish
    complete source matching, or verify any current physical file condition.
    """

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_query(self.raw_bytes)


def read_cohort_query(snapshot: ValidatedCohortQuery) -> dict:
    if type(snapshot) is not ValidatedCohortQuery:
        raise InputError("cohort_exact_validated_query_required")
    return deepcopy(_validated_query(snapshot.raw_bytes))


def _source_query_and_witnesses(validated_source: ValidatedCoReferenceSource,
                                request: dict) -> tuple[dict, dict]:
    """One source-bound algorithm shared by the query and witness builders."""
    from phase38_adapter import read_co_reference_source

    request = validate_request(request)
    join, _lookup, _receipt, source_artifacts, _old_request = read_co_reference_source(validated_source)
    fixed(request["source_phase38_join_sha256"], source_artifacts[0]["sha256"],
          "cohort_actual_Phase38_join_identity")
    fixed(request["source_phase38_manifest_sha256"], source_artifacts[-1]["sha256"],
          "cohort_actual_Phase38_manifest_identity")
    assertions = request["required_file_assertions"]
    required_ids = [assertion["file_id"] for assertion in assertions]
    if any(file_id not in join["requested_file_ids"] for file_id in required_ids):
        raise InputError("cohort_required_file_outside_recorded_request_scope")

    source_files = {result["file_id"]: result for result in join["file_results"]}
    # This is a direct intersection of ALL required sets. Pair relationships
    # are consulted only later as supporting triples, never transitively.
    visible_sets = [set(source_files[file_id]["visible_reference_ids"])
                    for file_id in required_ids]
    shared_ids = set.intersection(*visible_sets)
    packets = {packet["reference_id"]: packet for packet in join["reference_packets"]}
    source_pair_triples = {
        (binding["reference_id"], binding["candidate_id"], binding["file_id"])
        for pair in join["pair_results"]
        for binding in pair["supporting_projection_bindings"]
    }
    results = []
    for reference_id in sorted(shared_ids):
        if reference_id not in packets:
            raise InputError("cohort_complete_source_reference_packet_missing")
        packet = packets[reference_id]
        if packet["disclosure_status"] != "provided_limited_metadata":
            raise InputError("cohort_nonprovided_reference_rejected")
        supporting_triples, presence_matched = [], True
        for assertion in assertions:
            file_id = assertion["file_id"]
            projections = [projection for projection in packet["projections"]
                           if projection["file_id"] == file_id]
            if not projections:
                raise InputError("cohort_required_source_projection_missing")
            recorded_presence = {projection["source_file_presence"] for projection in projections}
            if len(recorded_presence) != 1:
                raise InputError("cohort_conflicting_recorded_presence_rejected")
            if recorded_presence != {assertion["expected_source_file_presence"]}:
                presence_matched = False
            for projection in projections:
                if projection["reference_id"] != reference_id:
                    raise InputError("cohort_source_reference_projection_mismatch")
                triple = (reference_id, projection["candidate_id"], file_id)
                if triple not in source_pair_triples:
                    raise InputError("cohort_source_pair_support_missing")
                supporting_triples.append(triple)
        if len(set(supporting_triples)) != len(supporting_triples):
            raise InputError("cohort_duplicate_source_support_rejected")
        if not presence_matched:
            continue
        results.append({
            "reference_id": reference_id,
            "disclosure_status": packet["disclosure_status"],
            "matched_file_ids": list(required_ids),
            "supporting_projection_bindings": [
                {"reference_id": ref, "candidate_id": candidate, "file_id": file_id}
                for ref, candidate, file_id in sorted(supporting_triples)
            ],
            # The assertion set limits the support, not the disclosed packet.
            "projections": deepcopy(packet["projections"]),
        })

    witnesses = validate_witnesses({
        **common(WITNESSES_SCHEMA),
        "source_phase38_join_sha256": source_artifacts[0]["sha256"],
        "source_phase38_manifest_sha256": source_artifacts[-1]["sha256"],
        "request": request,
        "results": results,
        "counts": cohort_counts(request, results),
        "limitations": list(LIMITATIONS),
    })
    return query_from_witnesses(witnesses), witnesses


def build_cohort_query(validated_source: ValidatedCoReferenceSource,
                        request: dict) -> ValidatedCohortQuery:
    """Evaluate recorded ALL-OF/presence conditions without filesystem I/O."""
    query, _witnesses = _source_query_and_witnesses(validated_source, request)
    return ValidatedCohortQuery(json_bytes(query, maximum=MAX_QUERY_BYTES))


__all__ = ("ValidatedCohortQuery", "read_cohort_query", "build_cohort_query")
