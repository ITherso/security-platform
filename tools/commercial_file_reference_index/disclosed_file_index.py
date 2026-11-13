"""Pure disclosed-file relationships and an exact immutable index snapshot."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from index_contracts import (
    INDEX_SCHEMA, LIMITATIONS, MAX_INDEX_BYTES, InputError, common,
    derive_file_records, fixed, index_counts, json_bytes, parse_json,
    validate_index,
)

if TYPE_CHECKING:
    from phase36_adapter import ValidatedPhase36Source


def _validated_index(raw_bytes: bytes) -> dict:
    if type(raw_bytes) is not bytes:
        raise InputError("disclosed_file_index_exact_immutable_bytes_required")
    return validate_index(parse_json(raw_bytes, maximum=MAX_INDEX_BYTES))


@dataclass(frozen=True, slots=True)
class ValidatedFileIndex:
    """Closed new-index bytes, without mutable cache or approval markers.

    Direct construction checks internal new-wire integrity. It does not reopen
    the original Phase36 files or establish their producer or import history.
    """

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_index(self.raw_bytes)


def read_disclosed_file_index(snapshot: ValidatedFileIndex) -> dict:
    if type(snapshot) is not ValidatedFileIndex:
        raise InputError("disclosed_file_index_exact_validated_snapshot_required")
    return deepcopy(_validated_index(snapshot.raw_bytes))


def build_disclosed_file_index(validated_inbox: ValidatedPhase36Source) -> ValidatedFileIndex:
    """Index complete permitted packets from an actually validated source group.

    Source inbox and manifest digests come from the five actual Phase36 input
    byte identities. They are not hashes of the canonical model reconstructed
    in memory, nor the Phase35 provenance descriptors embedded in that model.
    """
    from phase36_adapter import read_source
    from inbox_contracts import MAX_INBOX_BYTES as SOURCE_MAX_INBOX_BYTES
    from inbox_contracts import json_bytes as source_json_bytes
    from inbox_snapshot import ValidatedInbox
    from reference_query import query_reference_metadata

    inbox, source_artifacts = read_source(validated_inbox)
    provided_ids = sorted(record["reference_id"] for record in inbox["reference_records"]
                          if record["disclosure_status"] == "provided_limited_metadata")
    disclosed_references = []
    if provided_ids:
        source_snapshot = ValidatedInbox(source_json_bytes(inbox, maximum=SOURCE_MAX_INBOX_BYTES))
        disclosed_references = query_reference_metadata(source_snapshot, provided_ids)

    links = {record["reference_id"]: record["candidate_ids"]
             for record in inbox["reference_projection_links"]}
    for reference in disclosed_references:
        reference_id = reference["reference_id"]
        complete_source_projections = [
            projection for projection in inbox["projection_records"]
            if projection["reference_id"] == reference_id
        ]
        fixed(reference["projections"], complete_source_projections,
              "disclosed_file_index_complete_source_reference")
        fixed([projection["candidate_id"] for projection in reference["projections"]],
              links[reference_id], "disclosed_file_index_source_candidate_links")

    file_records = derive_file_records(disclosed_references)
    index = {
        **common(INDEX_SCHEMA),
        "source_inbox_sha256": source_artifacts[0]["sha256"],
        "source_manifest_sha256": source_artifacts[-1]["sha256"],
        "source_schema_version": inbox["schema_version"],
        "source_artifacts": [
            {"name": item["name"], "bytes": item["bytes"],
             "sha256": item["sha256"], "schema_version": item["schema_version"]}
            for item in source_artifacts
        ],
        "source_counts": dict(inbox["counts"]),
        "disclosed_references": disclosed_references,
        "file_records": file_records,
        "counts": index_counts(disclosed_references, file_records),
        "limitations": list(LIMITATIONS),
    }
    index = validate_index(index)
    return ValidatedFileIndex(json_bytes(index, maximum=MAX_INDEX_BYTES))


__all__ = ("ValidatedFileIndex", "build_disclosed_file_index", "read_disclosed_file_index")
