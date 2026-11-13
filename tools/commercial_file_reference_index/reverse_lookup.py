"""File hits to complete permitted reference packets, with no source I/O."""
from __future__ import annotations

from copy import deepcopy

from index_contracts import (
    LIMITATIONS, LOOKUP_SCHEMA, InputError, common, lookup_counts,
    validate_file_ids, validate_lookup, validate_request,
)
from disclosed_file_index import ValidatedFileIndex, read_disclosed_file_index


def lookup_disclosed_files(validated_index: ValidatedFileIndex,
                           requested_file_ids: list[str]) -> dict:
    """Return only visible relationships and whole matching references.

    A syntactically valid File ID outside this index gets the same answer
    whether it is unknown, undisclosed or outside the recorded input scope.
    No physical file, blocked source record or alternative data is consulted.
    """
    requested_ids = list(validate_file_ids(requested_file_ids))
    index = read_disclosed_file_index(validated_index)
    files = {record["file_id"]: record for record in index["file_records"]}
    references = {record["reference_id"]: record for record in index["disclosed_references"]}
    file_results, matched_references = [], set()
    for file_id in requested_ids:
        if file_id in files:
            reference_ids = list(files[file_id]["reference_ids"])
            matched_references.update(reference_ids)
            file_results.append({"file_id": file_id, "status": "matched",
                                 "reference_ids": reference_ids})
        else:
            file_results.append({"file_id": file_id, "status": "not_in_disclosed_index",
                                 "reference_ids": []})

    reference_results = []
    for reference_id in sorted(matched_references):
        if reference_id not in references:
            raise InputError("disclosed_file_lookup_reference_binding_rejected")
        # The index validator closes this entire five-field permitted packet.
        # Copy it whole rather than filtering its projections by requested file.
        reference = deepcopy(references[reference_id])
        if reference["disclosure_status"] != "provided_limited_metadata":
            raise InputError("disclosed_file_lookup_nonprovided_reference_rejected")
        reference["matched_file_ids"] = [
            file_id for file_id in requested_ids
            if file_id in files and reference_id in files[file_id]["reference_ids"]
        ]
        reference_results.append(reference)
    return {"file_results": file_results, "reference_results": reference_results,
            "counts": lookup_counts(file_results, reference_results)}


def build_file_lookup(validated_index: ValidatedFileIndex, request: dict) -> dict:
    """Bind the explicit request to recorded Phase36 input-byte identities."""
    request = validate_request(request)
    index = read_disclosed_file_index(validated_index)
    if (request["source_inbox_sha256"] != index["source_inbox_sha256"]
            or request["source_manifest_sha256"] != index["source_manifest_sha256"]):
        raise InputError("disclosed_file_lookup_source_digest_mismatch")
    results = lookup_disclosed_files(validated_index, request["requested_file_ids"])
    lookup = {
        **common(LOOKUP_SCHEMA),
        "request": request,
        "source_inbox_sha256": index["source_inbox_sha256"],
        "source_manifest_sha256": index["source_manifest_sha256"],
        "file_results": results["file_results"],
        "reference_results": results["reference_results"],
        "counts": results["counts"],
        "limitations": list(LIMITATIONS),
    }
    return validate_lookup(lookup)


__all__ = ("lookup_disclosed_files", "build_file_lookup")
