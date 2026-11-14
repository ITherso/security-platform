"""Validate exactly five current Phase39 artifacts into immutable bytes."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib

from phase38_adapter import InputBudget
from cohort_contracts import (
    COMMON_FIELDS as SOURCE_COMMON_FIELDS,
    MANIFEST_SCHEMA as OLD_MANIFEST_SCHEMA,
    common as source_common,
    parse_json as source_parse_json,
    json_bytes as source_json_bytes,
    validate_relationships as source_validate_relationships,
    query_from_witnesses as source_query_from_witnesses,
)
from commercial_cohort_query.output_renderer import render_cohort_summary
from commercial_cohort_query.artifact_manifest import manifest_data as source_manifest_data

from followup_contracts import (
    InputError, SOURCE_NAMES, SOURCE_LIMITS, SOURCE_SCHEMAS,
    closed, fixed, validate_source_artifacts,
)


_MANIFEST_FIELDS = (*SOURCE_COMMON_FIELDS, "files", "source_phase38_join_sha256",
                    "source_phase38_manifest_sha256", "source_artifacts", "query_counts",
                    "request", "manifest_self_excluded", "integrity_scope")


def _validated_source(artifact_bytes: tuple) -> tuple[dict, dict, dict, list]:
    if type(artifact_bytes) is not tuple or len(artifact_bytes) != len(SOURCE_NAMES):
        raise InputError("followup_exact_five_immutable_Phase39_sources_required")
    raw = dict(zip(SOURCE_NAMES, artifact_bytes))
    for name, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[name]:
            raise InputError("followup_source_byte_type_or_limit_rejected")
    artifacts = validate_source_artifacts([
        {"name": name, "bytes": len(raw[name]), "sha256": hashlib.sha256(raw[name]).hexdigest(),
         "schema_version": SOURCE_SCHEMAS[name]}
        for name in SOURCE_NAMES
    ])
    # Bind the old manifest to all four actual payload byte strings first.
    # Its source_phase38_* values remain lineage, never the current identities.
    manifest = source_parse_json(raw["manifest.json"], maximum=SOURCE_LIMITS["manifest.json"])
    closed(manifest, _MANIFEST_FIELDS, "followup_old_manifest_fields")
    fixed({key: manifest[key] for key in SOURCE_COMMON_FIELDS},
          source_common(OLD_MANIFEST_SCHEMA), "followup_old_manifest_common")
    fixed(manifest["files"], [{"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
                               for item in artifacts[:-1]], "followup_actual_Phase39_payload_bytes")
    query, witnesses, receipt = source_validate_relationships(
        source_parse_json(raw["cohort-query.json"], maximum=SOURCE_LIMITS["cohort-query.json"]),
        source_parse_json(raw["cohort-witnesses.json"], maximum=SOURCE_LIMITS["cohort-witnesses.json"]),
        source_parse_json(raw["cohort-source-receipt.json"], maximum=SOURCE_LIMITS["cohort-source-receipt.json"]),
    )
    fixed(query, source_query_from_witnesses(witnesses), "followup_original_full_query_witness_relation")
    if raw["cohort-summary.md"] != render_cohort_summary(query, witnesses, receipt):
        raise InputError("followup_source_summary_correspondence_rejected")
    payloads = {name: raw[name] for name in SOURCE_NAMES[:-1]}
    if (source_json_bytes(manifest, maximum=SOURCE_LIMITS["manifest.json"])
            != source_json_bytes(source_manifest_data(query, witnesses, receipt, payloads), maximum=SOURCE_LIMITS["manifest.json"])):
        raise InputError("followup_source_full_manifest_correspondence_rejected")
    return query, witnesses, receipt, artifacts


@dataclass(frozen=True, slots=True)
class ValidatedPhase39Source:
    """The actual immutable group, with no caller approval flag or model cache."""

    artifact_bytes: tuple[bytes, bytes, bytes, bytes, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        _validated_source(self.artifact_bytes)


def read_source(snapshot: ValidatedPhase39Source) -> tuple[dict, dict, dict, list]:
    if type(snapshot) is not ValidatedPhase39Source:
        raise InputError("followup_exact_validated_Phase39_source_required")
    query, witnesses, receipt, artifacts = _validated_source(snapshot.artifact_bytes)
    return deepcopy(query), deepcopy(witnesses), deepcopy(receipt), deepcopy(artifacts)


def load_source(query_path: str, witnesses_path: str, receipt_path: str,
                summary_path: str, manifest_path: str, budget: InputBudget) -> ValidatedPhase39Source:
    """Only five explicit bounded stable physical reads; all later reads pure."""
    if type(budget) is not InputBudget:
        raise InputError("followup_exact_input_budget_required")
    paths = (query_path, witnesses_path, receipt_path, summary_path, manifest_path)
    raw = tuple(budget.read_text(path, SOURCE_LIMITS[name]) for name, path in zip(SOURCE_NAMES, paths))
    budget.check_stability()
    return ValidatedPhase39Source(raw)


__all__ = ("InputBudget", "ValidatedPhase39Source", "load_source", "read_source")
