"""Pure all-or-nothing queries over an exact immutable typed inbox."""
from __future__ import annotations

from copy import deepcopy

from inbox_contracts import (
    CSV_HEADERS, LIMITATIONS, PROJECTION_FIELDS, QUERY_SCHEMA, QUERY_SCOPE,
    InputError, common, dataset_counts, reference_ids, validate_query,
    validate_request,
)
from inbox_snapshot import ValidatedInbox, read_typed_inbox


def query_reference_metadata(validated_inbox: ValidatedInbox,
                             requested_ids: list[str]) -> list[dict]:
    """Return complete selected reference records, never partial projections.

    ValidatedInbox represents closed new-inbox bytes. Reading it validates
    internal typed relationships; this query does not reopen source CSVs or
    establish the truth, freshness or producer of their recorded metadata.
    """
    ids = list(reference_ids(requested_ids))
    inbox = read_typed_inbox(validated_inbox)
    references = {record["reference_id"]: record for record in inbox["reference_records"]}
    if any(reference not in references for reference in ids):
        raise InputError("typed_inbox_query_unknown_reference")
    grouped = {reference: [] for reference in ids}
    for projection in inbox["projection_records"]:
        reference = projection["reference_id"]
        if reference in grouped:
            grouped[reference].append(projection)

    results = []
    for reference in ids:
        record, projections = references[reference], grouped[reference]
        if len(projections) != record["projection_count"]:
            raise InputError("typed_inbox_query_projection_count_mismatch")
        if record["disclosure_status"] != "provided_limited_metadata" and projections:
            raise InputError("typed_inbox_query_nonprovided_projection_rejected")
        result = {key: deepcopy(record[key]) for key in CSV_HEADERS["reference"]}
        result["projections"] = [
            {key: deepcopy(projection[key]) for key in PROJECTION_FIELDS}
            for projection in projections
        ]
        results.append(result)
    return results


def build_reference_query(validated_inbox: ValidatedInbox, request: dict) -> dict:
    """Bind an explicit demo request to the recorded source-manifest identity."""
    request = validate_request(request)
    inbox = read_typed_inbox(validated_inbox)
    source_manifest = inbox["source_artifacts"][-1]
    if (source_manifest["name"] != "manifest.json"
            or source_manifest["sha256"] != request["source_manifest_sha256"]):
        raise InputError("typed_inbox_query_source_manifest_mismatch")
    # All request IDs are validated before the selection function constructs
    # any result, so an unknown ID cannot produce a partially successful query.
    results = query_reference_metadata(validated_inbox, request["requested_reference_ids"])
    references = [{key: result[key] for key in CSV_HEADERS["reference"]} for result in results]
    projections = [projection for result in results for projection in result["projections"]]
    query = {
        **common(QUERY_SCHEMA),
        "request": request,
        "source_manifest": {
            "name": source_manifest["name"], "bytes": source_manifest["bytes"],
            "sha256": source_manifest["sha256"],
        },
        "results": results,
        "counts": dataset_counts(references, projections),
        "query_scope": QUERY_SCOPE,
        "limitations": list(LIMITATIONS),
    }
    return validate_query(query)


__all__ = ("query_reference_metadata", "build_reference_query")
