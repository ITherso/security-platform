"""Owner-validate five actual Phase37 files without opening earlier inputs."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib

from phase33_adapter import InputBudget
from index_contracts import (
    COMMON_FIELDS as SOURCE_COMMON_FIELDS,
    MANIFEST_SCHEMA as OLD_MANIFEST_SCHEMA,
    common as source_common,
    json_bytes as source_json_bytes,
    parse_json as parse_source_json,
    make_source_receipt as owner_source_receipt,
    validate_relationships as validate_source_relationships,
)
from disclosed_file_index import ValidatedFileIndex
from reverse_lookup import build_file_lookup
from commercial_file_reference_index.output_renderer import render_index_summary
from commercial_file_reference_index.artifact_manifest import manifest_data as source_manifest_data

from co_reference_contracts import (
    InputError, SOURCE_NAMES, SOURCE_LIMITS, SOURCE_SCHEMAS,
    closed, fixed, validate_source_artifacts,
)


_MANIFEST_FIELDS = (*SOURCE_COMMON_FIELDS, "files", "source_inbox_sha256", "source_manifest_sha256",
                    "source_artifacts", "index_counts", "lookup_counts", "request",
                    "manifest_self_excluded", "integrity_scope")


def _validated_source(artifact_bytes: tuple) -> tuple[dict, list]:
    if type(artifact_bytes) is not tuple or len(artifact_bytes) != len(SOURCE_NAMES):
        raise InputError("co_reference_exact_five_immutable_sources_required")
    raw = dict(zip(SOURCE_NAMES, artifact_bytes))
    for name, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[name]:
            raise InputError("co_reference_source_byte_type_or_limit_rejected")
    artifacts = validate_source_artifacts([
        {"name": name, "bytes": len(raw[name]), "sha256": hashlib.sha256(raw[name]).hexdigest(),
         "schema_version": SOURCE_SCHEMAS[name]}
        for name in SOURCE_NAMES
    ])
    manifest = parse_source_json(raw["manifest.json"], maximum=SOURCE_LIMITS["manifest.json"])
    closed(manifest, _MANIFEST_FIELDS, "co_reference_old_manifest_fields")
    fixed({key: manifest[key] for key in SOURCE_COMMON_FIELDS},
          source_common(OLD_MANIFEST_SCHEMA), "co_reference_old_manifest_common")
    payloads = {name: raw[name] for name in SOURCE_NAMES[:-1]}
    fixed(manifest["files"], [{"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
                               for item in artifacts[:-1]], "co_reference_actual_source_payload_bytes")
    index, lookup, receipt = validate_source_relationships(
        parse_source_json(raw["file-reference-index.json"], maximum=SOURCE_LIMITS["file-reference-index.json"]),
        parse_source_json(raw["file-reference-lookup.json"], maximum=SOURCE_LIMITS["file-reference-lookup.json"]),
        parse_source_json(raw["index-source-receipt.json"], maximum=SOURCE_LIMITS["index-source-receipt.json"]),
    )
    snapshot = ValidatedFileIndex(raw["file-reference-index.json"])
    if (source_json_bytes(lookup, maximum=SOURCE_LIMITS["file-reference-lookup.json"])
            != source_json_bytes(build_file_lookup(snapshot, lookup["request"]), maximum=SOURCE_LIMITS["file-reference-lookup.json"])):
        raise InputError("co_reference_source_lookup_correspondence_rejected")
    if (source_json_bytes(receipt, maximum=SOURCE_LIMITS["index-source-receipt.json"])
            != source_json_bytes(owner_source_receipt(index), maximum=SOURCE_LIMITS["index-source-receipt.json"])):
        raise InputError("co_reference_source_receipt_correspondence_rejected")
    if raw["file-index-summary.md"] != render_index_summary(index, lookup, receipt):
        raise InputError("co_reference_source_summary_correspondence_rejected")
    if (source_json_bytes(manifest, maximum=SOURCE_LIMITS["manifest.json"])
            != source_json_bytes(source_manifest_data(index, lookup, receipt, payloads), maximum=SOURCE_LIMITS["manifest.json"])):
        raise InputError("co_reference_source_manifest_correspondence_rejected")
    return index, artifacts


@dataclass(frozen=True, slots=True)
class ValidatedPhase37Source:
    """Exact immutable real Phase37 bytes, without mutable approval flags."""

    artifact_bytes: tuple[bytes, bytes, bytes, bytes, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        _validated_source(self.artifact_bytes)


def read_source(snapshot: ValidatedPhase37Source) -> tuple[dict, list]:
    if type(snapshot) is not ValidatedPhase37Source:
        raise InputError("co_reference_exact_validated_Phase37_source_required")
    index, artifacts = _validated_source(snapshot.artifact_bytes)
    return deepcopy(index), deepcopy(artifacts)


def load_source(index_path: str, lookup_path: str, receipt_path: str,
                summary_path: str, manifest_path: str,
                budget: InputBudget) -> ValidatedPhase37Source:
    """Read only the five CLI-selected sources using the protected budget."""
    if type(budget) is not InputBudget:
        raise InputError("co_reference_exact_input_budget_required")
    paths = (index_path, lookup_path, receipt_path, summary_path, manifest_path)
    raw = tuple(budget.read_text(path, SOURCE_LIMITS[name]) for name, path in zip(SOURCE_NAMES, paths))
    budget.check_stability()
    return ValidatedPhase37Source(raw)


__all__ = ("InputBudget", "ValidatedPhase37Source", "load_source", "read_source")
