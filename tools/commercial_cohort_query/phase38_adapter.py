"""Actually validate the five Phase38 files into immutable source bytes."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib

from phase33_adapter import InputBudget
from co_reference_contracts import (
    COMMON_FIELDS as SOURCE_COMMON_FIELDS,
    MANIFEST_SCHEMA as OLD_MANIFEST_SCHEMA,
    common as source_common,
    parse_json as source_parse_json,
    json_bytes as source_json_bytes,
    validate_relationships as source_validate_relationships,
    validate_request as source_validate_request,
)
from commercial_co_reference.output_renderer import render_co_reference_summary
from commercial_co_reference.artifact_manifest import manifest_data as source_manifest_data

from cohort_contracts import (
    InputError, SOURCE_NAMES, SOURCE_LIMITS, SOURCE_SCHEMAS,
    closed, fixed, validate_source_artifacts,
)


_MANIFEST_FIELDS = (*SOURCE_COMMON_FIELDS, "files", "source_index_sha256", "source_manifest_sha256",
                    "source_artifacts", "join_counts", "lookup_counts", "request",
                    "manifest_self_excluded", "integrity_scope")


def _validated_source(artifact_bytes: tuple) -> tuple[dict, dict, dict, list, dict]:
    if type(artifact_bytes) is not tuple or len(artifact_bytes) != len(SOURCE_NAMES):
        raise InputError("cohort_exact_five_immutable_Phase38_sources_required")
    raw = dict(zip(SOURCE_NAMES, artifact_bytes))
    for name, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[name]:
            raise InputError("cohort_source_byte_type_or_limit_rejected")
    artifacts = validate_source_artifacts([
        {"name": name, "bytes": len(raw[name]), "sha256": hashlib.sha256(raw[name]).hexdigest(),
         "schema_version": SOURCE_SCHEMAS[name]}
        for name in SOURCE_NAMES
    ])
    join, lookup, receipt = source_validate_relationships(
        source_parse_json(raw["co-reference-join.json"], maximum=SOURCE_LIMITS["co-reference-join.json"]),
        source_parse_json(raw["co-reference-lookup.json"], maximum=SOURCE_LIMITS["co-reference-lookup.json"]),
        source_parse_json(raw["co-reference-source-receipt.json"], maximum=SOURCE_LIMITS["co-reference-source-receipt.json"]),
    )
    manifest = source_parse_json(raw["manifest.json"], maximum=SOURCE_LIMITS["manifest.json"])
    closed(manifest, _MANIFEST_FIELDS, "cohort_old_manifest_fields")
    fixed({key: manifest[key] for key in SOURCE_COMMON_FIELDS},
          source_common(OLD_MANIFEST_SCHEMA), "cohort_old_manifest_common")
    request = source_validate_request(manifest["request"])
    if raw["co-reference-summary.md"] != render_co_reference_summary(join, lookup, receipt):
        raise InputError("cohort_source_summary_correspondence_rejected")
    payloads = {name: raw[name] for name in SOURCE_NAMES[:-1]}
    fixed(manifest["files"], [{"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
                               for item in artifacts[:-1]], "cohort_actual_Phase38_payload_bytes")
    if (source_json_bytes(manifest, maximum=SOURCE_LIMITS["manifest.json"])
            != source_json_bytes(source_manifest_data(join, lookup, receipt, payloads, request), maximum=SOURCE_LIMITS["manifest.json"])):
        raise InputError("cohort_source_full_manifest_correspondence_rejected")
    # The old JOIN's source_index/source_manifest fields remain Phase37 roles;
    # the new artifact descriptors above are actual current Phase38 identities.
    return join, lookup, receipt, artifacts, request


@dataclass(frozen=True, slots=True)
class ValidatedCoReferenceSource:
    """Exact immutable five-file bytes, no mutable approval or model cache."""

    artifact_bytes: tuple[bytes, bytes, bytes, bytes, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        _validated_source(self.artifact_bytes)


def read_co_reference_source(snapshot: ValidatedCoReferenceSource) -> tuple[dict, dict, dict, list, dict]:
    if type(snapshot) is not ValidatedCoReferenceSource:
        raise InputError("cohort_exact_validated_Phase38_source_required")
    join, lookup, receipt, artifacts, request = _validated_source(snapshot.artifact_bytes)
    return deepcopy(join), deepcopy(lookup), deepcopy(receipt), deepcopy(artifacts), deepcopy(request)


def load_co_reference_source(join_path: str, lookup_path: str, receipt_path: str,
                             summary_path: str, manifest_path: str,
                             budget: InputBudget) -> ValidatedCoReferenceSource:
    """Read the five explicit Phase38 CLI paths once under the owner budget."""
    if type(budget) is not InputBudget:
        raise InputError("cohort_exact_input_budget_required")
    paths = (join_path, lookup_path, receipt_path, summary_path, manifest_path)
    raw = tuple(budget.read_text(path, SOURCE_LIMITS[name]) for name, path in zip(SOURCE_NAMES, paths))
    budget.check_stability()
    return ValidatedCoReferenceSource(raw)


__all__ = ("InputBudget", "ValidatedCoReferenceSource", "load_co_reference_source", "read_co_reference_source")
