"""Validate only the five explicit Phase40 outputs into immutable bytes."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib

from phase39_adapter import InputBudget
from followup_contracts import (
    COMMON_FIELDS as SOURCE_COMMON_FIELDS,
    MANIFEST_SCHEMA as OLD_MANIFEST_SCHEMA,
    common as source_common,
    parse_json as source_parse_json,
    json_bytes as source_json_bytes,
    validate_relationships as source_validate_relationships,
)
from commercial_evidence_followup.output_renderer import render_followup_summary
from commercial_evidence_followup.artifact_manifest import manifest_data as source_manifest_data

from slot_contracts import (
    InputError, SOURCE_NAMES, SOURCE_LIMITS, SOURCE_SCHEMAS,
    closed, fixed, validate_source_artifacts,
)


_MANIFEST_FIELDS = (*SOURCE_COMMON_FIELDS, "files", "source_phase39_witnesses_sha256",
                    "source_phase39_manifest_sha256", "source_artifacts", "queue_sha256", "queue_counts",
                    "handoff_counts", "request", "manifest_self_excluded", "integrity_scope")


def _validated_source(artifact_bytes: tuple) -> tuple[dict, dict, dict, list]:
    if type(artifact_bytes) is not tuple or len(artifact_bytes) != len(SOURCE_NAMES):
        raise InputError("slots_exact_five_immutable_Phase40_sources_required")
    raw = dict(zip(SOURCE_NAMES, artifact_bytes))
    for name, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[name]:
            raise InputError("slots_source_byte_type_or_limit_rejected")
    artifacts = validate_source_artifacts([
        {"name": name, "bytes": len(raw[name]), "sha256": hashlib.sha256(raw[name]).hexdigest(),
         "schema_version": SOURCE_SCHEMAS[name]}
        for name in SOURCE_NAMES
    ])
    manifest = source_parse_json(raw["manifest.json"], maximum=SOURCE_LIMITS["manifest.json"])
    closed(manifest, _MANIFEST_FIELDS, "slots_old_manifest_fields")
    fixed({key: manifest[key] for key in SOURCE_COMMON_FIELDS},
          source_common(OLD_MANIFEST_SCHEMA), "slots_old_manifest_common")
    # First bind the manifest to the actual four payloads. Embedded Phase39
    # hashes remain parent lineage; current source queue is artifact role zero.
    fixed(manifest["files"], [{"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
                               for item in artifacts[:-1]], "slots_actual_Phase40_payload_bytes")
    queue, handoff, receipt = source_validate_relationships(
        source_parse_json(raw["evidence-followup-queue.json"], maximum=SOURCE_LIMITS["evidence-followup-queue.json"]),
        source_parse_json(raw["analyst-handoff.json"], maximum=SOURCE_LIMITS["analyst-handoff.json"]),
        source_parse_json(raw["followup-source-receipt.json"], maximum=SOURCE_LIMITS["followup-source-receipt.json"]),
    )
    if raw["evidence-followup-queue.json"] != source_json_bytes(queue, maximum=SOURCE_LIMITS["evidence-followup-queue.json"]):
        raise InputError("slots_source_queue_must_be_canonical")
    if raw["followup-summary.md"] != render_followup_summary(queue, handoff, receipt):
        raise InputError("slots_source_summary_correspondence_rejected")
    payloads = {name: raw[name] for name in SOURCE_NAMES[:-1]}
    if (source_json_bytes(manifest, maximum=SOURCE_LIMITS["manifest.json"])
            != source_json_bytes(source_manifest_data(queue, handoff, receipt, payloads), maximum=SOURCE_LIMITS["manifest.json"])):
        raise InputError("slots_source_full_manifest_correspondence_rejected")
    return queue, handoff, receipt, artifacts


@dataclass(frozen=True, slots=True)
class ValidatedPhase40Source:
    """Actual five immutable bytes; never a source-freshness approval token."""

    artifact_bytes: tuple[bytes, bytes, bytes, bytes, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        _validated_source(self.artifact_bytes)


def read_source(snapshot: ValidatedPhase40Source) -> tuple[dict, dict, dict, list]:
    if type(snapshot) is not ValidatedPhase40Source:
        raise InputError("slots_exact_validated_Phase40_source_required")
    queue, handoff, receipt, artifacts = _validated_source(snapshot.artifact_bytes)
    return deepcopy(queue), deepcopy(handoff), deepcopy(receipt), deepcopy(artifacts)


def load_source(queue_path: str, handoff_path: str, receipt_path: str,
                summary_path: str, manifest_path: str, budget: InputBudget) -> ValidatedPhase40Source:
    """Five explicit bounded stable reads; the excluded inspector is no input."""
    if type(budget) is not InputBudget:
        raise InputError("slots_exact_input_budget_required")
    paths = (queue_path, handoff_path, receipt_path, summary_path, manifest_path)
    raw = tuple(budget.read_text(path, SOURCE_LIMITS[name]) for name, path in zip(SOURCE_NAMES, paths))
    budget.check_stability()
    return ValidatedPhase40Source(raw)


__all__ = ("InputBudget", "ValidatedPhase40Source", "load_source", "read_source")
