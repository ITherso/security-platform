"""Five explicit Phase35 artifacts to an actually reconciled typed import.

Only this assembly boundary reads source files. No capsule adapter, ZIP reader,
guard or source scanner is called. Immutable source bytes are revalidated on
construction and consumption rather than relying on an approval marker.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib

from phase33_adapter import InputBudget
from tabular_contracts import (
    COMMON_FIELDS as SOURCE_COMMON_FIELDS,
    MANIFEST_SCHEMA as SOURCE_MANIFEST_SCHEMA,
    common as source_common,
    dataset_counts,
    json_bytes as source_json_bytes,
    parse_json as parse_source_json,
    validate_dataset,
)
from commercial_capsule_tabular.artifact_manifest import manifest_data as source_manifest_data
from commercial_capsule_tabular.output_renderer import render_summary as render_tabular_summary

from inbox_contracts import (
    INBOX_SCHEMA, INBOX_SCOPE, LIMITATIONS, SOURCE_LIMITS, SOURCE_NAMES,
    InputError, closed, common, fixed, validate_inbox,
)
from typed_csv_reader import parse_typed_csvs


_SOURCE_MANIFEST_FIELDS = (
    *SOURCE_COMMON_FIELDS, "files", "source_capsule", "counts",
    "reference_data_rows", "projection_data_rows", "csv_encoding",
    "manifest_self_excluded", "integrity_scope",
)


def _validated_inbox(artifact_bytes: tuple) -> dict:
    if type(artifact_bytes) is not tuple or len(artifact_bytes) != len(SOURCE_NAMES):
        raise InputError("typed_import_exact_five_immutable_artifacts_required")
    raw = dict(zip(SOURCE_NAMES, artifact_bytes))
    for name, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= SOURCE_LIMITS[name]:
            raise InputError("typed_import_source_byte_type_or_limit_rejected")

    # Establish real four-payload byte identities before dataset validation.
    # The complete owning manifest is compared below after its dataset can be
    # validated. No embedded path or member name is followed.
    manifest = parse_source_json(raw["manifest.json"], maximum=SOURCE_LIMITS["manifest.json"])
    closed(manifest, _SOURCE_MANIFEST_FIELDS, "typed_import_source_manifest_fields")
    fixed({key: manifest[key] for key in SOURCE_COMMON_FIELDS},
          source_common(SOURCE_MANIFEST_SCHEMA), "typed_import_source_manifest_common")
    payloads = {name: raw[name] for name in SOURCE_NAMES[:-1]}
    identities = [{"name": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
                  for name, body in payloads.items()]
    fixed(manifest["files"], identities, "typed_import_source_payload_byte_binding")

    dataset = validate_dataset(parse_source_json(
        raw["tabular-dataset.json"], maximum=SOURCE_LIMITS["tabular-dataset.json"]))
    expected_manifest = source_manifest_data(dataset, payloads)
    if (source_json_bytes(manifest, maximum=SOURCE_LIMITS["manifest.json"])
            != source_json_bytes(expected_manifest, maximum=SOURCE_LIMITS["manifest.json"])):
        raise InputError("typed_import_source_manifest_correspondence_rejected")
    if raw["tabular-summary.md"] != render_tabular_summary(dataset):
        raise InputError("typed_import_source_summary_mismatch")
    references, projections = parse_typed_csvs(
        dataset, raw["reference-register.csv"], raw["projection-register.csv"])

    inbox = {
        **common(INBOX_SCHEMA),
        "source_artifacts": [
            {"name": name, "bytes": len(raw[name]),
             "sha256": hashlib.sha256(raw[name]).hexdigest()}
            for name in SOURCE_NAMES
        ],
        "source_dataset_schema": dataset["schema_version"],
        "reference_records": references,
        "projection_records": projections,
        "reference_projection_links": [
            {"reference_id": reference["reference_id"],
             "candidate_ids": [p["candidate_id"] for p in projections
                               if p["reference_id"] == reference["reference_id"]]}
            for reference in references
        ],
        "counts": dataset_counts(references, projections),
        "import_scope": INBOX_SCOPE,
        "limitations": list(LIMITATIONS),
    }
    return validate_inbox(inbox)


@dataclass(frozen=True, slots=True)
class ValidatedTabularImport:
    """Exact immutable five-file bytes, not a caller-supplied trusted model."""

    artifact_bytes: tuple[bytes, bytes, bytes, bytes, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        _validated_inbox(self.artifact_bytes)


def read_validated_import(snapshot: ValidatedTabularImport) -> dict:
    if type(snapshot) is not ValidatedTabularImport:
        raise InputError("typed_import_exact_validated_snapshot_required")
    return deepcopy(_validated_inbox(snapshot.artifact_bytes))


def load_tabular_import(dataset_path: str, references_path: str,
                        projections_path: str, summary_path: str,
                        manifest_path: str, budget: InputBudget) -> ValidatedTabularImport:
    """Read only the five CLI inputs using the existing bounded text reader."""
    if type(budget) is not InputBudget:
        raise InputError("typed_import_exact_input_budget_required")
    paths = (dataset_path, references_path, projections_path, summary_path, manifest_path)
    raw = tuple(budget.read_text(path, SOURCE_LIMITS[name])
                for name, path in zip(SOURCE_NAMES, paths))
    budget.check_stability()
    return ValidatedTabularImport(raw)


__all__ = ("InputBudget", "ValidatedTabularImport", "load_tabular_import", "read_validated_import")
