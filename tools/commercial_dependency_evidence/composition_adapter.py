"""Load explicit Phase24/26 artifacts, never rediscover sources from metadata."""
from __future__ import annotations

from dataclasses import dataclass
import copy

from commercial_handoff.input_loader import explicit_relative_path
from commercial_composition.artifact_manifest import identity, manifest_data as composition_manifest
from commercial_composition.composition_contracts import DEPENDENCY_FIELDS, validate_documents as validate_composition
from commercial_composition.release_constraints import build_constraints
from commercial_license_review.evidence_contracts import record_digest
from commercial_pilot_variants.composition_adapter import ReadBudget, COMPOSITION_SCHEMAS
from commercial_pilot_variants.variant_contracts import validate_documents as validate_pilot
from commercial_pilot_variants.artifact_manifest import manifest_data as pilot_manifest
from commercial_pilot_variants.output_renderer import render_summary as pilot_summary
from .evidence_contracts import InputError, json_bytes, parse_json, validate_reference

VARIANT_SCHEMAS = {
    "analysis": "termivar-offline-pilot-variant-analysis/v1",
    "dependencies": "termivar-offline-dependency-exposure/v1",
    "licenses": "termivar-offline-pilot-license-readiness/v1",
    "summary": None, "manifest": "termivar-offline-pilot-variant-manifest/v1",
}
RECORD_FIELDS = (*DEPENDENCY_FIELDS, "source_json_pointer", "source_record_sha256",
                 "source_artifact_sha256", "manifest_file_ref", "license_source_key")
VARIANT_FIELDS = ("variant_id", "label", "description", "selected_component_ids", "not_selected_component_ids")


def read_group(paths: dict, expected: dict, schemas: dict, budget: ReadBudget) -> tuple[dict, dict]:
    if set(paths) != set(schemas) or set(expected) != set(schemas):
        raise InputError("dependency_evidence_explicit_artifact_roles_required")
    raw, docs = {}, {}
    for role, schema in schemas.items():
        limit = 64 * 1024 if role == "manifest" else 512 * 1024 if role == "summary" else 2 * 1024 * 1024
        raw[role] = budget.read(explicit_relative_path(paths[role]), limit)
        if {"schema_version": schema, **identity(raw[role])} != expected[role]:
            raise InputError("dependency_evidence_artifact_identity_mismatch")
        if role != "summary":
            docs[role] = parse_json(raw[role], maximum=limit)
            if type(docs[role]) is not dict or docs[role].get("schema_version") != schema:
                raise InputError("dependency_evidence_unsupported_artifact_contract")
    return raw, docs


@dataclass(frozen=True, slots=True)
class SourceContext:
    inventory: dict
    reference: dict
    components: list
    manifest_catalog: list
    phase24_records: list
    variant_selections: list
    license_boundary_counts: dict


def load_context(scope: dict, composition_paths: dict, variant_paths: dict, budget: ReadBudget) -> SourceContext:
    raw, old = read_group(composition_paths, scope["composition_sources"], COMPOSITION_SCHEMAS, budget)
    inv, dep, constraints = (old[key] for key in ("inventory", "dependencies", "constraints"))
    validate_composition(inv, dep, constraints)
    if json_bytes(constraints) != json_bytes(build_constraints(inv, dep)):
        raise InputError("dependency_evidence_source_constraints_mismatch")
    payloads = {"composition-inventory.json": raw["inventory"], "dependency-license-ledger.json": raw["dependencies"],
                "release-constraints.json": raw["constraints"], "composition-summary.md": raw["summary"]}
    if json_bytes(old["manifest"]) != json_bytes(composition_manifest(inv, dep, constraints, payloads)):
        raise InputError("dependency_evidence_composition_manifest_mismatch")
    variant_raw, pilot = read_group(variant_paths, scope["variant_sources"], VARIANT_SCHEMAS, budget)
    analysis, exposures, licenses = (pilot[key] for key in ("analysis", "dependencies", "licenses"))
    validate_pilot(analysis, exposures, licenses)
    if variant_raw["summary"] != pilot_summary(analysis, exposures, licenses):
        raise InputError("dependency_evidence_pilot_summary_mismatch")
    payloads = {"variant-analysis.json": variant_raw["analysis"], "dependency-exposure.json": variant_raw["dependencies"],
                "license-readiness.json": variant_raw["licenses"], "variant-comparison.md": variant_raw["summary"]}
    if json_bytes(pilot["manifest"]) != json_bytes(pilot_manifest(analysis, exposures, licenses, payloads)):
        raise InputError("dependency_evidence_pilot_manifest_mismatch")
    pins = {row["root_id"]: row["pinned_commit"] for row in inv["source_roots"]}
    selected = scope["source_reference"]
    if (selected["source_commits"] != pins or selected["composition_candidate_reference"] != inv["candidate_reference"]
            or analysis["source_reference"]["composition_sources"] != scope["composition_sources"]
            or analysis["source_reference"]["source_commits"] != pins):
        raise InputError("dependency_evidence_cross_phase_reference_mismatch")
    components = analysis["component_catalog"]
    if len(components) != len(inv["components"]) or len(exposures["records"]) != len(dep["dependencies"]):
        raise InputError("dependency_evidence_incomplete_source_projection")
    for index, (row, actual) in enumerate(zip(components, inv["components"])):
        if (any(row[key] != value for key, value in actual.items())
                or row["source_json_pointer"] != f"/components/{index}"
                or row["source_record_sha256"] != record_digest(actual)):
            raise InputError("dependency_evidence_component_source_mismatch")
    for row, actual in zip(exposures["records"], dep["dependencies"]):
        if any(row[key] != value for key, value in actual.items()):
            raise InputError("dependency_evidence_dependency_source_mismatch")
    file_ids = {(row["root_id"], row["path"]): row["file_id"] for row in inv["files"]}
    expected_catalog = [{**row, "source_file_ref": file_ids[(row["root_id"], row["path"])]}
                        for row in dep["manifest_records"]]
    if json_bytes(expected_catalog) != json_bytes(analysis["manifest_catalog"]):
        raise InputError("dependency_evidence_manifest_catalog_mismatch")
    declared_ownership = [{"component_id": row["component_id"], "source_record_sha256": record_digest(row)}
                          for row in inv["components"]]
    if scope["component_ownership_sources"] != declared_ownership:
        raise InputError("dependency_evidence_ownership_source_selection_mismatch")
    reference = validate_reference({**copy.deepcopy(selected),
                                    "composition_sources": copy.deepcopy(scope["composition_sources"]),
                                    "variant_sources": copy.deepcopy(scope["variant_sources"])})
    if len(dep["dependencies"]) > 1024:
        raise InputError("dependency_evidence_source_record_limit")
    boundary_fields = ("source_license_record_count", "base_unknown_license_count", "evidence_present_record_count",
                       "missing_evidence_record_count", "human_review_required_record_count", "source_blocker_count")
    return SourceContext(inv, reference, copy.deepcopy(components), copy.deepcopy(expected_catalog),
                         [{key: copy.deepcopy(row[key]) for key in RECORD_FIELDS} for row in exposures["records"]],
                         [{key: copy.deepcopy(row[key]) for key in VARIANT_FIELDS} for row in analysis["variants"]],
                         {key: licenses["counts"][key] for key in boundary_fields})
