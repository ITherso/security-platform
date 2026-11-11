"""Potential manifest-file associations, explicitly distinct from build closure."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy

from commercial_composition.composition_contracts import DEPENDENCY_FIELDS
from commercial_license_review.evidence_contracts import record_digest
from .component_selection import project_variants
from .variant_contracts import DEPENDENCIES_SCHEMA, EXPOSURE_CLASSES, InputError, common


def _exposures(row: dict, potential: list[str], variants: list[dict]) -> list[dict]:
    result = []
    for variant in variants:
        selected = [identity for identity in potential if identity in variant["selected_component_ids"]]
        if row["review_scope"] == "excluded_backend_context":
            classification, reason = "excluded_context_record", "excluded_backend_context_preserved"
        elif selected and len(potential) > 1:
            classification, reason = "shared_or_ambiguous_scope", "potential_source_file_shared"
        elif selected:
            classification, reason = "declared_source_scope", "potential_source_file_single"
        else:
            classification, reason = "unattributed_record", "no_selected_potential_source_association"
        # Existing contracts have no owning dependency/component pair. Neither
        # directness nor one matching manifest file can produce an explicit link.
        result.append({"variant_id": variant["variant_id"], "classification": classification,
                       "reason_code": reason, "selected_potential_component_ids": selected})
    return result


def _project(records: list[dict], components: list[dict], manifests: list[dict],
             variants: list[dict], source_reference: dict, candidate_reference: str) -> dict:
    variants = project_variants(variants, components)
    manifest_by_id = {row["manifest_id"]: row for row in manifests}
    projected, identities = [], set()
    artifact_digest = source_reference["composition_sources"]["dependencies"]["sha256"]
    for index, row in enumerate(records):
        original = {name: deepcopy(row[name]) for name in DEPENDENCY_FIELDS}
        identity = row["dependency_id"]
        manifest = manifest_by_id.get(row["manifest_id"])
        if identity in identities or manifest is None:
            raise InputError("variant_dependency_reference_or_duplicate")
        identities.add(identity)
        if (row["source_json_pointer"] != f"/dependencies/{index}"
                or row["source_record_sha256"] != record_digest(original)
                or row["source_artifact_sha256"] != artifact_digest
                or row["manifest_file_ref"] != manifest["source_file_ref"]
                or row["review_scope"] != manifest["context"]):
            raise InputError("variant_dependency_source_identity_mismatch")
        potential = [component["component_id"] for component in components
                     if manifest["source_file_ref"] in component["source_file_refs"]]
        projected.append({**original,
                          "source_json_pointer": row["source_json_pointer"],
                          "source_record_sha256": row["source_record_sha256"],
                          "source_artifact_sha256": artifact_digest,
                          "manifest_file_ref": manifest["source_file_ref"],
                          "license_source_key": row["license_source_key"],
                          "potential_component_ids": potential,
                          "exposures": _exposures(original, potential, variants)})
    relation = Counter(row["relation"] for row in projected)
    directness = Counter(row["directness"] for row in projected)
    by_variant = []
    for variant in variants:
        classes = Counter(exposure["classification"] for row in projected for exposure in row["exposures"]
                          if exposure["variant_id"] == variant["variant_id"])
        by_variant.append({"variant_id": variant["variant_id"], "classifications": [
            {"classification": name, "record_count": classes[name]} for name in EXPOSURE_CLASSES]})
    return {**common(DEPENDENCIES_SCHEMA, candidate_reference),
            "source_reference": deepcopy(source_reference), "records": projected,
            "counts": {"source_dependency_record_count": len(projected), "variant_count": len(variants),
                       "by_relation": [{"relation": name, "record_count": relation[name]}
                                       for name in ("direct_declaration", "lock_record")],
                       "by_directness": [{"directness": name, "record_count": directness[name]}
                                         for name in ("direct_in_selected_manifest", "unknown")],
                       "by_variant": by_variant},
            "package_identity_deduplication": "not_performed_records_are_not_unique_packages"}


def build_dependencies(dependencies: dict, components: list[dict], manifests: list[dict],
                       evidence_ledger: dict, variants: list[dict], source_reference: dict,
                       *, candidate_reference: str) -> dict:
    subjects = {row["subject_id"]: row for row in evidence_ledger["source_subjects"]
                if row["subject_type"] == "dependency"}
    manifest_by_id = {row["manifest_id"]: row for row in manifests}
    records = []
    digest = source_reference["composition_sources"]["dependencies"]["sha256"]
    for index, row in enumerate(dependencies["dependencies"]):
        subject = subjects.get(row["dependency_id"])
        manifest = manifest_by_id.get(row["manifest_id"])
        if subject is None or manifest is None:
            raise InputError("variant_dependency_license_reference_missing")
        if (subject["source_json_pointer"] != f"/dependencies/{index}"
                or subject["source_record_sha256"] != record_digest(row)
                or subject["source_artifact_sha256"] != digest):
            raise InputError("variant_dependency_evidence_identity_mismatch")
        records.append({**deepcopy(row), "source_json_pointer": subject["source_json_pointer"],
                        "source_record_sha256": subject["source_record_sha256"],
                        "source_artifact_sha256": digest, "manifest_file_ref": manifest["source_file_ref"],
                        "license_source_key": subject["source_key"]})
    if len(records) != len(subjects):
        raise InputError("variant_dependency_projection_incomplete")
    return _project(records, components, manifests, variants, source_reference, candidate_reference)


def rebuild_dependencies(document: dict, components: list[dict], manifests: list[dict],
                         variants: list[dict]) -> dict:
    """Recompute internal projections only; never re-open or attest old sources."""
    return _project(document["records"], components, manifests, variants,
                    document["source_reference"], document["candidate_reference"])


__all__ = ("build_dependencies", "rebuild_dependencies")
