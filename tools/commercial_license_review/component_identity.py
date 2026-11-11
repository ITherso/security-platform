"""Immutable, artifact-scoped identities of actual Phase24 license subjects."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from commercial_composition.composition_contracts import validate_documents as validate_composition
from .evidence_contracts import (
    InputError, MAX_RECORDS, record_digest, source_key_for, validate_reference, validate_subject,
)

if TYPE_CHECKING:
    from .composition_adapter import CompositionContext


@dataclass(frozen=True, slots=True)
class SourceSubject:
    source_key: str
    source_license_id: str
    subject_type: str
    subject_id: str
    source_artifact: str
    source_artifact_sha256: str
    source_json_pointer: str
    source_record_sha256: str
    license_record_pointer: str
    license_record_sha256: str
    ecosystem: str
    name: str
    version: str | None
    source_type: str
    manifest_id: str | None
    manifest_file_ref: str
    product_scope: str
    base_declared_license: str | None
    base_evidence_level: str
    base_source_file_refs: tuple[str, ...]
    base_human_review_required: bool = True

    def __post_init__(self) -> None:
        nullable = ("version", "manifest_id", "base_declared_license")
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name == "base_source_file_refs":
                if type(value) is not tuple or any(type(item) is not str for item in value):
                    raise InputError("license_evidence_mutable_subject_reference")
            elif name == "base_human_review_required":
                if value is not True:
                    raise InputError("license_evidence_subject_review_required")
            elif type(value) is not str and not (name in nullable and value is None):
                raise InputError("license_evidence_non_scalar_subject_metadata")

    def to_dict(self) -> dict:
        """Return only allowed metadata; no raw source rows or file paths."""
        return {
            "source_key": self.source_key, "source_license_id": self.source_license_id,
            "subject_type": self.subject_type, "subject_id": self.subject_id,
            "source_artifact": self.source_artifact, "source_artifact_sha256": self.source_artifact_sha256,
            "source_json_pointer": self.source_json_pointer, "source_record_sha256": self.source_record_sha256,
            "license_record_pointer": self.license_record_pointer, "license_record_sha256": self.license_record_sha256,
            "ecosystem": self.ecosystem, "name": self.name, "version": self.version,
            "source_type": self.source_type, "manifest_id": self.manifest_id,
            "manifest_file_ref": self.manifest_file_ref, "product_scope": self.product_scope,
            "base_declared_license": self.base_declared_license, "base_evidence_level": self.base_evidence_level,
            "base_source_file_refs": list(self.base_source_file_refs),
            "base_human_review_required": self.base_human_review_required,
        }


def build_subjects(base: CompositionContext) -> list[dict]:
    """Preserve every original L row and its exact primary-row digest/location.

    The adapter binds the five input byte identities. This pure projection does
    not reopen those inputs, source roots, package caches, or dependency files.
    """
    validate_composition(base.inventory, base.dependencies, base.constraints)
    reference = validate_reference(base.reference)
    inventory, ledger = base.inventory, base.dependencies
    declared_pins = {row["root_id"]: row["pinned_commit"] for row in inventory["source_roots"]}
    if reference["source_commits"] != declared_pins:
        raise InputError("license_evidence_declared_source_commit_relationship")
    if not 1 <= len(ledger["license_evidence"]) <= MAX_RECORDS:
        raise InputError("license_evidence_source_record_limit")
    components = {row["component_id"]: (index, row) for index, row in enumerate(inventory["components"])}
    dependencies = {row["dependency_id"]: (index, row) for index, row in enumerate(ledger["dependencies"])}
    files = {(row["root_id"], row["path"]): row["file_id"] for row in inventory["files"]}
    manifests = {row["manifest_id"]: row for row in ledger["manifest_records"]}
    subjects = []
    for license_index, license_row in enumerate(ledger["license_evidence"]):
        subject_type, subject_id = license_row["subject_type"], license_row["subject_id"]
        if subject_type == "component":
            primary_index, primary = components[subject_id]
            if primary["manifest_path"] is None:
                raise InputError("license_evidence_component_manifest_not_selected")
            manifest_key = (primary["root_id"], primary["manifest_path"])
            artifact, pointer = "inventory", f"/components/{primary_index}"
            ecosystem, name = "first_party_source", primary["component_id"]
            version, source_type = primary["version_declaration"], "source_repository"
            manifest_id, product_scope = None, "proposed_source_component"
        else:
            primary_index, primary = dependencies[subject_id]
            manifest = manifests[primary["manifest_id"]]
            manifest_key = (manifest["root_id"], manifest["path"])
            artifact, pointer = "dependencies", f"/dependencies/{primary_index}"
            ecosystem, name = primary["ecosystem"], primary["name"]
            version, source_type = primary["version"], primary["source_type"]
            manifest_id, product_scope = primary["manifest_id"], primary["review_scope"]
        if manifest_key not in files:
            raise InputError("license_evidence_primary_manifest_reference_missing")
        row = {
            "source_license_id": license_row["evidence_id"], "subject_type": subject_type,
            "subject_id": subject_id, "source_artifact": artifact,
            "source_artifact_sha256": reference[artifact]["sha256"],
            "source_json_pointer": pointer, "source_record_sha256": record_digest(primary),
            "license_record_pointer": f"/license_evidence/{license_index}",
            "license_record_sha256": record_digest(license_row), "ecosystem": ecosystem,
            "name": name, "version": version, "source_type": source_type,
            "manifest_id": manifest_id, "manifest_file_ref": files[manifest_key],
            "product_scope": product_scope, "base_declared_license": license_row["declared_license"],
            "base_evidence_level": license_row["evidence_level"],
            "base_source_file_refs": list(license_row["source_file_refs"]),
            "base_human_review_required": license_row["human_review_required"],
        }
        row["source_key"] = source_key_for(row, reference)
        checked = validate_subject(row, reference, license_index)
        checked["base_source_file_refs"] = tuple(checked["base_source_file_refs"])
        subjects.append(SourceSubject(**checked).to_dict())
    return subjects


__all__ = ("SourceSubject", "build_subjects")
