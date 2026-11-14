"""Validate the exact five Phase41 files without reopening any parent data."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib

from phase40_adapter import InputBudget
from slot_contracts import (
    COMMON_FIELDS as SOURCE_COMMON_FIELDS,
    MANIFEST_SCHEMA as OLD_MANIFEST_SCHEMA,
    common as source_common,
    parse_json as source_parse_json,
    json_bytes as source_json_bytes,
    validate_relationships as source_validate_relationships,
    template_from_slots as source_template_from_slots,
)
from commercial_response_slots.output_renderer import render_response_slot_summary
from commercial_response_slots.artifact_manifest import manifest_data as source_manifest_data

from intake_contracts import (
    InputError, SOURCE_NAMES, SOURCE_LIMITS, SOURCE_SCHEMAS,
    closed, fixed, validate_source_artifacts,
)


_MANIFEST_FIELDS = (*SOURCE_COMMON_FIELDS, "files", "source_phase40_queue_sha256",
                    "source_phase40_manifest_sha256", "source_artifacts", "source_counts", "slots_sha256",
                    "slot_counts", "template_counts", "request", "manifest_self_excluded", "integrity_scope")


def _validated_source(artifact_bytes: tuple) -> tuple[dict, dict, dict, list]:
    if type(artifact_bytes) is not tuple or len(artifact_bytes) != len(SOURCE_NAMES):
        raise InputError("intake_exact_five_immutable_Phase41_sources_required")
    raw = dict(zip(SOURCE_NAMES, artifact_bytes))
    for name, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[name]:
            raise InputError("intake_source_byte_type_or_limit_rejected")
    artifacts = validate_source_artifacts([
        {"name": name, "bytes": len(raw[name]), "sha256": hashlib.sha256(raw[name]).hexdigest(),
         "schema_version": SOURCE_SCHEMAS[name]}
        for name in SOURCE_NAMES
    ])
    manifest = source_parse_json(raw["manifest.json"], maximum=SOURCE_LIMITS["manifest.json"])
    closed(manifest, _MANIFEST_FIELDS, "intake_old_manifest_fields")
    fixed({key: manifest[key] for key in SOURCE_COMMON_FIELDS},
          source_common(OLD_MANIFEST_SCHEMA), "intake_old_manifest_common")
    fixed(manifest["files"], [{"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
                               for item in artifacts[:-1]], "intake_actual_Phase41_payload_bytes")
    slots, template, receipt = source_validate_relationships(
        source_parse_json(raw["task-response-slots.json"], maximum=SOURCE_LIMITS["task-response-slots.json"]),
        source_parse_json(raw["response-template.json"], maximum=SOURCE_LIMITS["response-template.json"]),
        source_parse_json(raw["response-slot-source-receipt.json"], maximum=SOURCE_LIMITS["response-slot-source-receipt.json"]),
    )
    fixed(template, source_template_from_slots(slots), "intake_original_template_slot_correspondence")
    if raw["task-response-slots.json"] != source_json_bytes(slots, maximum=SOURCE_LIMITS["task-response-slots.json"]):
        raise InputError("intake_source_slots_must_be_canonical")
    if raw["response-slot-summary.md"] != render_response_slot_summary(slots, template, receipt):
        raise InputError("intake_source_summary_correspondence_rejected")
    payloads = {name: raw[name] for name in SOURCE_NAMES[:-1]}
    if (source_json_bytes(manifest, maximum=SOURCE_LIMITS["manifest.json"])
            != source_json_bytes(source_manifest_data(slots, template, receipt, payloads), maximum=SOURCE_LIMITS["manifest.json"])):
        raise InputError("intake_source_full_manifest_correspondence_rejected")
    # Original owner validation above retains the parent40 binding preimage.
    # Current descriptors below identify Phase41 slots/manifest, not that parent.
    return slots, template, receipt, artifacts


@dataclass(frozen=True, slots=True)
class ValidatedPhase41Source:
    """Actual immutable five-file group, never a caller validation marker."""

    artifact_bytes: tuple[bytes, bytes, bytes, bytes, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        _validated_source(self.artifact_bytes)


def read_source(snapshot: ValidatedPhase41Source) -> tuple[dict, dict, dict, list]:
    if type(snapshot) is not ValidatedPhase41Source:
        raise InputError("intake_exact_validated_Phase41_source_required")
    slots, template, receipt, artifacts = _validated_source(snapshot.artifact_bytes)
    return deepcopy(slots), deepcopy(template), deepcopy(receipt), deepcopy(artifacts)


def load_source(slots_path: str, template_path: str, receipt_path: str,
                summary_path: str, manifest_path: str, budget: InputBudget) -> ValidatedPhase41Source:
    """Exactly five explicit stable bounded physical reads under one budget."""
    if type(budget) is not InputBudget:
        raise InputError("intake_exact_input_budget_required")
    paths = (slots_path, template_path, receipt_path, summary_path, manifest_path)
    raw = tuple(budget.read_text(path, SOURCE_LIMITS[name]) for name, path in zip(SOURCE_NAMES, paths))
    budget.check_stability()
    return ValidatedPhase41Source(raw)


__all__ = ("InputBudget", "ValidatedPhase41Source", "load_source", "read_source")
