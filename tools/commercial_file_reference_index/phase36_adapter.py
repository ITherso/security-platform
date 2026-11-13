"""Actual five-file Phase36 validation into an immutable source snapshot."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib

from phase33_adapter import InputBudget
from inbox_contracts import (
    COMMON_FIELDS as SOURCE_COMMON_FIELDS,
    MANIFEST_SCHEMA as OLD_MANIFEST_SCHEMA,
    common as source_common,
    json_bytes as source_json_bytes,
    parse_json as parse_source_json,
    validate_relationships as validate_source_relationships,
)
from inbox_snapshot import ValidatedInbox
from reference_query import build_reference_query
from import_receipt import build_import_receipt
from commercial_tabular_inbox.output_renderer import render_inbox_summary
from commercial_tabular_inbox.artifact_manifest import manifest_data as source_manifest_data

from index_contracts import (
    InputError, SOURCE_LIMITS, SOURCE_NAMES, SOURCE_SCHEMAS,
    closed, fixed, validate_source_artifacts,
)


_MANIFEST_FIELDS = (*SOURCE_COMMON_FIELDS, "files", "source_artifacts", "counts",
                    "query_counts", "request", "manifest_self_excluded", "integrity_scope")


def _validated_source(artifact_bytes: tuple) -> tuple[dict, list]:
    if type(artifact_bytes) is not tuple or len(artifact_bytes) != len(SOURCE_NAMES):
        raise InputError("file_index_exact_five_immutable_sources_required")
    raw = dict(zip(SOURCE_NAMES, artifact_bytes))
    for name, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[name]:
            raise InputError("file_index_source_bytes_type_or_limit_rejected")
    artifacts = validate_source_artifacts([
        {"name": name, "bytes": len(raw[name]), "sha256": hashlib.sha256(raw[name]).hexdigest(),
         "schema_version": SOURCE_SCHEMAS[name]}
        for name in SOURCE_NAMES
    ])
    actual_manifest = parse_source_json(raw["manifest.json"], maximum=SOURCE_LIMITS["manifest.json"])
    closed(actual_manifest, _MANIFEST_FIELDS, "file_index_old_manifest_fields")
    fixed({key: actual_manifest[key] for key in SOURCE_COMMON_FIELDS},
          source_common(OLD_MANIFEST_SCHEMA), "file_index_old_manifest_common")
    payloads = {name: raw[name] for name in SOURCE_NAMES[:-1]}
    fixed(actual_manifest["files"], [{"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
                                     for item in artifacts[:-1]], "file_index_actual_source_payload_bytes")

    inbox, query, receipt = validate_source_relationships(
        parse_source_json(raw["typed-inbox.json"], maximum=SOURCE_LIMITS["typed-inbox.json"]),
        parse_source_json(raw["reference-query.json"], maximum=SOURCE_LIMITS["reference-query.json"]),
        parse_source_json(raw["import-receipt.json"], maximum=SOURCE_LIMITS["import-receipt.json"]),
    )
    # This temporary owner snapshot supports its pure query/receipt APIs. The
    # public five-file snapshot is returned only after every check succeeds.
    snapshot = ValidatedInbox(raw["typed-inbox.json"])
    if (source_json_bytes(query, maximum=SOURCE_LIMITS["reference-query.json"])
            != source_json_bytes(build_reference_query(snapshot, query["request"]), maximum=SOURCE_LIMITS["reference-query.json"])):
        raise InputError("file_index_source_query_correspondence_rejected")
    if (source_json_bytes(receipt, maximum=SOURCE_LIMITS["import-receipt.json"])
            != source_json_bytes(build_import_receipt(snapshot), maximum=SOURCE_LIMITS["import-receipt.json"])):
        raise InputError("file_index_source_receipt_correspondence_rejected")
    if raw["inbox-summary.md"] != render_inbox_summary(inbox, query, receipt):
        raise InputError("file_index_source_summary_correspondence_rejected")
    if (source_json_bytes(actual_manifest, maximum=SOURCE_LIMITS["manifest.json"])
            != source_json_bytes(source_manifest_data(inbox, query, receipt, payloads), maximum=SOURCE_LIMITS["manifest.json"])):
        raise InputError("file_index_source_manifest_correspondence_rejected")
    return inbox, artifacts


@dataclass(frozen=True, slots=True)
class ValidatedPhase36Source:
    """Exact immutable actual Phase36 bytes, never embedded Phase35 markers."""

    artifact_bytes: tuple[bytes, bytes, bytes, bytes, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        _validated_source(self.artifact_bytes)


def read_source(snapshot: ValidatedPhase36Source) -> tuple[dict, list]:
    if type(snapshot) is not ValidatedPhase36Source:
        raise InputError("file_index_exact_validated_Phase36_source_required")
    inbox, artifacts = _validated_source(snapshot.artifact_bytes)
    return deepcopy(inbox), deepcopy(artifacts)


def load_source(inbox_path: str, query_path: str, receipt_path: str,
                summary_path: str, manifest_path: str,
                budget: InputBudget) -> ValidatedPhase36Source:
    """Read only the five explicit CLI files using the existing safe reader."""
    if type(budget) is not InputBudget:
        raise InputError("file_index_exact_input_budget_required")
    paths = (inbox_path, query_path, receipt_path, summary_path, manifest_path)
    raw = tuple(budget.read_text(path, SOURCE_LIMITS[name]) for name, path in zip(SOURCE_NAMES, paths))
    budget.check_stability()
    return ValidatedPhase36Source(raw)


__all__ = ("InputBudget", "ValidatedPhase36Source", "load_source", "read_source")
