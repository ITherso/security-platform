"""Closed source catalogs and explicit component partitions; no file access."""
from __future__ import annotations

from copy import deepcopy

from commercial_composition.composition_contracts import COMPONENT_FIELDS
from commercial_license_review.evidence_contracts import record_digest
from .variant_contracts import InputError, MAX_VARIANTS


VARIANT_FIELDS = ("variant_id", "label", "description", "selected_component_ids", "not_selected_component_ids")
MANIFEST_FIELDS = ("manifest_id", "root_id", "path", "sha256", "bytes", "format", "context",
                   "parse_status", "record_count", "limitation_code")


def build_component_catalog(inventory: dict, evidence_ledger: dict) -> list[dict]:
    subjects = {row["subject_id"]: row for row in evidence_ledger["source_subjects"]
                if row["subject_type"] == "component"}
    files = {(row["root_id"], row["path"]): row["file_id"] for row in inventory["files"]}
    digest = evidence_ledger["composition_reference"]["inventory"]["sha256"]
    catalog = []
    for index, row in enumerate(inventory["components"]):
        subject = subjects.get(row["component_id"])
        key = (row["root_id"], row["manifest_path"])
        if subject is None or key not in files:
            raise InputError("variant_component_source_reference_missing")
        if (subject["source_record_sha256"] != record_digest(row)
                or subject["source_json_pointer"] != f"/components/{index}"
                or subject["source_artifact_sha256"] != digest):
            raise InputError("variant_component_evidence_identity_mismatch")
        catalog.append({**{name: deepcopy(row[name]) for name in COMPONENT_FIELDS},
                        "manifest_file_ref": files[key],
                        "source_json_pointer": subject["source_json_pointer"],
                        "source_record_sha256": subject["source_record_sha256"],
                        "source_artifact_sha256": digest, "license_source_key": subject["source_key"]})
    if len(catalog) != len(subjects):
        raise InputError("variant_component_evidence_projection_incomplete")
    return catalog


def build_manifest_catalog(inventory: dict, dependencies: dict) -> list[dict]:
    files = {(row["root_id"], row["path"]): row for row in inventory["files"]}
    catalog = []
    for row in dependencies["manifest_records"]:
        file = files.get((row["root_id"], row["path"]))
        if file is None or file["sha256"] != row["sha256"] or file["bytes"] != row["bytes"]:
            raise InputError("variant_manifest_file_identity_mismatch")
        catalog.append({**{name: deepcopy(row[name]) for name in MANIFEST_FIELDS},
                        "source_file_ref": file["file_id"]})
    return catalog


def project_variants(variants: list[dict], components: list[dict]) -> list[dict]:
    """Require the full real component partition; never choose by display name."""
    catalog = {row["component_id"] for row in components}
    if len(catalog) != len(components) or not 1 <= len(variants) <= MAX_VARIANTS:
        raise InputError("variant_component_selection_limit_or_duplicate")
    identities, result = set(), []
    for row in variants:
        identity = row["variant_id"]
        selected, omitted = row["selected_component_ids"], row["not_selected_component_ids"]
        if (identity in identities or not selected or len(set(selected)) != len(selected)
                or len(set(omitted)) != len(omitted) or set(selected) & set(omitted)
                or (set(selected) | set(omitted)) != catalog):
            raise InputError("variant_component_partition_invalid")
        identities.add(identity)
        result.append({name: deepcopy(row[name]) for name in VARIANT_FIELDS})
    return result


__all__ = ("build_component_catalog", "build_manifest_catalog", "project_variants")
